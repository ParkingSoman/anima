"""Per-Anima JSON-on-disk persistence (E5).

Master plan §5 distinguishes two storage regions with distinct semantic roles:

  - §5.1 BEHAVIORAL RECORD — what actually happened. Append-only,
    researcher-auditable, never pruned in Phase 2. Episodic events, action
    history (TurnTraces), session transcripts.

  - §5.2 INTERPRETED STATE — what the Anima believes / feels / wants. Updated
    each turn; this is what the Anima itself reads next turn. Self-model,
    semantic facts, relations, mood, drives.

These regions are kept as SEPARATE JSON files so a researcher can directly
compare "what was real" to "what the Anima thinks was real" — the architectural
substrate for §11.6 self-deception probes.

On-disk layout::

    <root>/<name>/
        behavioral_record.json        (§5.1)
        interpreted.json              (§5.2)
        transcripts/<session_id>.json (one file per session)

Atomicity: every write goes through a same-directory ``.tmp`` sibling and
``os.replace`` — atomic on POSIX and Windows for same-filesystem renames.
``shutil.move`` is deliberately avoided because it can fall back to copy+delete
and break atomicity.

Concurrency: single-writer. Phase 2 is single-process; no file locks here.
Phase 4 (offline consolidation) will adopt a writer protocol then.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AnimaStoreSnapshot:
    """In-memory representation matching the on-disk JSON layout.

    Field shape mirrors the JSON exactly so :meth:`AnimaStore.save` and
    :meth:`AnimaStore.load` are thin codecs over ``json.dump`` / ``json.load``.

    §5.1 behavioral record:
        ``episodic_events`` — list of serialized :class:`EpisodicEvent`
        ``action_history`` — list of serialized :class:`TurnTrace`

    §5.2 interpreted state:
        ``self_model`` — serialized :class:`SelfModel`
        ``semantic_facts`` — list of serialized :class:`SemanticFact`
        ``relations`` — mapping name -> serialized :class:`RelationalSchema`
        ``mood`` — serialized :class:`MoodVector`
        ``drives`` — serialized :class:`DriveState`

    Session bookkeeping (carried alongside, written into separate files):
        ``conversation_history`` — current in-session message log
        ``current_session_id`` — id of the active session (if any)
        ``transcripts_by_session`` — full per-session transcripts read back
          off disk on load(). Save only writes the *current* session's
          transcript file (others are left untouched, preserving prior runs).
    """

    # §5.1 behavioral record
    episodic_events: list[dict] = field(default_factory=list)
    action_history: list[dict] = field(default_factory=list)
    # §5.2 interpreted state
    self_model: dict = field(default_factory=dict)
    semantic_facts: list[dict] = field(default_factory=list)
    relations: dict = field(default_factory=dict)
    mood: dict = field(default_factory=dict)
    drives: dict = field(default_factory=dict)
    # session
    conversation_history: list[dict] = field(default_factory=list)
    current_session_id: str | None = None
    transcripts_by_session: dict[str, list[dict]] = field(default_factory=dict)


@dataclass
class AnimaStore:
    """Per-Anima JSON-on-disk persistence with §5.1/§5.2 separation.

    Single-writer. One Anima process owns one store. Cross-process coordination
    is out of scope for Phase 2.
    """

    name: str
    root: Path = field(default_factory=lambda: Path("anima_store"))

    # ---------- paths

    @property
    def dir(self) -> Path:
        """The per-Anima directory: ``<root>/<name>/``."""
        return Path(self.root) / self.name

    @property
    def behavioral_path(self) -> Path:
        return self.dir / "behavioral_record.json"

    @property
    def interpreted_path(self) -> Path:
        return self.dir / "interpreted.json"

    @property
    def transcripts_dir(self) -> Path:
        return self.dir / "transcripts"

    # ---------- load

    def load(self) -> AnimaStoreSnapshot | None:
        """Return a snapshot of the on-disk state, or ``None`` if no state
        exists yet (fresh Anima, first run).

        A store is considered to have on-disk state if EITHER the behavioral
        record or interpreted-state JSON file is present. Missing siblings
        default to empty.
        """
        if not self.behavioral_path.exists() and not self.interpreted_path.exists():
            return None

        snap = AnimaStoreSnapshot()

        if self.behavioral_path.exists():
            data = self._read_json(self.behavioral_path)
            snap.episodic_events = list(data.get("episodic_events", []))
            snap.action_history = list(data.get("action_history", []))

        if self.interpreted_path.exists():
            data = self._read_json(self.interpreted_path)
            snap.self_model = dict(data.get("self_model", {}))
            snap.semantic_facts = list(data.get("semantic_facts", []))
            snap.relations = dict(data.get("relations", {}))
            snap.mood = dict(data.get("mood", {}))
            snap.drives = dict(data.get("drives", {}))
            snap.conversation_history = list(data.get("conversation_history", []))
            snap.current_session_id = data.get("current_session_id")

        # Transcripts: one file per session.
        if self.transcripts_dir.exists():
            for p in sorted(self.transcripts_dir.glob("*.json")):
                try:
                    payload = self._read_json(p)
                except (OSError, json.JSONDecodeError):
                    # Skip malformed / partial transcripts; the rest of the
                    # store should still load.
                    continue
                sid = payload.get("session_id") or p.stem
                snap.transcripts_by_session[sid] = list(payload.get("messages", []))

        return snap

    # ---------- save

    def save(
        self,
        snapshot: AnimaStoreSnapshot,
        session_id: str | None = None,
    ) -> None:
        """Atomically persist the snapshot to disk.

        Writes:
          - ``behavioral_record.json`` (the FULL current behavioral record;
            merging with any on-disk version is the caller's responsibility —
            ``load()`` before mutating, then ``save()``)
          - ``interpreted.json`` (full interpreted state)
          - if ``session_id`` is set: ``transcripts/<session_id>.json`` with
            the CURRENT in-snapshot conversation history — replacing the prior
            version of that one session's transcript. Other session files are
            untouched, preserving prior runs.

        Each write goes through a temp sibling + ``os.replace`` so partial
        writes are never visible to readers.
        """
        self.dir.mkdir(parents=True, exist_ok=True)

        behavioral = {
            "episodic_events": list(snapshot.episodic_events),
            "action_history": list(snapshot.action_history),
        }
        interpreted = {
            "self_model": dict(snapshot.self_model),
            "semantic_facts": list(snapshot.semantic_facts),
            "relations": dict(snapshot.relations),
            "mood": dict(snapshot.mood),
            "drives": dict(snapshot.drives),
            "conversation_history": list(snapshot.conversation_history),
            "current_session_id": session_id if session_id is not None else snapshot.current_session_id,
        }

        self._write_json_atomic(self.behavioral_path, behavioral)
        self._write_json_atomic(self.interpreted_path, interpreted)

        if session_id is not None:
            self.transcripts_dir.mkdir(parents=True, exist_ok=True)
            transcript_path = self.transcripts_dir / f"{session_id}.json"
            payload = {
                "session_id": session_id,
                "messages": list(snapshot.conversation_history),
            }
            self._write_json_atomic(transcript_path, payload)

    # ---------- helpers

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
        """Write JSON atomically: temp sibling + ``os.replace``.

        Uses ``NamedTemporaryFile(delete=False)`` in the same directory so the
        rename stays on one filesystem (a cross-fs rename is not atomic). The
        temp file is removed if the write or replace fails.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=path.name + ".",
            suffix=".tmp",
            delete=False,
        )
        try:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, path)
        except Exception:
            tmp.close()
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise
