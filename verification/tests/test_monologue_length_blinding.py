"""Tests for the monologue-length blinding stage.

Verifies determinism, criterion-independence, group-independence,
metadata leakage prevention, and group UUID reproducibility.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make the script importable. ``verification/scripts/`` isn't a package
# and the filename starts with a date, so we load it via importlib.
import importlib.util

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    PROJECT_ROOT
    / "verification"
    / "scripts"
    / "2026-05-16_monologue_length_blinding.py"
)

_spec = importlib.util.spec_from_file_location(
    "monologue_length_blinding", SCRIPT_PATH
)
assert _spec is not None and _spec.loader is not None
blinding = importlib.util.module_from_spec(_spec)
sys.modules["monologue_length_blinding"] = blinding
_spec.loader.exec_module(blinding)


# ---- helpers ----------------------------------------------------------

def _mk_record(
    *,
    persona: str,
    cell: str,
    prompt_index: int,
    trial_index: int,
    prompt_text: str = "What did you feel?",
    response_text: str | None = None,
    monologue_text: str = "internal monologue here",
    model: str = "mistral",
) -> dict:
    if response_text is None:
        response_text = f"{persona}-{cell}-{prompt_index}-{trial_index}"
    return {
        "cell": cell,
        "persona": persona,
        "prompt_index": prompt_index,
        "trial_index": trial_index,
        "prompt_text": prompt_text,
        "response_text": response_text,
        "monologue_text": monologue_text,
        "monologue_sentence_count": 2,
        "response_sentence_count": 1,
        "model": model,
        "model_slug": "x/y",
        "monologue_max_tokens": 120,
        "monologue_actual_tokens": None,
        "timestamp_iso": "2026-05-16T00:00:00Z",
        "anima_v1_sha": "abc",
        "pre_reg_doc_sha": "def",
    }


def _full_group(persona: str, prompt_index: int, trial_index: int) -> list[dict]:
    return [
        _mk_record(persona=persona, cell="variable",
                   prompt_index=prompt_index, trial_index=trial_index),
        _mk_record(persona=persona, cell="short",
                   prompt_index=prompt_index, trial_index=trial_index),
        _mk_record(persona=persona, cell="long",
                   prompt_index=prompt_index, trial_index=trial_index),
    ]


# ---- determinism tests ------------------------------------------------

def test_permutation_is_deterministic_for_same_seed_and_group():
    """Same (persona, prompt_index, trial_index, criterion, seed) ->
    identical label permutation across invocations."""
    a = blinding.assign_labels(
        persona="marcus", prompt_index=3, trial_index=7,
        criterion="emotional-inhibition", seed=42,
    )
    b = blinding.assign_labels(
        persona="marcus", prompt_index=3, trial_index=7,
        criterion="emotional-inhibition", seed=42,
    )
    assert a == b
    # And the labels A/B/C cover all three cells.
    assert sorted(a.values()) == ["long", "short", "variable"]


def test_permutation_differs_across_criteria_for_same_group():
    """For the same group, different criteria should usually produce
    different permutations. We sample all 4 Marcus criteria; with 6
    permutations of 3 elements, at least two of them should differ."""
    perms = set()
    for criterion in (
        "intellectualization-as-defense",
        "isolation-of-affect",
        "emotional-inhibition",
        "avoidant-deflection",
    ):
        p = blinding.assign_labels(
            persona="marcus", prompt_index=2, trial_index=5,
            criterion=criterion, seed=42,
        )
        perms.add(tuple(sorted(p.items())))
    assert len(perms) > 1, (
        f"all 4 criteria produced identical permutation: {perms}"
    )


def test_permutation_differs_across_groups_for_same_criterion():
    """Different groups under the same criterion should usually produce
    different permutations across a reasonable sample."""
    perms = set()
    for trial_index in range(1, 17):  # 16 groups
        p = blinding.assign_labels(
            persona="jamie", prompt_index=1, trial_index=trial_index,
            criterion="warmth", seed=42,
        )
        perms.add(tuple(sorted(p.items())))
    assert len(perms) > 1, (
        f"all 16 groups produced identical permutation: {perms}"
    )


# ---- group_uuid reproducibility ---------------------------------------

def test_group_uuid_is_reproducible_from_input_identity():
    u1 = blinding.group_uuid(
        model="mistral", persona="marcus", prompt_index=5,
        trial_index=12, criterion="isolation-of-affect",
    )
    u2 = blinding.group_uuid(
        model="mistral", persona="marcus", prompt_index=5,
        trial_index=12, criterion="isolation-of-affect",
    )
    assert u1 == u2
    # Changing any component should change the UUID.
    u3 = blinding.group_uuid(
        model="deepseek", persona="marcus", prompt_index=5,
        trial_index=12, criterion="isolation-of-affect",
    )
    u4 = blinding.group_uuid(
        model="mistral", persona="jamie", prompt_index=5,
        trial_index=12, criterion="isolation-of-affect",
    )
    u5 = blinding.group_uuid(
        model="mistral", persona="marcus", prompt_index=6,
        trial_index=12, criterion="isolation-of-affect",
    )
    u6 = blinding.group_uuid(
        model="mistral", persona="marcus", prompt_index=5,
        trial_index=13, criterion="isolation-of-affect",
    )
    u7 = blinding.group_uuid(
        model="mistral", persona="marcus", prompt_index=5,
        trial_index=12, criterion="emotional-inhibition",
    )
    assert len({u1, u3, u4, u5, u6, u7}) == 6


# ---- metadata leakage prevention -------------------------------------

FORBIDDEN_KEYS = {
    "persona", "cell", "monologue_text", "monologue_sentence_count",
    "model", "model_slug", "prompt_index", "trial_index", "timestamp_iso",
    "anima_v1_sha", "pre_reg_doc_sha", "response_sentence_count",
    "monologue_max_tokens", "monologue_actual_tokens",
}


def test_blinded_input_has_no_persona_cell_monologue_or_metadata(tmp_path):
    """End-to-end: run main() and verify blinded files contain ONLY
    the four allowed keys (group_uuid, question, response_A/B/C)."""
    # Build a synthetic harness file: 2 prompts x 2 trials x 2 personas
    # x 3 cells = 24 records.
    recs: list[dict] = []
    for persona in ("marcus", "jamie"):
        for prompt_index in (1, 2):
            for trial_index in (10, 11):
                recs.extend(_full_group(persona, prompt_index, trial_index))
    # Toss in an _error record that must be skipped.
    recs.append({
        "_error": True, "persona": "marcus", "cell": "short",
        "prompt_index": 1, "trial_index": 99, "model": "mistral",
    })
    input_path = tmp_path / "harness.jsonl"
    with input_path.open("w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    output_dir = tmp_path / "blinded"
    rc = blinding.main([
        "--input", str(input_path),
        "--model", "mistral",
        "--output-dir", str(output_dir),
        "--seed", "42",
    ])
    assert rc == 0

    # 8 blinded files + 8 mapping files.
    blinded_files = sorted(output_dir.glob("blinded_mistral_*.jsonl"))
    mapping_files = sorted(output_dir.glob("mapping_mistral_*.jsonl"))
    assert len(blinded_files) == 8, (
        f"expected 8 blinded files, got {[p.name for p in blinded_files]}"
    )
    assert len(mapping_files) == 8

    allowed = {"group_uuid", "question", "response_A", "response_B",
               "response_C"}
    for bf in blinded_files:
        for ln_no, line in enumerate(bf.read_text().splitlines(), start=1):
            rec = json.loads(line)
            extra = set(rec) - allowed
            missing = allowed - set(rec)
            assert not extra, (
                f"{bf.name}:{ln_no}: extra keys {extra} in blinded record"
            )
            assert not missing, (
                f"{bf.name}:{ln_no}: missing keys {missing}"
            )
            for k in FORBIDDEN_KEYS:
                assert k not in rec, (
                    f"{bf.name}:{ln_no}: forbidden key {k!r} leaked "
                    f"into blinded record"
                )
            # And no value should contain the literal monologue text.
            blob = json.dumps(rec)
            assert "internal monologue here" not in blob, (
                f"{bf.name}:{ln_no}: monologue text leaked into blinded "
                f"record"
            )

    # Mapping files MUST contain the cell labels (this is their job).
    expected_mapping_keys = {
        "group_uuid", "persona", "prompt_index", "trial_index",
        "model", "criterion", "label_to_cell",
    }
    for mf in mapping_files:
        for ln_no, line in enumerate(mf.read_text().splitlines(), start=1):
            rec = json.loads(line)
            assert set(rec) == expected_mapping_keys, (
                f"{mf.name}:{ln_no}: unexpected mapping keys "
                f"{set(rec)} (want {expected_mapping_keys})"
            )
            assert set(rec["label_to_cell"]) == {"A", "B", "C"}
            assert set(rec["label_to_cell"].values()) == {
                "variable", "short", "long"
            }


def test_per_criterion_record_count_matches_groups(tmp_path):
    """4 Marcus groups -> 4 records in each of the 4 Marcus criteria
    files; same for Jamie."""
    recs: list[dict] = []
    for persona in ("marcus", "jamie"):
        for prompt_index in (1, 2):
            for trial_index in (10, 11):
                recs.extend(_full_group(persona, prompt_index, trial_index))
    input_path = tmp_path / "harness.jsonl"
    with input_path.open("w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    output_dir = tmp_path / "blinded"
    rc = blinding.main([
        "--input", str(input_path),
        "--model", "mistral",
        "--output-dir", str(output_dir),
    ])
    assert rc == 0
    marcus_criteria = [
        "intellectualization-as-defense", "isolation-of-affect",
        "emotional-inhibition", "avoidant-deflection",
    ]
    jamie_criteria = [
        "warmth", "social-attunement", "humor-playfulness",
        "emotional-openness",
    ]
    for c in marcus_criteria + jamie_criteria:
        bf = output_dir / f"blinded_mistral_{c}.jsonl"
        lines = bf.read_text().splitlines()
        # 2 prompts * 2 trials = 4 groups per persona.
        assert len(lines) == 4, (
            f"{bf.name}: expected 4 records, got {len(lines)}"
        )


def test_uneven_group_is_logged_and_skipped(tmp_path, capsys):
    """A group with only 2 of the 3 cells must be skipped with a
    WARNING and not cause an error if the count works out after
    skipping. (Note: pre-flight will then fail if the total
    records-divided-by-3 doesn't match groups.) We test the skip path
    via the function directly."""
    recs = [
        _mk_record(persona="marcus", cell="variable",
                   prompt_index=1, trial_index=1),
        _mk_record(persona="marcus", cell="short",
                   prompt_index=1, trial_index=1),
        # missing "long"
    ]
    msgs: list[str] = []
    groups = blinding.group_records_for_persona(
        recs, "marcus", log=msgs.append
    )
    assert groups == {}
    assert any("SKIPPING" in m for m in msgs), msgs


def test_question_is_verbatim_prompt_text(tmp_path):
    """The blinded ``question`` field is the verbatim ``prompt_text``
    from the harness, unchanged."""
    custom_question = (
        "What did you feel when this happened? -- verbatim/long-form."
    )
    recs = [
        _mk_record(persona="marcus", cell=c, prompt_index=1,
                   trial_index=1, prompt_text=custom_question)
        for c in ("variable", "short", "long")
    ]
    input_path = tmp_path / "harness.jsonl"
    with input_path.open("w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    output_dir = tmp_path / "blinded"
    rc = blinding.main([
        "--input", str(input_path),
        "--model", "mistral",
        "--output-dir", str(output_dir),
    ])
    assert rc == 0
    bf = output_dir / "blinded_mistral_isolation-of-affect.jsonl"
    rec = json.loads(bf.read_text().splitlines()[0])
    assert rec["question"] == custom_question
