"""Unit tests for the monologue-length-directive judging script.

The script lives at
``verification/scripts/2026-05-16_monologue_length_judging.py``. The
filename starts with a digit, so we load it via ``importlib.util``
(matching the test_monologue_length_experiment.py pattern).

These tests cover (per the task spec):
  - input loading + grouping (3 cells per group)
  - invalid grouping (group with != 3 cells) -> warning, skipped
  - label-randomization seeding (deterministic by group + criterion)
  - composite scoring math
  - bias-mitigation phrase present in every judge call (via mocked client)
  - resumability (pre-populate output, only missing tuples attempted)
  - parse-retry on malformed response (mock first 2 calls return gibberish,
    3rd returns valid -> succeeds within max_retries=3)
  - --dry-run does not call the Anthropic API
  - the Anthropic client is mocked throughout — no real API calls
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest import mock

import pytest


_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _ROOT / "verification" / "scripts"
    / "2026-05-16_monologue_length_judging.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "monologue_length_judging_under_test", _SCRIPT_PATH,
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mlj():
    return _load_module()


def _record(persona, prompt_index, trial_index, cell, response_text="resp",
            prompt_text="hi", pre_reg_doc_sha="sha-AAA"):
    return {
        "cell": cell,
        "persona": persona,
        "prompt_index": prompt_index,
        "prompt_text": prompt_text,
        "trial_index": trial_index,
        "model": "deepseek",
        "model_slug": "deepseek/deepseek-v4-flash",
        "monologue_text": "internal mono",
        "response_text": response_text,
        "anima_v1_sha": "anima-sha",
        "pre_reg_doc_sha": pre_reg_doc_sha,
    }


def _make_group(persona="marcus", pi=0, ti=0, prompt_text="p", suffix=""):
    return [
        _record(persona, pi, ti, "variable",
                response_text=f"variable-resp{suffix}",
                prompt_text=prompt_text),
        _record(persona, pi, ti, "short",
                response_text=f"short-resp{suffix}",
                prompt_text=prompt_text),
        _record(persona, pi, ti, "long",
                response_text=f"long-resp{suffix}",
                prompt_text=prompt_text),
    ]


# ---- grouping tests -----------------------------------------------------


def test_group_records_3_cells_per_group(mlj):
    records = _make_group("marcus", 0, 0)
    logs: list[str] = []
    groups, n_err = mlj._group_records(records, log=logs.append)
    assert n_err == 0
    assert list(groups.keys()) == [("marcus", 0, 0)]
    cm = groups[("marcus", 0, 0)]
    assert set(cm.keys()) == {"variable", "short", "long"}
    assert cm["short"]["response_text"] == "short-resp"
    assert not logs  # no warnings


def test_group_records_skips_error_records(mlj):
    records = _make_group("jamie", 1, 2)
    records.append({"_error": True, "reason": "oops"})
    logs: list[str] = []
    groups, n_err = mlj._group_records(records, log=logs.append)
    assert n_err == 1
    assert list(groups.keys()) == [("jamie", 1, 2)]


def test_group_records_skips_group_with_two_cells(mlj):
    """Group with only 2 cells -> warning logged, group DROPPED, no crash."""
    records = [
        _record("marcus", 0, 0, "variable"),
        _record("marcus", 0, 0, "short"),
    ]
    logs: list[str] = []
    groups, n_err = mlj._group_records(records, log=logs.append)
    assert groups == {}
    assert n_err == 0
    assert any("SKIPPING" in m for m in logs), logs


def test_group_records_skips_group_with_four_cells(mlj):
    """Duplicate cell -> kept first; if cells != {variable,short,long}
    the group is still skipped."""
    records = _make_group("marcus", 0, 0)
    # add a 4th record with an unknown cell
    records.append(_record("marcus", 0, 0, "extra-cell"))
    logs: list[str] = []
    groups, n_err = mlj._group_records(records, log=logs.append)
    assert groups == {}
    assert any("SKIPPING" in m for m in logs)


# ---- label-randomization seeding ----------------------------------------


def test_label_randomization_is_deterministic_for_same_inputs(mlj):
    s1 = mlj._label_seed("marcus", 3, 7, "warmth", 42)
    s2 = mlj._label_seed("marcus", 3, 7, "warmth", 42)
    assert s1 == s2
    m1 = mlj._randomize_labels(["variable", "short", "long"], seed=s1)
    m2 = mlj._randomize_labels(["variable", "short", "long"], seed=s2)
    assert m1 == m2


def test_label_randomization_differs_across_criteria(mlj):
    """Different criterion -> different seed -> almost-always different
    mapping (over many groups; we check that it's not pinned)."""
    diffs = 0
    for ti in range(40):
        s1 = mlj._label_seed("marcus", 0, ti, "warmth", 42)
        s2 = mlj._label_seed("marcus", 0, ti, "humor-playfulness", 42)
        m1 = mlj._randomize_labels(["variable", "short", "long"], seed=s1)
        m2 = mlj._randomize_labels(["variable", "short", "long"], seed=s2)
        if m1 != m2:
            diffs += 1
    # With 6 possible permutations, expect ~5/6 to differ across 40 trials.
    assert diffs >= 25, f"expected >=25 differences in 40 trials, got {diffs}"


def test_label_randomization_permutes_correctly(mlj):
    """Every output is a permutation of variable/short/long."""
    for seed in range(50):
        m = mlj._randomize_labels(
            ["variable", "short", "long"], seed=seed
        )
        assert set(m.keys()) == {"A", "B", "C"}
        assert set(m.values()) == {"variable", "short", "long"}


# ---- composite scoring math ---------------------------------------------


def test_composite_scoring_basic(mlj):
    """rank {A:2, B:1, C:3} + label_to_cell {A:short, B:variable, C:long}
    -> composite {short:2, variable:3, long:1}"""
    ranking = {"A": 2, "B": 1, "C": 3}
    label_to_cell = {"A": "short", "B": "variable", "C": "long"}
    out = mlj._composite_points_by_cell(ranking, label_to_cell)
    assert out == {"short": 2, "variable": 3, "long": 1}


def test_composite_scoring_full_permutation(mlj):
    """rank 1->3pt, 2->2pt, 3->1pt over the canonical mapping."""
    ranking = {"A": 1, "B": 2, "C": 3}
    label_to_cell = {"A": "variable", "B": "short", "C": "long"}
    out = mlj._composite_points_by_cell(ranking, label_to_cell)
    assert out == {"variable": 3, "short": 2, "long": 1}


# ---- ranking parsing ----------------------------------------------------


def test_parse_ranking_canonical_format(mlj):
    assert mlj._parse_ranking("A: 1\nB: 2\nC: 3") == {"A": 1, "B": 2, "C": 3}


def test_parse_ranking_with_whitespace_and_dashes(mlj):
    """Permissive separator handling."""
    text = "  A : 2 \n  B - 1\n  C: 3  "
    assert mlj._parse_ranking(text) == {"A": 2, "B": 1, "C": 3}


def test_parse_ranking_json_form(mlj):
    text = 'Sure! Here:\n{"A": 3, "B": 1, "C": 2}'
    assert mlj._parse_ranking(text) == {"A": 3, "B": 1, "C": 2}


def test_parse_ranking_rejects_duplicates(mlj):
    """A ranking that has any rank used more than once is invalid."""
    assert mlj._parse_ranking("A: 1\nB: 1\nC: 1") is None


def test_parse_ranking_rejects_out_of_range(mlj):
    """Ranks outside [1, 3] are invalid."""
    assert mlj._parse_ranking("A: 0\nB: 1\nC: 2") is None
    assert mlj._parse_ranking("A: 4\nB: 1\nC: 2") is None


def test_parse_ranking_rejects_gibberish(mlj):
    assert mlj._parse_ranking("I cannot rank these.") is None
    assert mlj._parse_ranking("") is None


# ---- bias-mitigation phrase present ------------------------------------


def test_system_prompt_includes_bias_mitigation_for_all_criteria(mlj):
    """For every (persona, criterion), the locked bias-mitigation
    phrase must appear in the system prompt."""
    for persona, crits in (
        ("marcus", mlj.MARCUS_CRITERIA),
        ("jamie", mlj.JAMIE_CRITERIA),
    ):
        for crit in crits:
            sp = mlj._build_system_prompt(persona, crit)
            assert "do not use response length" in sp.lower(), (
                f"{persona}/{crit}: bias-mitigation phrase missing"
            )
            # The phrase from §6 verbatim:
            assert "Do NOT use response length as a criterion" in sp, (
                f"{persona}/{crit}: verbatim phrase missing"
            )


def test_judge_client_asserts_bias_mitigation_present(mlj):
    """JudgeClient.ask refuses to call the API if the system prompt
    is missing the bias-mitigation phrase."""
    fake_client = mock.Mock()
    jc = mlj.JudgeClient(client=fake_client)
    with pytest.raises(AssertionError):
        jc.ask(system="You are a judge. Nothing else.", user="hi")
    fake_client.messages.create.assert_not_called()


def test_every_judge_call_carries_bias_mitigation(mlj, tmp_path,
                                                   monkeypatch):
    """End-to-end: every messages.create call's system block contains
    the locked bias-mitigation phrase."""
    in_path = tmp_path / "in.jsonl"
    out_path = tmp_path / "out.jsonl"
    with in_path.open("w") as fh:
        for r in _make_group("marcus", 0, 0):
            fh.write(json.dumps(r) + "\n")

    seen_systems: list[str] = []

    class _FakeResp:
        class _Usage:
            input_tokens = 100
            output_tokens = 10
            cache_read_input_tokens = 0
            cache_creation_input_tokens = 0
        class _Block:
            type = "text"
            text = "A: 1\nB: 2\nC: 3"
        usage = _Usage()
        content = [_Block()]

    class _FakeMessages:
        def create(self, **kwargs):
            sys_blocks = kwargs["system"]
            assert isinstance(sys_blocks, list)
            for sb in sys_blocks:
                seen_systems.append(sb["text"])
            return _FakeResp()

    class _FakeClient:
        messages = _FakeMessages()

    # Patch JudgeClient to use our fake client.
    real_init = mlj.JudgeClient.__init__

    def _fake_init(self, *, model=mlj.JUDGE_MODEL, client=None,
                   api_key=None):
        real_init(self, model=model, client=_FakeClient(), api_key=None)

    monkeypatch.setattr(mlj.JudgeClient, "__init__", _fake_init)

    rc = mlj.main([
        "--input", str(in_path),
        "--output", str(out_path),
    ])
    assert rc == 0, "expected success exit"
    # 1 group * 4 criteria (marcus) = 4 judge calls.
    assert len(seen_systems) == 4
    for sp in seen_systems:
        assert "Do NOT use response length as a criterion" in sp


# ---- resumability -------------------------------------------------------


def test_resumability_skips_completed_tuples(mlj, tmp_path, monkeypatch):
    """Pre-populate output with judgments for 2 of the 4 criteria; verify
    only the missing 2 are attempted."""
    in_path = tmp_path / "in.jsonl"
    out_path = tmp_path / "out.jsonl"
    with in_path.open("w") as fh:
        for r in _make_group("marcus", 0, 0):
            fh.write(json.dumps(r) + "\n")

    # Pre-populate with 2 completed judgments.
    pre = []
    for crit in mlj.MARCUS_CRITERIA[:2]:
        pre.append({
            "persona": "marcus",
            "prompt_index": 0,
            "trial_index": 0,
            "criterion": crit,
            "label_to_cell": {"A": "variable", "B": "short", "C": "long"},
            "ranking_by_label": {"A": 1, "B": 2, "C": 3},
            "composite_points_by_cell": {"variable": 3, "short": 2, "long": 1},
            "judge_model": mlj.JUDGE_MODEL,
            "judge_response_raw": "A: 1\nB: 2\nC: 3",
            "judge_seed": 1234,
            "timestamp_iso": "2026-05-16T00:00:00Z",
            "pre_reg_doc_sha": "sha-AAA",
        })
    with out_path.open("w") as fh:
        for r in pre:
            fh.write(json.dumps(r) + "\n")

    call_count = {"n": 0}

    class _FakeResp:
        class _Usage:
            input_tokens = 100
            output_tokens = 10
            cache_read_input_tokens = 0
            cache_creation_input_tokens = 0
        class _Block:
            type = "text"
            text = "A: 1\nB: 2\nC: 3"
        usage = _Usage()
        content = [_Block()]

    class _FakeMessages:
        def create(self, **kwargs):
            call_count["n"] += 1
            return _FakeResp()

    class _FakeClient:
        messages = _FakeMessages()

    real_init = mlj.JudgeClient.__init__

    def _fake_init(self, *, model=mlj.JUDGE_MODEL, client=None,
                   api_key=None):
        real_init(self, model=model, client=_FakeClient(), api_key=None)

    monkeypatch.setattr(mlj.JudgeClient, "__init__", _fake_init)

    rc = mlj.main([
        "--input", str(in_path),
        "--output", str(out_path),
    ])
    assert rc == 0
    # 4 criteria total; 2 pre-completed; should make 2 calls.
    assert call_count["n"] == 2

    # Output file should have all 4 records now.
    with out_path.open() as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    crits_in_output = sorted(r["criterion"] for r in lines)
    assert crits_in_output == sorted(mlj.MARCUS_CRITERIA)


def test_resumability_retries_errored_records(mlj, tmp_path, monkeypatch):
    """Pre-populate output with an errored judgment; verify the script
    retries it (and drops the errored record from the rewritten file)."""
    in_path = tmp_path / "in.jsonl"
    out_path = tmp_path / "out.jsonl"
    with in_path.open("w") as fh:
        for r in _make_group("marcus", 0, 0):
            fh.write(json.dumps(r) + "\n")

    errored = {
        "persona": "marcus",
        "prompt_index": 0,
        "trial_index": 0,
        "criterion": mlj.MARCUS_CRITERIA[0],
        "label_to_cell": {"A": "variable", "B": "short", "C": "long"},
        "_judge_error": True,
        "judge_error": "parse failure",
        "judge_response_raw": "garbage",
        "judge_attempts": 4,
        "pre_reg_doc_sha": "sha-AAA",
    }
    # Pre-populate output with 3 ok records (for the other 3 criteria)
    # plus the errored one.
    ok_records = []
    for crit in mlj.MARCUS_CRITERIA[1:]:
        ok_records.append({
            "persona": "marcus",
            "prompt_index": 0,
            "trial_index": 0,
            "criterion": crit,
            "label_to_cell": {"A": "variable", "B": "short", "C": "long"},
            "ranking_by_label": {"A": 1, "B": 2, "C": 3},
            "composite_points_by_cell": {"variable": 3, "short": 2, "long": 1},
            "judge_model": mlj.JUDGE_MODEL,
            "judge_response_raw": "A: 1\nB: 2\nC: 3",
            "judge_seed": 1,
            "timestamp_iso": "2026-05-16T00:00:00Z",
            "pre_reg_doc_sha": "sha-AAA",
        })
    with out_path.open("w") as fh:
        fh.write(json.dumps(errored) + "\n")
        for r in ok_records:
            fh.write(json.dumps(r) + "\n")

    calls = {"n": 0}

    class _FakeResp:
        class _Usage:
            input_tokens = 100
            output_tokens = 10
            cache_read_input_tokens = 0
            cache_creation_input_tokens = 0
        class _Block:
            type = "text"
            text = "A: 2\nB: 1\nC: 3"
        usage = _Usage()
        content = [_Block()]

    class _FakeMessages:
        def create(self, **kwargs):
            calls["n"] += 1
            return _FakeResp()

    class _FakeClient:
        messages = _FakeMessages()

    real_init = mlj.JudgeClient.__init__

    def _fake_init(self, *, model=mlj.JUDGE_MODEL, client=None,
                   api_key=None):
        real_init(self, model=model, client=_FakeClient(), api_key=None)

    monkeypatch.setattr(mlj.JudgeClient, "__init__", _fake_init)

    rc = mlj.main([
        "--input", str(in_path),
        "--output", str(out_path),
    ])
    assert rc == 0
    # Should have re-attempted exactly the errored criterion.
    assert calls["n"] == 1

    with out_path.open() as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    # 3 pre-ok + 1 re-attempted = 4 total records, all ok.
    assert len(lines) == 4
    for r in lines:
        assert not r.get("_judge_error")


# ---- parse-retry on malformed response ----------------------------------


def test_parse_retry_succeeds_within_budget(mlj, tmp_path, monkeypatch):
    """Mock first 2 calls return gibberish, 3rd returns valid -> the
    judgment record succeeds (max_retries=3 means up to 4 total
    attempts, well within budget)."""
    in_path = tmp_path / "in.jsonl"
    out_path = tmp_path / "out.jsonl"
    with in_path.open("w") as fh:
        for r in _make_group("marcus", 0, 0):
            fh.write(json.dumps(r) + "\n")

    sequence = iter([
        "garbage 1",
        "still nonsense",
        "A: 1\nB: 2\nC: 3",
        # remaining criteria succeed first try
        "A: 1\nB: 2\nC: 3",
        "A: 1\nB: 2\nC: 3",
        "A: 1\nB: 2\nC: 3",
    ])

    class _FakeMessages:
        def create(self, **kwargs):
            txt = next(sequence)
            class _FakeResp:
                class _Usage:
                    input_tokens = 100
                    output_tokens = 10
                    cache_read_input_tokens = 0
                    cache_creation_input_tokens = 0
                class _Block:
                    type = "text"
                    text = txt
                usage = _Usage()
                content = [_Block()]
            return _FakeResp()

    class _FakeClient:
        messages = _FakeMessages()

    real_init = mlj.JudgeClient.__init__

    def _fake_init(self, *, model=mlj.JUDGE_MODEL, client=None,
                   api_key=None):
        real_init(self, model=model, client=_FakeClient(), api_key=None)

    monkeypatch.setattr(mlj.JudgeClient, "__init__", _fake_init)
    # Avoid sleeping during retries.
    monkeypatch.setattr(mlj.time, "sleep", lambda s: None)

    rc = mlj.main([
        "--input", str(in_path),
        "--output", str(out_path),
        "--max-retries", "3",
    ])
    assert rc == 0
    with out_path.open() as fh:
        records = [json.loads(l) for l in fh if l.strip()]
    assert len(records) == 4
    # Calls now iterate in (persona, criterion, prompt_index, trial_index)
    # order — i.e. criteria are visited in ALPHABETICAL order, not in the
    # order they appear in MARCUS_CRITERIA. The first iterated criterion
    # is the one that consumed the 3 retries in `sequence`.
    first_iter_crit = sorted(mlj.MARCUS_CRITERIA)[0]
    first = next(
        r for r in records if r["criterion"] == first_iter_crit
    )
    assert first.get("judge_attempts") == 3
    assert first.get("ranking_by_label") == {"A": 1, "B": 2, "C": 3}
    assert not first.get("_judge_error")


def test_parse_retry_exhausts_budget_writes_error_record(mlj, tmp_path,
                                                          monkeypatch):
    """If all retries return gibberish, write a record with
    _judge_error=True."""
    in_path = tmp_path / "in.jsonl"
    out_path = tmp_path / "out.jsonl"
    with in_path.open("w") as fh:
        for r in _make_group("marcus", 0, 0):
            fh.write(json.dumps(r) + "\n")

    class _FakeMessages:
        def create(self, **kwargs):
            class _FakeResp:
                class _Usage:
                    input_tokens = 100
                    output_tokens = 10
                    cache_read_input_tokens = 0
                    cache_creation_input_tokens = 0
                class _Block:
                    type = "text"
                    text = "never going to parse"
                usage = _Usage()
                content = [_Block()]
            return _FakeResp()

    class _FakeClient:
        messages = _FakeMessages()

    real_init = mlj.JudgeClient.__init__

    def _fake_init(self, *, model=mlj.JUDGE_MODEL, client=None,
                   api_key=None):
        real_init(self, model=model, client=_FakeClient(), api_key=None)

    monkeypatch.setattr(mlj.JudgeClient, "__init__", _fake_init)
    monkeypatch.setattr(mlj.time, "sleep", lambda s: None)

    rc = mlj.main([
        "--input", str(in_path),
        "--output", str(out_path),
        "--max-retries", "2",
    ])
    # Errors -> non-zero exit per script convention (6).
    assert rc == 6
    with out_path.open() as fh:
        records = [json.loads(l) for l in fh if l.strip()]
    assert len(records) == 4
    for r in records:
        assert r.get("_judge_error") is True
        assert r.get("judge_attempts") == 3  # max_retries=2 -> 3 attempts


# ---- --dry-run ----------------------------------------------------------


def test_dry_run_makes_no_api_calls(mlj, tmp_path, monkeypatch):
    """--dry-run must short-circuit before any Anthropic API call."""
    in_path = tmp_path / "in.jsonl"
    out_path = tmp_path / "out.jsonl"
    with in_path.open("w") as fh:
        for r in _make_group("marcus", 0, 0):
            fh.write(json.dumps(r) + "\n")
        for r in _make_group("jamie", 0, 0):
            fh.write(json.dumps(r) + "\n")

    def _explode(*args, **kwargs):
        raise AssertionError(
            "--dry-run leaked a JudgeClient construction call"
        )

    monkeypatch.setattr(mlj, "JudgeClient", _explode)

    rc = mlj.main([
        "--input", str(in_path),
        "--output", str(out_path),
        "--dry-run",
    ])
    assert rc == 0
    # Output file should not have any judgment records.
    assert not out_path.exists() or out_path.read_text().strip() == ""


# ---- input-loading sanity ----------------------------------------------


def test_load_input_records_missing_file_raises(mlj, tmp_path):
    with pytest.raises(FileNotFoundError):
        mlj._load_input_records(tmp_path / "nope.jsonl")


def test_load_input_records_skips_blank_lines(mlj, tmp_path):
    in_path = tmp_path / "in.jsonl"
    with in_path.open("w") as fh:
        for r in _make_group("marcus", 0, 0):
            fh.write(json.dumps(r) + "\n")
            fh.write("\n")  # blank line
    recs = mlj._load_input_records(in_path)
    assert len(recs) == 3


def test_load_input_records_malformed_json_raises(mlj, tmp_path):
    in_path = tmp_path / "in.jsonl"
    in_path.write_text('{"persona": "marcus"\n')  # truncated JSON
    with pytest.raises(ValueError, match="malformed JSON"):
        mlj._load_input_records(in_path)


def test_verify_pre_reg_consistency_logs_on_mismatch(mlj):
    records = _make_group("marcus", 0, 0)
    records[1]["pre_reg_doc_sha"] = "different-sha"
    logs: list[str] = []
    sha = mlj._verify_pre_reg_consistency(records, log=logs.append)
    # Mismatch -> returns None per the function contract.
    assert sha is None
    assert any("mismatch" in m.lower() for m in logs)


# ---- judge prompt content ----------------------------------------------


def test_user_prompt_contains_response_text_not_monologue(mlj):
    label_to_response = {
        "A": "this is response A",
        "B": "this is response B",
        "C": "this is response C",
    }
    up = mlj._build_user_prompt("the original prompt", label_to_response)
    assert "this is response A" in up
    assert "this is response B" in up
    assert "this is response C" in up
    assert "the original prompt" in up


def test_persona_yaml_unknown_raises(mlj):
    with pytest.raises(ValueError):
        mlj._persona_yaml_path("not-a-persona")


# ---- new behaviors (post-review): caching, call order, malformed-resume ----


def test_persona_summary_loaded_once_per_persona(mlj, monkeypatch, tmp_path):
    """_load_persona_summary should be cached: called once per persona,
    not once per judge call. With 2 personas in the input, we expect
    AT MOST 2 underlying disk reads even across many judge calls.

    We test the cache via the lru_cache wrapper directly — clear the
    cache, then exercise _build_system_prompt many times for both
    personas and verify the underlying loader was hit at most once per
    persona.
    """
    # The decorator wraps _load_persona_summary with lru_cache, so it
    # exposes cache_info() and cache_clear(). Reset before exercising.
    mlj._load_persona_summary.cache_clear()

    # Spy on the YAML loader so we can count actual disk reads.
    calls: list[str] = []
    real_loader = mlj._load_persona_summary.__wrapped__  # underlying fn

    def _counting(persona):
        calls.append(persona)
        return real_loader(persona)

    # Patch the cached attr to wrap the underlying fn through our spy.
    cached = mlj.functools.lru_cache(maxsize=None)(_counting)
    monkeypatch.setattr(mlj, "_load_persona_summary", cached)

    # Now build system prompts for 4 criteria * 2 personas = 8 calls.
    for persona, crits in (
        ("marcus", mlj.MARCUS_CRITERIA),
        ("jamie", mlj.JAMIE_CRITERIA),
    ):
        for crit in crits:
            for _ in range(5):  # extra iterations to prove caching
                _ = mlj._build_system_prompt(persona, crit)

    # We expect exactly ONE underlying load per persona (lru_cache hit
    # the second time onward). Total: 2 disk reads, not 40.
    assert sorted(calls) == ["jamie", "marcus"], (
        f"expected one disk read per persona; got calls={calls}"
    )


def test_persona_summary_cache_decorator_present(mlj):
    """Confirm lru_cache is in place on _load_persona_summary."""
    assert hasattr(mlj._load_persona_summary, "cache_info"), (
        "_load_persona_summary must be wrapped with functools.lru_cache"
    )
    assert hasattr(mlj._load_persona_summary, "cache_clear")


def test_call_order_is_persona_criterion_prompt_trial(
    mlj, tmp_path, monkeypatch
):
    """End-to-end: with multiple groups, the order of API calls must be
    sorted by (persona, criterion, prompt_index, trial_index), NOT by
    (persona, prompt_index, trial_index, criterion). This is required
    for Anthropic ephemeral cache reuse on the system prompt block.
    """
    in_path = tmp_path / "in.jsonl"
    out_path = tmp_path / "out.jsonl"

    # Two marcus groups (pi=0,ti=0) and (pi=0,ti=1) — 2 groups * 4
    # criteria = 8 calls expected. We can verify order from the call
    # log.
    with in_path.open("w") as fh:
        for r in _make_group("marcus", 0, 0, suffix="-a"):
            fh.write(json.dumps(r) + "\n")
        for r in _make_group("marcus", 0, 1, suffix="-b"):
            fh.write(json.dumps(r) + "\n")

    seen_systems: list[str] = []

    class _FakeResp:
        class _Usage:
            input_tokens = 100
            output_tokens = 10
            cache_read_input_tokens = 0
            cache_creation_input_tokens = 0
        class _Block:
            type = "text"
            text = "A: 1\nB: 2\nC: 3"
        usage = _Usage()
        content = [_Block()]

    class _FakeMessages:
        def create(self, **kwargs):
            sys_blocks = kwargs["system"]
            for sb in sys_blocks:
                seen_systems.append(sb["text"])
            return _FakeResp()

    class _FakeClient:
        messages = _FakeMessages()

    real_init = mlj.JudgeClient.__init__

    def _fake_init(self, *, model=mlj.JUDGE_MODEL, client=None,
                   api_key=None):
        real_init(self, model=model, client=_FakeClient(), api_key=None)

    monkeypatch.setattr(mlj.JudgeClient, "__init__", _fake_init)

    rc = mlj.main([
        "--input", str(in_path),
        "--output", str(out_path),
    ])
    assert rc == 0

    # Read the output to recover the actual order of (persona,
    # criterion, prompt_index, trial_index) tuples.
    with out_path.open() as fh:
        records = [json.loads(l) for l in fh if l.strip()]
    order = [
        (r["persona"], r["criterion"], r["prompt_index"], r["trial_index"])
        for r in records
    ]

    # Expected order: same persona throughout (only marcus). Criteria
    # iterated alphabetically. Within each criterion, the two groups
    # iterated in (prompt_index, trial_index) order.
    expected = []
    for crit in sorted(mlj.MARCUS_CRITERIA):
        for (pi, ti) in [(0, 0), (0, 1)]:
            expected.append(("marcus", crit, pi, ti))
    assert order == expected, (
        f"call order is wrong for cache reuse.\n"
        f"got:      {order}\n"
        f"expected: {expected}"
    )

    # Sanity: same system prompt appears in TWO consecutive calls per
    # criterion (because we have 2 groups per persona-criterion pair).
    # That's the property that lets the ephemeral cache hit.
    assert len(seen_systems) == 8
    # Pairs 0-1, 2-3, 4-5, 6-7 should match (same criterion).
    for i in (0, 2, 4, 6):
        assert seen_systems[i] == seen_systems[i + 1], (
            f"consecutive same-criterion calls should share system "
            f"prompt (index {i})"
        )
    # Adjacent across criteria should differ (criterion changed).
    for i in (1, 3, 5):
        assert seen_systems[i] != seen_systems[i + 1], (
            f"across-criterion calls should differ in system prompt "
            f"(index {i})"
        )


def test_malformed_resume_jsonl_refuses_to_start(mlj, tmp_path, monkeypatch):
    """If the existing output JSONL has a malformed line, the script
    must refuse to start and exit with code 8 — mirroring the harness
    MalformedJsonlError discipline. The default behavior of silently
    skipping malformed lines is unacceptable for a resumable run."""
    in_path = tmp_path / "in.jsonl"
    out_path = tmp_path / "out.jsonl"
    with in_path.open("w") as fh:
        for r in _make_group("marcus", 0, 0):
            fh.write(json.dumps(r) + "\n")

    # Pre-populate with one ok record followed by a malformed line.
    with out_path.open("w") as fh:
        fh.write(json.dumps({
            "persona": "marcus",
            "prompt_index": 0,
            "trial_index": 0,
            "criterion": mlj.MARCUS_CRITERIA[0],
            "label_to_cell": {"A": "variable", "B": "short", "C": "long"},
            "ranking_by_label": {"A": 1, "B": 2, "C": 3},
            "composite_points_by_cell": {"variable": 3, "short": 2, "long": 1},
            "judge_model": mlj.JUDGE_MODEL,
            "judge_seed": 7,
            "timestamp_iso": "2026-05-16T00:00:00Z",
        }) + "\n")
        fh.write('{"persona": "marcus", "broken\n')  # malformed
        fh.write(json.dumps({
            "persona": "marcus",
            "prompt_index": 0,
            "trial_index": 0,
            "criterion": mlj.MARCUS_CRITERIA[1],
            "label_to_cell": {"A": "variable", "B": "short", "C": "long"},
            "ranking_by_label": {"A": 1, "B": 2, "C": 3},
            "composite_points_by_cell": {"variable": 3, "short": 2, "long": 1},
            "judge_model": mlj.JUDGE_MODEL,
            "judge_seed": 8,
            "timestamp_iso": "2026-05-16T00:00:00Z",
        }) + "\n")

    # JudgeClient should never be constructed — we should bail before
    # any API call.
    def _explode(*args, **kwargs):
        raise AssertionError(
            "malformed JSONL leaked past the refusal check; "
            "JudgeClient was constructed"
        )

    monkeypatch.setattr(mlj, "JudgeClient", _explode)

    rc = mlj.main([
        "--input", str(in_path),
        "--output", str(out_path),
    ])
    assert rc == 8, (
        f"expected exit code 8 (malformed JSONL refusal); got {rc}"
    )

    # Direct unit-level check on the helper.
    with pytest.raises(mlj.MalformedJsonlError):
        mlj._load_completed_keys(out_path)


def test_load_completed_keys_well_formed_still_works(mlj, tmp_path):
    """Smoke test: a well-formed existing output must still load
    cleanly after the malformed-refusal change."""
    out_path = tmp_path / "out.jsonl"
    with out_path.open("w") as fh:
        fh.write(json.dumps({
            "persona": "marcus",
            "prompt_index": 3,
            "trial_index": 7,
            "criterion": "warmth",
            "ranking_by_label": {"A": 1, "B": 2, "C": 3},
        }) + "\n")
        fh.write(json.dumps({
            "_judge_error": True,
            "persona": "marcus",
            "prompt_index": 3,
            "trial_index": 8,
            "criterion": "warmth",
        }) + "\n")
    completed, existing = mlj._load_completed_keys(out_path)
    assert ("marcus", 3, 7, "warmth") in completed
    assert len(existing) == 2  # ok + errored both returned
