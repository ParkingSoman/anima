"""Memory retrieval — step 2 of the turn loop (master plan §10).

Episodic recall is *reconstructive*, not playback. Conway & Pleydell-Pearce
(2000): autobiographical memory is built at retrieval time, shaped by current
goals, self-model, and affect. This subsystem implements that:

  1. Symbolic prefilter      — narrow the candidate pool from perception cues
  2. Numerical scoring       — mood-congruence + schema-relevance + recency +
                               importance, weighted sum normalized to [0,1]
  3. Top-k selection         — k=3 by default
  4. ONE fast-tier LLM call  — batch over k events, returns retrieval_reason
                               and reconstructed_framing per event (the
                               "Conway-style" interpretive recall)
  5. Bookkeeping             — increment retrieval_count on each retrieved id

Design notes:
  - Numerical ranker uses mood (valence/arousal/dominance) vs event.affect_tag
    cosine-similarity. Discrete dict is deferred to E4 (affect-congruence).
  - importance is read directly off event.importance — no decay (E4 work).
  - The LLM call is batched (k events in, k {reason, framing} pairs out) so
    cost stays at ≤1 LLM call per turn regardless of k.
  - Empty store / k=0 short-circuits to []. No LLM call in those cases.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from anima.llm.base import LLMAdapter
from anima.state.episodic import EpisodicEvent, EpisodicStore
from anima.state.mood import MoodVector
from anima.state.self_model import SelfModel
from anima.subsystems._common import extract_json
from anima.subsystems.perception import Perception


# Weights for the ranker. Sum to 1.0 so the score is in [0,1].
_W_MOOD = 0.35
_W_SCHEMA = 0.25
_W_RECENCY = 0.20
_W_IMPORTANCE = 0.20


@dataclass
class RetrievedMemory:
    event: EpisodicEvent
    score: float                  # ranker score in [0, 1]
    retrieval_reason: str         # one-sentence: why is this surfacing right now
    reconstructed_framing: str    # Conway-style: how the Anima recalls this RIGHT NOW


_INSTR = """You are the MEMORY RETRIEVAL subsystem of a cognitive architecture
that simulates a specific person. You do NOT decide what memories surface — a
numerical ranker has already done that. Your job is to render, for each
already-selected memory, two short texts:

  retrieval_reason       : ONE sentence — why is this particular memory
                           surfacing for this person right now, given their
                           current self-model, mood, and active schemas?
  reconstructed_framing  : ONE-to-TWO sentences in first-person — how the
                           person RECALLS this event RIGHT NOW. Memory is
                           reconstructive, not playback (Conway & Pleydell-
                           Pearce). The framing should be coloured by who the
                           person currently is, their current mood, and their
                           active schemas. The same event can be recalled with
                           warmth on one day and with bitterness on another.
                           Do not replay raw content — interpret it.

You will receive a list of candidate events. For EACH, produce one
{retrieval_reason, reconstructed_framing} pair.

Output a single JSON object with this shape:
  {"items": [
      {"id": "<event-id>", "retrieval_reason": "...", "reconstructed_framing": "..."},
      ...
   ]}

Preserve the order and ids of the input candidates. Return ONLY the JSON.
"""


def _cosine_3vec(av: float, aa: float, ad: float,
                 bv: float, ba: float, bd: float) -> float:
    """Cosine similarity between two 3-vectors. Defined in [-1, 1]; if either
    vector is zero, returns 0.0 (neutral)."""
    na = math.sqrt(av * av + aa * aa + ad * ad)
    nb = math.sqrt(bv * bv + ba * ba + bd * bd)
    if na <= 1e-9 or nb <= 1e-9:
        return 0.0
    dot = av * bv + aa * ba + ad * bd
    return max(-1.0, min(1.0, dot / (na * nb)))


def _mood_congruence(mood: MoodVector, event: EpisodicEvent) -> float:
    """Cosine similarity between mood VAD and event affect VAD, mapped to [0,1]."""
    cos = _cosine_3vec(
        mood.valence, mood.arousal, mood.dominance,
        event.affect_tag.valence, event.affect_tag.arousal, event.affect_tag.dominance,
    )
    return (cos + 1.0) / 2.0  # [-1,1] -> [0,1]


def _schema_relevance(event: EpisodicEvent, active_schemas: list[str]) -> float:
    """1.0 if any active-schema string appears as a substring in the event
    summary or full content; else 0.0. Case-insensitive."""
    if not active_schemas:
        return 0.0
    hay = (event.content_summary + " " + event.full_content).lower()
    for s in active_schemas:
        if s and s.lower() in hay:
            return 1.0
    return 0.0


def _recency_score(event: EpisodicEvent, all_events: list[EpisodicEvent]) -> float:
    """Rank-based recency: most-recent event scores 1.0, oldest scores 0.0.
    Lex-comparable on ISO-8601 timestamps. With a single event, returns 1.0.
    """
    if len(all_events) <= 1:
        return 1.0
    sorted_ts = sorted({e.ts for e in all_events})
    if len(sorted_ts) == 1:
        return 1.0
    idx = sorted_ts.index(event.ts)
    return idx / (len(sorted_ts) - 1)


def _score_event(event: EpisodicEvent, *, mood: MoodVector,
                 active_schemas: list[str], all_events: list[EpisodicEvent]) -> float:
    mood_c = _mood_congruence(mood, event)                  # [0,1]
    schema_r = _schema_relevance(event, active_schemas)     # 0 or 1
    recency = _recency_score(event, all_events)             # [0,1]
    importance = max(0.0, min(1.0, event.importance))       # [0,1]
    score = (_W_MOOD * mood_c
             + _W_SCHEMA * schema_r
             + _W_RECENCY * recency
             + _W_IMPORTANCE * importance)
    # Weights sum to 1.0, so score is already in [0,1]. Clamp defensively.
    return max(0.0, min(1.0, score))


def _extract_keywords(perception: Perception) -> list[str]:
    """Crude keyword extraction from perception.salient_features +
    perception.perceived_demands. Keeps tokens of length >= 4. Lowercase.
    Returns up to ~12 tokens; we treat the resulting list as a *disjunctive*
    prefilter (any hit is a candidate) rather than ANDed, because the store's
    filter_by uses AND-semantics — so for prefiltering we instead union over
    per-keyword filter_by calls.
    """
    raw: list[str] = []
    for s in (perception.salient_features or []):
        raw.append(str(s))
    for d in (perception.perceived_demands or []):
        raw.append(str(d))
    tokens: list[str] = []
    seen: set[str] = set()
    for phrase in raw:
        for tok in phrase.lower().replace(",", " ").replace(";", " ").split():
            tok = tok.strip(".:;,!?()[]\"'")
            if len(tok) >= 4 and tok not in seen:
                seen.add(tok)
                tokens.append(tok)
            if len(tokens) >= 12:
                return tokens
    return tokens


class MemoryRetrieval:
    """Phase-2 reconstructive episodic retrieval."""

    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def run(
        self,
        *,
        perception: Perception,
        perception_view: str,
        self_model: SelfModel,
        mood: MoodVector,
        active_schemas: list[str],
        episodic_store: EpisodicStore,
        k: int = 3,
    ) -> list[RetrievedMemory]:
        # Short-circuit on degenerate inputs — no LLM call.
        if k <= 0 or not episodic_store.events:
            return []

        # 1. Symbolic prefilter. Build a candidate pool by unioning per-keyword
        # filter_by hits. If perception yields no useful keywords, fall back to
        # the most-recent 20 events.
        keywords = _extract_keywords(perception)
        candidates: list[EpisodicEvent] = []
        if keywords:
            seen_ids: set[str] = set()
            for kw in keywords:
                for ev in episodic_store.filter_by(topic_keywords=[kw]):
                    if ev.id not in seen_ids:
                        seen_ids.add(ev.id)
                        candidates.append(ev)
        if not candidates:
            candidates = episodic_store.list_recent(20)

        # 2. Score each candidate.
        all_events = episodic_store.events
        scored: list[tuple[float, EpisodicEvent]] = [
            (_score_event(ev, mood=mood, active_schemas=active_schemas,
                          all_events=all_events), ev)
            for ev in candidates
        ]
        # 3. Top-k by score (stable order ties by ts desc as a tiebreaker).
        scored.sort(key=lambda pair: (pair[0], pair[1].ts), reverse=True)
        top = scored[:k]

        if not top:
            return []

        # 4. ONE fast-tier LLM call for retrieval_reason + reconstructed_framing.
        candidates_block = self._render_candidates_for_llm(top)
        active_schemas_str = ", ".join(active_schemas) if active_schemas else "none salient"
        system = (
            _INSTR + "\n\n"
            + self_model.render() + "\n\n"
            + mood.render() + "\n\n"
            + f"--- active schemas right now ---\n{active_schemas_str}\n--- end schemas ---\n\n"
            + perception_view
        )
        msgs = [{"role": "user", "content":
                 f"Candidate memories the ranker just selected:\n\n{candidates_block}\n\n"
                 f"For each, return retrieval_reason and reconstructed_framing. JSON only."}]
        resp = self.llm.generate(tier="fast", system=system, messages=msgs,
                                 max_tokens=600, temperature=0.6)
        parsed = extract_json(resp.text) or {}
        items_by_id: dict[str, dict] = {}
        for item in (parsed.get("items") or []):
            if not isinstance(item, dict):
                continue
            eid = str(item.get("id", ""))
            if eid:
                items_by_id[eid] = item

        # 5. Build RetrievedMemory list + mark_retrieved.
        retrieved: list[RetrievedMemory] = []
        for score, ev in top:
            item = items_by_id.get(ev.id, {})
            reason = str(item.get("retrieval_reason") or
                         "this memory came up in association with the current moment")[:400]
            framing = str(item.get("reconstructed_framing") or
                          ev.content_summary)[:800]
            retrieved.append(RetrievedMemory(
                event=ev,
                score=float(score),
                retrieval_reason=reason,
                reconstructed_framing=framing,
            ))
            episodic_store.mark_retrieved(ev.id)
        return retrieved

    def render(self, retrieved: list[RetrievedMemory]) -> str:
        """Render as a prompt-ready block for downstream subsystems."""
        if not retrieved:
            return (
                "--- memories surfacing ---\n"
                "(no relevant memories surface right now)\n"
                "--- end memories ---"
            )
        lines = ["--- memories surfacing ---"]
        for i, rm in enumerate(retrieved, start=1):
            lines.append(
                f"[{i}] (score={rm.score:.2f}) {rm.event.content_summary}"
            )
            lines.append(f"    how I recall it now: {rm.reconstructed_framing}")
            lines.append(f"    why it surfaced: {rm.retrieval_reason}")
        lines.append("--- end memories ---")
        return "\n".join(lines)

    # ---------- internal

    @staticmethod
    def _render_candidates_for_llm(scored: list[tuple[float, EpisodicEvent]]) -> str:
        rows: list[str] = []
        for score, ev in scored:
            rows.append(
                f"- id: {ev.id}\n"
                f"  ts: {ev.ts}\n"
                f"  summary: {ev.content_summary}\n"
                f"  participants: {', '.join(ev.participants)}\n"
                f"  affect (then): valence={ev.affect_tag.valence:+.2f}, "
                f"arousal={ev.affect_tag.arousal:+.2f}, dominance={ev.affect_tag.dominance:+.2f}\n"
                f"  importance: {ev.importance:.2f}; ranker_score: {score:.2f}\n"
                f"  full_content: {ev.full_content[:400]}"
            )
        return "\n".join(rows)
