"""Unit tests for the monologue-length-directive experiment harness.

The harness lives at
``verification/scripts/2026-05-16_monologue_length_experiment.py``. The
filename starts with a digit, so we load it via ``importlib.util`` rather
than a normal import — that keeps the date prefix in the artifact name
while still allowing in-process testing.

These tests cover (per the task spec):
  - prompt JSON loading (the on-disk files for both sources)
  - record schema (a mocked trial yields a dict with all required keys)
  - randomization is seeded (same seed -> same order)
  - pre-flight check catches a modified anima_v1 hash
  - --dry-run does not call any LLM

The LLM adapter is always mocked — no real API calls, no network, no
keys required.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

import pytest


_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _ROOT / "verification" / "scripts"
    / "2026-05-16_monologue_length_experiment.py"
)


def _load_module():
    """Load the date-prefixed script as a module without importing it via
    its non-identifier name."""
    spec = importlib.util.spec_from_file_location(
        "monologue_length_experiment_under_test", _SCRIPT_PATH,
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mle():
    return _load_module()


# ---- prompt JSON loading -------------------------------------------------


def test_load_prompts_primary_returns_8_strings(mle):
    prompts, path = mle._load_prompts("primary")
    assert len(prompts) == 8
    assert all(isinstance(p, str) and p.strip() for p in prompts)
    assert path.name == "aai_2026-05-16.json"


def test_load_prompts_fresh_returns_8_strings(mle):
    prompts, path = mle._load_prompts("fresh")
    assert len(prompts) == 8
    assert all(isinstance(p, str) and p.strip() for p in prompts)
    assert path.name == "mcadams_lsi_2026-05-16.json"


def test_load_prompts_unknown_source_raises(mle):
    with pytest.raises(ValueError):
        mle._load_prompts("nonsense")


def test_load_prompts_missing_file_raises(mle, tmp_path, monkeypatch):
    """If the on-disk file is missing, _load_prompts raises FileNotFoundError."""
    # Patch _ROOT to a tmp dir with no prompts/ subtree.
    monkeypatch.setattr(mle, "_ROOT", tmp_path)
    with pytest.raises(FileNotFoundError):
        mle._load_prompts("primary")


def test_load_prompts_wrong_count_raises(mle, tmp_path, monkeypatch):
    """A prompts file with != 8 entries must be rejected."""
    fake_prompts_dir = tmp_path / "verification" / "prompts"
    fake_prompts_dir.mkdir(parents=True)
    bad_file = fake_prompts_dir / "aai_2026-05-16.json"
    bad_file.write_text(json.dumps(["only one"]))
    monkeypatch.setattr(mle, "_ROOT", tmp_path)
    with pytest.raises(ValueError, match="exactly 8"):
        mle._load_prompts("primary")


# ---- record schema -------------------------------------------------------


def _patch_anima_for_trial(monkeypatch, mle, *, monologue_text: str,
                            response_text: str):
    """Replace ``_build_anima`` with a stub that returns an object whose
    ``respond()`` yields (response_text, fake_trace).
    """
    class _FakeTrace:
        def __init__(self, mono):
            self.monologue = mono
            self.usage = {}

    class _FakeAnima:
        def __init__(self, mono, resp):
            self._mono = mono
            self._resp = resp

        def respond(self, prompt):  # noqa: ARG002
            return self._resp, _FakeTrace(self._mono)

    def _stub(persona, cell, llm):  # noqa: ARG001
        return _FakeAnima(monologue_text, response_text)

    monkeypatch.setattr(mle, "_build_anima", _stub)


def test_record_schema_has_all_required_keys(mle, monkeypatch):
    """A mocked turn yields a dict with every key in RECORD_SCHEMA_KEYS,
    and every value has the expected type."""
    _patch_anima_for_trial(
        monkeypatch, mle,
        monologue_text="A thought. Another thought. A third.",
        response_text="I'm fine. Really.",
    )
    rec = mle._run_single_trial(
        persona="marcus",
        cell="short",
        prompt_index=0,
        prompt_text="hello",
        trial_index=3,
        model="deepseek",
        model_slug="deepseek/deepseek-v4-flash",
        llm=mock.Mock(),
        anima_v1_sha="abc123",
        pre_reg_doc_sha="def456",
    )
    for key in mle.RECORD_SCHEMA_KEYS:
        assert key in rec, f"missing key {key!r} in record"
    assert rec["cell"] == "short"
    assert rec["persona"] == "marcus"
    assert rec["prompt_index"] == 0
    assert rec["trial_index"] == 3
    assert rec["model"] == "deepseek"
    assert rec["model_slug"] == "deepseek/deepseek-v4-flash"
    assert rec["monologue_text"] == "A thought. Another thought. A third."
    assert rec["monologue_sentence_count"] == 3
    assert rec["response_text"] == "I'm fine. Really."
    assert rec["response_sentence_count"] == 2
    assert rec["monologue_max_tokens"] == 120  # short cell cap
    assert rec["anima_v1_sha"] == "abc123"
    assert rec["pre_reg_doc_sha"] == "def456"
    # ISO timestamp ends with Z, length matches "YYYY-MM-DDTHH:MM:SSZ"
    assert rec["timestamp_iso"].endswith("Z")


def test_sentence_count_handles_edge_cases(mle):
    assert mle._sentence_count("") == 0
    assert mle._sentence_count("   ") == 0
    assert mle._sentence_count("One.") == 1
    assert mle._sentence_count("One. Two!") == 2
    assert mle._sentence_count("Q? A. Yes.") == 3
    # Fragments with no terminal punctuation don't get counted as
    # sentences — that's fine for the compliance check.
    assert mle._sentence_count("just words") == 0


# ---- randomization seeded -----------------------------------------------


def test_run_plan_reproducible_under_same_seed(mle):
    a = mle._build_run_plan(
        source="primary", model="deepseek",
        personas=["marcus", "jamie"],
        cells=["variable", "short", "long"],
        n_prompts=8, trials=20, seed=42,
    )
    b = mle._build_run_plan(
        source="primary", model="deepseek",
        personas=["marcus", "jamie"],
        cells=["variable", "short", "long"],
        n_prompts=8, trials=20, seed=42,
    )
    assert a == b
    # And different seed produces a different order (overwhelmingly likely
    # at 960 elements; the probability of identical permutations is 1/960!).
    c = mle._build_run_plan(
        source="primary", model="deepseek",
        personas=["marcus", "jamie"],
        cells=["variable", "short", "long"],
        n_prompts=8, trials=20, seed=123,
    )
    assert a != c


def test_run_plan_preserves_count(mle):
    plan = mle._build_run_plan(
        source="primary", model="deepseek",
        personas=["marcus", "jamie"],
        cells=["variable", "short", "long"],
        n_prompts=8, trials=20, seed=42,
    )
    # 2 personas * 3 cells * 8 prompts * 20 trials = 960
    assert len(plan) == 960
    # Every (persona, cell, prompt, trial) appears exactly once.
    seen = set()
    for step in plan:
        key = (step["persona"], step["cell"], step["prompt_index"],
               step["trial_index"])
        assert key not in seen, f"duplicate: {key}"
        seen.add(key)
    assert len(seen) == 960


def test_run_plan_trial_index_is_zero_to_n_minus_1(mle):
    plan = mle._build_run_plan(
        source="fresh", model="qwen",
        personas=["marcus"],
        cells=["variable"],
        n_prompts=2, trials=5, seed=42,
    )
    # 1 * 1 * 2 * 5 = 10
    assert len(plan) == 10
    # trial_index ranges 0..4 for each (persona, cell, prompt)
    by_key: dict[tuple, list[int]] = {}
    for s in plan:
        k = (s["persona"], s["cell"], s["prompt_index"])
        by_key.setdefault(k, []).append(s["trial_index"])
    for k, idxs in by_key.items():
        assert sorted(idxs) == list(range(5)), f"bad trial_index set for {k}"


# ---- pre-flight: anima_v1 SHA mismatch ----------------------------------


def test_main_aborts_on_anima_v1_sha_mismatch(mle, tmp_path, monkeypatch,
                                              capsys):
    """main() must return non-zero (specifically 3) when the actual anima_v1
    SHA differs from EXPECTED_ANIMA_V1_SHA."""
    # Patch the SHA-computer to return a bogus value; everything else is
    # left intact (so prompts load fine and the pre-reg doc still exists).
    monkeypatch.setattr(mle, "_compute_anima_v1_sha", lambda: "deadbeef" * 8)
    out_dir = tmp_path / "reports"
    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "1",
    ])
    assert rc == 3, f"expected exit code 3 on SHA mismatch; got {rc}"
    # No JSONL should be written.
    assert not (out_dir / "2026-05-16_monologue_length_primary_deepseek.jsonl"
                ).exists()


def test_main_skip_integrity_check_bypasses_mismatch(mle, tmp_path,
                                                     monkeypatch):
    """With --skip-integrity-check, a mismatched SHA does NOT abort
    (debugging escape hatch). Combined with --dry-run so we don't make
    network calls."""
    monkeypatch.setattr(mle, "_compute_anima_v1_sha", lambda: "deadbeef" * 8)
    out_dir = tmp_path / "reports"
    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "1",
        "--skip-integrity-check",
        "--dry-run",
    ])
    assert rc == 0, f"expected dry-run + skip-integrity to exit 0; got {rc}"


# ---- --dry-run makes zero LLM calls -------------------------------------


def test_dry_run_makes_no_llm_calls(mle, tmp_path, monkeypatch):
    """--dry-run must short-circuit before any adapter is built, let alone
    used. We patch the adapter factory to raise — if it's called, the
    test fails. We ALSO patch _build_anima for symmetry, in case the
    short-circuit ever regresses."""
    def _explode(*args, **kwargs):
        raise AssertionError(
            "--dry-run leaked an LLM-adapter construction call"
        )

    monkeypatch.setattr(mle, "_make_adapter_for_model", _explode)
    monkeypatch.setattr(mle, "_build_anima", _explode)

    out_dir = tmp_path / "reports"
    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "5",
        "--dry-run",
    ])
    assert rc == 0, f"dry-run should exit 0; got {rc}"
    # No JSONL written.
    out_path = (out_dir
                / "2026-05-16_monologue_length_primary_deepseek.jsonl")
    assert not out_path.exists()


def test_dry_run_with_fresh_source(mle, tmp_path, monkeypatch):
    """Same as above but exercises the fresh source path."""
    monkeypatch.setattr(
        mle, "_make_adapter_for_model",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("leaked"))
    )
    rc = mle.main([
        "--source", "fresh",
        "--model", "qwen",
        "--output-dir", str(tmp_path / "reports"),
        "--dry-run",
    ])
    assert rc == 0


# ---- model dispatch -----------------------------------------------------


def test_model_slugs_locked(mle):
    """The pre-reg locks the OpenRouter slugs in §2; this test fails loudly
    if a future edit accidentally changes them."""
    assert mle.MODEL_SLUGS == {
        "deepseek": "deepseek/deepseek-v4-flash",
        "mistral": "mistralai/mistral-small-3.2-24b-instruct",
        "qwen": "qwen/qwen3-30b-a3b",
    }


def test_cell_max_tokens_match_pre_reg(mle):
    """The pre-reg §5 locks max_tokens=1500/120/720 for variable/short/long."""
    assert mle.CELL_MAX_TOKENS == {"variable": 1500, "short": 120, "long": 720}


# =========================================================================
# Resume / error-record / exit-code coverage (Fix 1 + Fix 2)
# =========================================================================

# These tests share a small set of helpers for driving main() with a fake
# adapter and a fake _build_anima that can be told to succeed or to raise
# per-trial. We always use --skip-integrity-check to avoid worrying about
# the anima_v1 SHA from inside a tmp_path setup. _load_prompts and the
# pre-reg doc are left intact (they load fine from the real repo).


def _install_fake_adapter_and_anima(
    monkeypatch, mle, *,
    failing_tuples: set[tuple[str, str, int, int]] | None = None,
    monologue_text: str = "M1. M2.",
    response_text: str = "R1. R2.",
):
    """Patch ``_make_adapter_for_model`` and ``_build_anima`` so main() can
    run end-to-end with no LLM calls.

    If a trial's (persona, cell, prompt_index, trial_index) is in
    ``failing_tuples``, the corresponding _build_anima call returns an
    Anima whose ``respond()`` raises RuntimeError. The harness must
    persist an error record and continue.
    """
    if failing_tuples is None:
        failing_tuples = set()

    class _FakeTrace:
        def __init__(self, mono):
            self.monologue = mono
            self.usage = {}

    class _FakeAnima:
        def __init__(self, key):
            self._key = key

        def respond(self, prompt):  # noqa: ARG002
            if self._key in failing_tuples:
                raise RuntimeError(f"synthetic failure for {self._key}")
            return response_text, _FakeTrace(monologue_text)

    # We need to know which (persona, cell, prompt, trial) we're in when
    # _build_anima is called, but _build_anima only gets (persona, cell, llm).
    # We can't recover prompt/trial from those args. Instead, patch
    # _run_single_trial to route through a wrapper that gives us the full
    # tuple, OR keep _build_anima dumb and let respond() check via prompt.
    # Easiest: monkeypatch _run_single_trial directly. That decouples this
    # test from anima_v1 entirely and lets us decide pass/fail per tuple.

    real_run = mle._run_single_trial

    def _stub_run_single_trial(*, persona, cell, prompt_index, prompt_text,
                                trial_index, model, model_slug, llm,
                                anima_v1_sha, pre_reg_doc_sha):
        key = (persona, cell, prompt_index, trial_index)
        if key in failing_tuples:
            raise RuntimeError(f"synthetic failure for {key}")
        # Build a success record matching SUCCESS_RECORD_SCHEMA_KEYS.
        import datetime as _dt
        rec = {
            "cell": cell,
            "persona": persona,
            "prompt_index": prompt_index,
            "prompt_text": prompt_text,
            "trial_index": trial_index,
            "model": model,
            "model_slug": model_slug,
            "monologue_text": monologue_text,
            "monologue_sentence_count": mle._sentence_count(monologue_text),
            "response_text": response_text,
            "response_sentence_count": mle._sentence_count(response_text),
            "monologue_max_tokens": mle.CELL_MAX_TOKENS[cell],
            "monologue_actual_tokens": None,
            "timestamp_iso": _dt.datetime.now(_dt.timezone.utc)
                .replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
            "anima_v1_sha": anima_v1_sha,
            "pre_reg_doc_sha": pre_reg_doc_sha,
        }
        return rec

    monkeypatch.setattr(mle, "_run_single_trial", _stub_run_single_trial)
    monkeypatch.setattr(
        mle, "_make_adapter_for_model",
        lambda provider, slug: mock.Mock(name="fake_adapter"),
    )


def _read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


# ---- schema split (Fix 2.5) ---------------------------------------------


def test_success_and_error_schema_keys_are_split(mle):
    """SUCCESS_RECORD_SCHEMA_KEYS keeps the original 16-key shape;
    ERROR_RECORD_SCHEMA_KEYS is the new error shape; RECORD_SCHEMA_KEYS
    is an alias to SUCCESS for backward-compat with existing tests."""
    assert hasattr(mle, "SUCCESS_RECORD_SCHEMA_KEYS")
    assert hasattr(mle, "ERROR_RECORD_SCHEMA_KEYS")
    # SUCCESS shape unchanged from the original RECORD_SCHEMA_KEYS.
    assert mle.SUCCESS_RECORD_SCHEMA_KEYS == (
        "cell", "persona", "prompt_index", "prompt_text", "trial_index",
        "model", "model_slug", "monologue_text", "monologue_sentence_count",
        "response_text", "response_sentence_count", "monologue_max_tokens",
        "monologue_actual_tokens", "timestamp_iso", "anima_v1_sha",
        "pre_reg_doc_sha",
    )
    # ERROR shape carries _error + identity + exception info + provenance.
    assert "_error" in mle.ERROR_RECORD_SCHEMA_KEYS
    for k in ("persona", "cell", "prompt_index", "trial_index", "model",
              "model_slug", "exception_class", "exception_message",
              "timestamp_iso", "anima_v1_sha", "pre_reg_doc_sha"):
        assert k in mle.ERROR_RECORD_SCHEMA_KEYS, f"missing error key {k}"
    # Backward-compat alias.
    assert mle.RECORD_SCHEMA_KEYS == mle.SUCCESS_RECORD_SCHEMA_KEYS


# ---- resume: skip already-completed tuples ------------------------------


def test_resume_skips_completed_tuples(mle, tmp_path, monkeypatch):
    """If the output file exists with successful records, those tuples
    must be removed from the run plan. Only the remaining tuples should
    be re-executed."""
    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    out_path = (
        out_dir / "2026-05-16_monologue_length_primary_deepseek.jsonl"
    )
    # Pre-populate with two completed records (different tuples).
    completed_records = [
        {
            "cell": "short", "persona": "marcus",
            "prompt_index": 0, "trial_index": 0,
            "prompt_text": "p0", "model": "deepseek",
            "model_slug": "deepseek/deepseek-v4-flash",
            "monologue_text": "x.", "monologue_sentence_count": 1,
            "response_text": "y.", "response_sentence_count": 1,
            "monologue_max_tokens": 120, "monologue_actual_tokens": None,
            "timestamp_iso": "2026-05-16T00:00:00Z",
            "anima_v1_sha": "pre", "pre_reg_doc_sha": "pre",
        },
        {
            "cell": "short", "persona": "marcus",
            "prompt_index": 0, "trial_index": 1,
            "prompt_text": "p0", "model": "deepseek",
            "model_slug": "deepseek/deepseek-v4-flash",
            "monologue_text": "x.", "monologue_sentence_count": 1,
            "response_text": "y.", "response_sentence_count": 1,
            "monologue_max_tokens": 120, "monologue_actual_tokens": None,
            "timestamp_iso": "2026-05-16T00:00:00Z",
            "anima_v1_sha": "pre", "pre_reg_doc_sha": "pre",
        },
    ]
    with out_path.open("w") as fh:
        for r in completed_records:
            fh.write(json.dumps(r) + "\n")

    # We're running a tiny plan: marcus only, short only, 2 prompts, 2 trials
    # = 4 total. Two are already complete, so only 2 should be attempted.
    attempted: list[tuple] = []

    real_run_plan = mle._build_run_plan

    def _spy_run(*, persona, cell, prompt_index, prompt_text, trial_index,
                  model, model_slug, llm, anima_v1_sha, pre_reg_doc_sha):
        key = (persona, cell, prompt_index, trial_index)
        attempted.append(key)
        return {
            "cell": cell, "persona": persona,
            "prompt_index": prompt_index, "prompt_text": prompt_text,
            "trial_index": trial_index, "model": model,
            "model_slug": model_slug,
            "monologue_text": "ok.", "monologue_sentence_count": 1,
            "response_text": "ok.", "response_sentence_count": 1,
            "monologue_max_tokens": mle.CELL_MAX_TOKENS[cell],
            "monologue_actual_tokens": None,
            "timestamp_iso": "2026-05-16T00:00:01Z",
            "anima_v1_sha": anima_v1_sha,
            "pre_reg_doc_sha": pre_reg_doc_sha,
        }

    monkeypatch.setattr(mle, "_run_single_trial", _spy_run)
    monkeypatch.setattr(
        mle, "_make_adapter_for_model",
        lambda provider, slug: mock.Mock(name="fake"),
    )
    # Force a synthetic prompts load returning just 2 prompts so we can
    # exercise the resume logic with a small plan.
    monkeypatch.setattr(
        mle, "_load_prompts",
        lambda src: (["p0", "p1"], tmp_path / "fake_prompts.json"),
    )

    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "2",
        "--personas", "marcus",
        "--cells", "short",
        "--skip-integrity-check",
    ])
    assert rc == 0, f"expected 0 from resume run; got {rc}"
    # The two already-completed tuples must NOT be re-attempted.
    assert (("marcus", "short", 0, 0)) not in attempted
    assert (("marcus", "short", 0, 1)) not in attempted
    # The remaining two tuples MUST be attempted.
    attempted_set = set(attempted)
    assert ("marcus", "short", 1, 0) in attempted_set
    assert ("marcus", "short", 1, 1) in attempted_set
    assert len(attempted) == 2
    # Output file now has 4 successful records (2 preloaded + 2 fresh).
    on_disk = _read_jsonl(out_path)
    assert len(on_disk) == 4
    assert all(not r.get("_error") for r in on_disk)


def test_resume_all_complete_exits_zero_immediately(
    mle, tmp_path, monkeypatch,
):
    """If every plan tuple is already on disk, main() exits 0 without
    constructing an adapter."""
    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    out_path = (
        out_dir / "2026-05-16_monologue_length_primary_deepseek.jsonl"
    )
    # Plan = 1 persona x 1 cell x 1 prompt x 1 trial = 1.
    record = {
        "cell": "short", "persona": "marcus",
        "prompt_index": 0, "trial_index": 0,
        "prompt_text": "p0", "model": "deepseek",
        "model_slug": "deepseek/deepseek-v4-flash",
        "monologue_text": "x.", "monologue_sentence_count": 1,
        "response_text": "y.", "response_sentence_count": 1,
        "monologue_max_tokens": 120, "monologue_actual_tokens": None,
        "timestamp_iso": "2026-05-16T00:00:00Z",
        "anima_v1_sha": "pre", "pre_reg_doc_sha": "pre",
    }
    with out_path.open("w") as fh:
        fh.write(json.dumps(record) + "\n")

    def _explode(*args, **kwargs):
        raise AssertionError("adapter should not be built when already complete")

    monkeypatch.setattr(mle, "_make_adapter_for_model", _explode)
    monkeypatch.setattr(mle, "_run_single_trial", _explode)
    monkeypatch.setattr(
        mle, "_load_prompts",
        lambda src: (["p0"], tmp_path / "fake.json"),
    )

    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "1",
        "--personas", "marcus",
        "--cells", "short",
        "--skip-integrity-check",
    ])
    assert rc == 0, f"expected 0; got {rc}"
    # The single record on disk was not duplicated.
    on_disk = _read_jsonl(out_path)
    assert len(on_disk) == 1


# ---- resume: malformed JSONL refused ------------------------------------


def test_resume_corrupted_jsonl_refused(mle, tmp_path, monkeypatch):
    """A malformed line in the existing output causes main() to refuse to
    start (exit code 8 — distinct from 'all good' 0). We must NOT silently
    overwrite or append to a corrupted file."""
    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    out_path = (
        out_dir / "2026-05-16_monologue_length_primary_deepseek.jsonl"
    )
    # One valid record followed by a garbage line.
    valid = {
        "cell": "short", "persona": "marcus",
        "prompt_index": 0, "trial_index": 0,
        "prompt_text": "p0", "model": "deepseek",
        "model_slug": "deepseek/deepseek-v4-flash",
        "monologue_text": "x.", "monologue_sentence_count": 1,
        "response_text": "y.", "response_sentence_count": 1,
        "monologue_max_tokens": 120, "monologue_actual_tokens": None,
        "timestamp_iso": "2026-05-16T00:00:00Z",
        "anima_v1_sha": "pre", "pre_reg_doc_sha": "pre",
    }
    with out_path.open("w") as fh:
        fh.write(json.dumps(valid) + "\n")
        fh.write("this is { not valid json\n")  # corrupt line

    def _explode(*args, **kwargs):
        raise AssertionError("must not build adapter when JSONL is malformed")

    monkeypatch.setattr(mle, "_make_adapter_for_model", _explode)
    monkeypatch.setattr(mle, "_run_single_trial", _explode)
    monkeypatch.setattr(
        mle, "_load_prompts",
        lambda src: (["p0"], tmp_path / "fake.json"),
    )

    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "1",
        "--personas", "marcus",
        "--cells", "short",
        "--skip-integrity-check",
    ])
    assert rc == 8, f"expected refusal exit code 8; got {rc}"
    # The corrupt file is NOT overwritten — both original lines remain.
    contents = out_path.read_text()
    assert "this is { not valid json" in contents
    # The valid line is still there too (we read but didn't write).
    assert '"trial_index": 0' in contents


def test_load_existing_records_basic(mle, tmp_path):
    """_load_existing_records returns the right completed-tuple set,
    success count, and error count."""
    path = tmp_path / "out.jsonl"
    records = [
        # Two successful records.
        {"cell": "short", "persona": "marcus",
         "prompt_index": 0, "trial_index": 0},
        {"cell": "short", "persona": "marcus",
         "prompt_index": 1, "trial_index": 0},
        # One error record (must NOT count toward completed_tuples).
        {"_error": True, "cell": "short", "persona": "jamie",
         "prompt_index": 0, "trial_index": 0,
         "exception_class": "X", "exception_message": "bad",
         "model": "deepseek", "model_slug": "deepseek/deepseek-v4-flash",
         "timestamp_iso": "2026-05-16T00:00:00Z",
         "anima_v1_sha": "x", "pre_reg_doc_sha": "x"},
    ]
    with path.open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    completed, n_succ, n_err = mle._load_existing_records(path)
    assert n_succ == 2
    assert n_err == 1
    assert completed == {
        ("marcus", "short", 0, 0),
        ("marcus", "short", 1, 0),
    }
    # The errored tuple is NOT in completed — it must be re-attempted.
    assert ("jamie", "short", 0, 0) not in completed


def test_load_existing_records_raises_on_bad_json(mle, tmp_path):
    """A bad line raises MalformedJsonlError."""
    path = tmp_path / "out.jsonl"
    path.write_text("not json\n")
    with pytest.raises(mle.MalformedJsonlError):
        mle._load_existing_records(path)


def test_iter_success_records_filters_errors(mle, tmp_path):
    """_iter_success_records yields only successful records, skipping
    `_error: true` records silently."""
    path = tmp_path / "out.jsonl"
    records = [
        {"cell": "short", "persona": "m", "prompt_index": 0, "trial_index": 0,
         "marker": "first"},
        {"_error": True, "cell": "short", "persona": "m",
         "prompt_index": 1, "trial_index": 0, "exception_class": "X",
         "exception_message": "bad"},
        {"cell": "short", "persona": "m", "prompt_index": 2, "trial_index": 0,
         "marker": "second"},
    ]
    with path.open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    got = list(mle._iter_success_records(path))
    assert len(got) == 2
    assert [r["marker"] for r in got] == ["first", "second"]


# ---- error records persisted on per-trial exception ---------------------


def test_error_record_written_on_partial_failure(
    mle, tmp_path, monkeypatch,
):
    """When some trials raise, the harness must:
      - persist an error record per failure
      - keep going (successes still written)
      - exit 6 (partial)
      - emit a summary log line with the counts."""
    out_dir = tmp_path / "reports"
    failing = {("marcus", "short", 0, 0)}  # one of four trials fails
    _install_fake_adapter_and_anima(monkeypatch, mle, failing_tuples=failing)
    monkeypatch.setattr(
        mle, "_load_prompts",
        lambda src: (["p0", "p1"], tmp_path / "fake.json"),
    )

    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "2",
        "--personas", "marcus",
        "--cells", "short",
        "--skip-integrity-check",
    ])
    assert rc == 6, f"expected partial-failure exit 6; got {rc}"

    out_path = (
        out_dir / "2026-05-16_monologue_length_primary_deepseek.jsonl"
    )
    on_disk = _read_jsonl(out_path)
    # 3 successes + 1 error record.
    assert len(on_disk) == 4
    errors = [r for r in on_disk if r.get("_error")]
    successes = [r for r in on_disk if not r.get("_error")]
    assert len(errors) == 1
    assert len(successes) == 3
    # The error record carries the right identity + exception info.
    err = errors[0]
    assert err["persona"] == "marcus"
    assert err["cell"] == "short"
    assert err["prompt_index"] == 0
    assert err["trial_index"] == 0
    assert err["exception_class"] == "RuntimeError"
    assert "synthetic failure" in err["exception_message"]
    # Provenance keys present.
    assert "timestamp_iso" in err
    assert "anima_v1_sha" in err
    assert "pre_reg_doc_sha" in err


def test_total_failure_exits_seven(mle, tmp_path, monkeypatch):
    """When EVERY trial raises, exit code is 7 (total failure), not 6."""
    out_dir = tmp_path / "reports"
    # All 2 trials will fail.
    failing = {
        ("marcus", "short", 0, 0),
        ("marcus", "short", 1, 0),
    }
    _install_fake_adapter_and_anima(monkeypatch, mle, failing_tuples=failing)
    monkeypatch.setattr(
        mle, "_load_prompts",
        lambda src: (["p0", "p1"], tmp_path / "fake.json"),
    )

    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "1",
        "--personas", "marcus",
        "--cells", "short",
        "--skip-integrity-check",
    ])
    assert rc == 7, f"expected total-failure exit 7; got {rc}"
    out_path = (
        out_dir / "2026-05-16_monologue_length_primary_deepseek.jsonl"
    )
    on_disk = _read_jsonl(out_path)
    assert len(on_disk) == 2
    assert all(r.get("_error") for r in on_disk)


def test_all_success_exits_zero(mle, tmp_path, monkeypatch):
    """When no trials fail, exit code is 0."""
    out_dir = tmp_path / "reports"
    _install_fake_adapter_and_anima(
        monkeypatch, mle, failing_tuples=set(),
    )
    monkeypatch.setattr(
        mle, "_load_prompts",
        lambda src: (["p0"], tmp_path / "fake.json"),
    )

    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "1",
        "--personas", "marcus",
        "--cells", "short",
        "--skip-integrity-check",
    ])
    assert rc == 0, f"expected success exit 0; got {rc}"


def test_summary_log_line_emitted(mle, tmp_path, monkeypatch, capsys):
    """The final summary log line must appear on stderr with the right
    counts and success_rate to 3 decimals."""
    out_dir = tmp_path / "reports"
    # 1 failure out of 2 trials -> success_rate = 0.500
    failing = {("marcus", "short", 0, 0)}
    _install_fake_adapter_and_anima(monkeypatch, mle, failing_tuples=failing)
    monkeypatch.setattr(
        mle, "_load_prompts",
        lambda src: (["p0", "p1"], tmp_path / "fake.json"),
    )

    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "1",
        "--personas", "marcus",
        "--cells", "short",
        "--skip-integrity-check",
    ])
    assert rc == 6
    captured = capsys.readouterr()
    # "summary: written=1 errors=1 total=2 success_rate=0.500"
    assert "summary:" in captured.err
    assert "written=1" in captured.err
    assert "errors=1" in captured.err
    assert "total=2" in captured.err
    assert "success_rate=0.500" in captured.err


# ---- resume re-attempts previously-errored tuples -----------------------


def test_resume_reattempts_errored_tuples(mle, tmp_path, monkeypatch):
    """A previously-errored tuple on disk must be re-attempted, not skipped.
    Successful tuples are skipped as usual."""
    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    out_path = (
        out_dir / "2026-05-16_monologue_length_primary_deepseek.jsonl"
    )

    # Pre-populate: one success, one error.
    preload = [
        {
            "cell": "short", "persona": "marcus",
            "prompt_index": 0, "trial_index": 0,  # COMPLETED -> should skip
            "prompt_text": "p0", "model": "deepseek",
            "model_slug": "deepseek/deepseek-v4-flash",
            "monologue_text": "x.", "monologue_sentence_count": 1,
            "response_text": "y.", "response_sentence_count": 1,
            "monologue_max_tokens": 120, "monologue_actual_tokens": None,
            "timestamp_iso": "2026-05-16T00:00:00Z",
            "anima_v1_sha": "pre", "pre_reg_doc_sha": "pre",
        },
        {
            "_error": True,
            "persona": "marcus", "cell": "short",
            "prompt_index": 1, "trial_index": 0,  # ERRORED -> should re-attempt
            "model": "deepseek",
            "model_slug": "deepseek/deepseek-v4-flash",
            "exception_class": "RuntimeError",
            "exception_message": "earlier crash",
            "timestamp_iso": "2026-05-16T00:00:00Z",
            "anima_v1_sha": "pre", "pre_reg_doc_sha": "pre",
        },
    ]
    with out_path.open("w") as fh:
        for r in preload:
            fh.write(json.dumps(r) + "\n")

    attempted: list[tuple] = []

    def _spy_run(*, persona, cell, prompt_index, prompt_text, trial_index,
                  model, model_slug, llm, anima_v1_sha, pre_reg_doc_sha):
        key = (persona, cell, prompt_index, trial_index)
        attempted.append(key)
        return {
            "cell": cell, "persona": persona,
            "prompt_index": prompt_index, "prompt_text": prompt_text,
            "trial_index": trial_index, "model": model,
            "model_slug": model_slug,
            "monologue_text": "ok.", "monologue_sentence_count": 1,
            "response_text": "ok.", "response_sentence_count": 1,
            "monologue_max_tokens": mle.CELL_MAX_TOKENS[cell],
            "monologue_actual_tokens": None,
            "timestamp_iso": "2026-05-16T00:00:01Z",
            "anima_v1_sha": anima_v1_sha,
            "pre_reg_doc_sha": pre_reg_doc_sha,
        }

    monkeypatch.setattr(mle, "_run_single_trial", _spy_run)
    monkeypatch.setattr(
        mle, "_make_adapter_for_model",
        lambda provider, slug: mock.Mock(name="fake"),
    )
    monkeypatch.setattr(
        mle, "_load_prompts",
        lambda src: (["p0", "p1"], tmp_path / "fake.json"),
    )

    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "1",
        "--personas", "marcus",
        "--cells", "short",
        "--skip-integrity-check",
    ])
    assert rc == 0
    attempted_set = set(attempted)
    # Previously-successful tuple is NOT re-attempted.
    assert ("marcus", "short", 0, 0) not in attempted_set
    # Previously-errored tuple IS re-attempted.
    assert ("marcus", "short", 1, 0) in attempted_set
    assert len(attempted) == 1


def test_resume_log_message_format(mle, tmp_path, monkeypatch, capsys):
    """The resume log line must include X/Y completed and Z remaining."""
    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    out_path = (
        out_dir / "2026-05-16_monologue_length_primary_deepseek.jsonl"
    )
    # 1 successful record out of a plan of 2.
    preload = {
        "cell": "short", "persona": "marcus",
        "prompt_index": 0, "trial_index": 0,
        "prompt_text": "p0", "model": "deepseek",
        "model_slug": "deepseek/deepseek-v4-flash",
        "monologue_text": "x.", "monologue_sentence_count": 1,
        "response_text": "y.", "response_sentence_count": 1,
        "monologue_max_tokens": 120, "monologue_actual_tokens": None,
        "timestamp_iso": "2026-05-16T00:00:00Z",
        "anima_v1_sha": "pre", "pre_reg_doc_sha": "pre",
    }
    with out_path.open("w") as fh:
        fh.write(json.dumps(preload) + "\n")

    _install_fake_adapter_and_anima(monkeypatch, mle, failing_tuples=set())
    monkeypatch.setattr(
        mle, "_load_prompts",
        lambda src: (["p0", "p1"], tmp_path / "fake.json"),
    )

    rc = mle.main([
        "--source", "primary",
        "--model", "deepseek",
        "--output-dir", str(out_dir),
        "--trials", "1",
        "--personas", "marcus",
        "--cells", "short",
        "--skip-integrity-check",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "resuming:" in captured.err
    # Full plan is 1 persona * 1 cell * 2 prompts * 1 trial = 2.
    assert "1/2 already complete" in captured.err
    assert "1 remaining" in captured.err
