"""§11.3 Discriminability probe.

Generate short transcripts from each of N configurations on a shared list of
opening prompts. Then ask a blind LLM-as-judge to classify each transcript to
the most likely originating configuration, given only one-paragraph
descriptions of each candidate config. We report:

  - per-config classification accuracy
  - Cohen's κ vs chance
  - confusion matrix

For the MVP we have N=3 (Elena, Marcus, Jamie) and a small probe-set. For
publication-grade results, increase N, the probe-set, and use human raters.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field

from anima.config import AnimaConfig
from anima.llm.base import LLMAdapter


DEFAULT_PROMPTS = [
    "Hey, I haven't talked to you in a while. How have you been?",
    "Tell me about something that's been weighing on you lately.",
    "I had a kind of strange week. I don't even know where to start.",
    "If you could not work tomorrow and do anything you wanted, what would you actually do?",
    "Someone said something to me yesterday that hurt more than I expected. Has that ever happened to you?",
    "Be honest — what are you avoiding right now?",
]


def _short_blurb(cfg: AnimaConfig) -> str:
    return (
        f"{cfg.biography.name} — {cfg.biography.one_line} "
        f"Personality (Big5): O={cfg.big5.openness:.2f}, C={cfg.big5.conscientiousness:.2f}, "
        f"E={cfg.big5.extraversion:.2f}, A={cfg.big5.agreeableness:.2f}, N={cfg.big5.neuroticism:.2f}. "
        f"Attachment: {cfg.attachment.style.value}. "
        f"Top values: {', '.join(k for k, _ in cfg.schwartz.top_k(3))}. "
        f"Speaks with register: {cfg.demographics.language_register}."
    )


def transcript_for(subject, prompts: list[str], *, progress=None,
                   subject_label: str | None = None) -> list[dict]:
    """Run a fresh subject through the prompt list once, return turn-by-turn.

    `progress` (optional) is `Callable[[str], None]` invoked once per turn.
    `subject_label` is included in progress messages so caller can disambiguate
    multiple subjects.
    """
    turns = []
    total = len(prompts)
    label = subject_label or getattr(getattr(subject, "cfg", None), "biography", None)
    if label is not None and not isinstance(label, str):
        label = label.name
    for i, p in enumerate(prompts):
        if progress is not None:
            tag = f"({label}) " if label else ""
            progress(f"[discriminability] {tag}transcript turn {i+1}/{total}")
        reply, _ = subject.respond(p)
        turns.append({"user": p, "subject": reply})
    return turns


@dataclass
class DiscriminabilityResult:
    transcripts: list[dict] = field(default_factory=list)   # one per transcript: config_id, turns
    judgments: list[dict] = field(default_factory=list)
    accuracy: float = 0.0
    per_config_accuracy: dict[str, float] = field(default_factory=dict)
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)


_JUDGE_INSTR = """You are a blind judge. You will be shown a short conversation
transcript and a numbered list of candidate personas. The transcript was
produced by one of the candidates. Choose which one.

Output a single line in the format:
  ANSWER: <number>

where <number> is the integer corresponding to your best guess (1-indexed).
No prose, no explanation. Just `ANSWER: N`.
"""


def _ask_judge(judge_llm: LLMAdapter, transcript_turns: list[dict],
               candidates: list[AnimaConfig], rng: random.Random) -> tuple[int, str]:
    # Shuffle candidate order to avoid positional bias
    indices = list(range(len(candidates)))
    rng.shuffle(indices)
    numbered = "\n".join(
        f"  {i+1}. {_short_blurb(candidates[idx])}"
        for i, idx in enumerate(indices)
    )
    convo = "\n".join(
        f"PARTNER: {t['user']}\nSPEAKER: {t['subject']}"
        for t in transcript_turns
    )
    msg = (
        "Candidates:\n" + numbered + "\n\n"
        + "Transcript:\n" + convo + "\n\n"
        + "Which candidate is the SPEAKER most likely to be? Reply only `ANSWER: N`."
    )
    resp = judge_llm.generate(tier="strong", system=_JUDGE_INSTR,
                              messages=[{"role": "user", "content": msg}],
                              max_tokens=20, temperature=0.0)
    import re
    m = re.search(r"ANSWER:\s*(\d+)", resp.text)
    chosen = int(m.group(1)) - 1 if m else -1
    if 0 <= chosen < len(candidates):
        return indices[chosen], resp.text
    return -1, resp.text


def run(*, subject_factory, configs: list[AnimaConfig], prompts: list[str] | None = None,
        judge_llm: LLMAdapter, transcripts_per_config: int = 2,
        seed: int = 0, progress=None, subject_label: str | None = None,
        transcripts: list[dict] | None = None) -> DiscriminabilityResult:
    """`subject_factory(config) -> Anima-like subject` lets you run the probe
    against both the cognitive architecture and the baseline by passing
    different factories.

    `progress` (optional) is `Callable[[str], None]` invoked per turn and per
    judge call. `subject_label` is included in transcript-progress lines.

    `transcripts` (optional) lets a caller supply pre-generated transcripts
    (e.g. produced concurrently elsewhere) and skip the generation phase. If
    provided, must be a list of {"config_name", "turns"} dicts.
    """
    rng = random.Random(seed)
    use_prompts = prompts or DEFAULT_PROMPTS

    if transcripts is None:
        transcripts = []
        for cfg in configs:
            for _ in range(transcripts_per_config):
                subject = subject_factory(cfg)
                turns = transcript_for(subject, use_prompts, progress=progress,
                                       subject_label=subject_label or cfg.biography.name)
                transcripts.append({"config_name": cfg.biography.name, "turns": turns})

    known_names = {c.biography.name for c in configs}
    unknown = [t["config_name"] for t in transcripts if t.get("config_name") not in known_names]
    if unknown:
        raise ValueError(
            f"transcripts contain unknown config_name(s) not in `configs`: {unknown}. "
            f"Known names: {sorted(known_names)}"
        )

    judgments = []
    correct = 0
    confusion: dict[str, dict[str, int]] = {c.biography.name: Counter() for c in configs}
    name_to_cfg = {c.biography.name: c for c in configs}
    total_t = len(transcripts)
    for i, t in enumerate(transcripts):
        if progress is not None:
            tag = f"({subject_label}) " if subject_label else ""
            progress(f"[discriminability] {tag}judging transcript {i+1}/{total_t}")
        true_idx = next(i for i, c in enumerate(configs)
                        if c.biography.name == t["config_name"])
        chosen_idx, raw = _ask_judge(judge_llm, t["turns"], configs, rng)
        chosen_name = configs[chosen_idx].biography.name if chosen_idx >= 0 else "<unparsed>"
        judgments.append({
            "true": t["config_name"], "predicted": chosen_name, "raw_judge_output": raw,
        })
        confusion[t["config_name"]][chosen_name] = confusion[t["config_name"]].get(chosen_name, 0) + 1
        if chosen_idx == true_idx:
            correct += 1

    accuracy = correct / len(transcripts) if transcripts else 0.0
    per_config: dict[str, float] = {}
    for name in {t["config_name"] for t in transcripts}:
        total = sum(1 for t in transcripts if t["config_name"] == name)
        right = sum(1 for j in judgments if j["true"] == name and j["predicted"] == name)
        per_config[name] = right / total if total else 0.0

    return DiscriminabilityResult(
        transcripts=transcripts,
        judgments=judgments,
        accuracy=accuracy,
        per_config_accuracy=per_config,
        confusion={k: dict(v) for k, v in confusion.items()},
    )
