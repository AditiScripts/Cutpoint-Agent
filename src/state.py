"""Plan state and audit log.

The agent's decisions are not independent. Accepting a cut consumes a
silence window, which constrains later cuts. Rejecting one frees evidence
for a weaker candidate to claim. This module holds that shared state and
records every decision as it is made.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from .audio import SilenceWindow
from .conflicts import ConflictType, Proposal


class CutStatus(Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    SHIFTED = "shifted"
    REJECTED = "rejected"


@dataclass
class Cut:
    time: float
    original_time: float
    status: CutStatus
    confidence: float
    conflict: ConflictType
    trusted_source: str
    rationale: str
    context: str
    history: List[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    @property
    def was_moved(self) -> bool:
        return abs(self.time - self.original_time) > 0.001

    def to_dict(self) -> dict:
        return {
            "time": round(self.time, 3),
            "original_time": round(self.original_time, 3),
            "moved_by": round(self.time - self.original_time, 3) if self.was_moved else 0,
            "status": self.status.value,
            "confidence": round(self.confidence, 2),
            "conflict_type": self.conflict.value,
            "trusted_source": self.trusted_source,
            "rationale": self.rationale,
            "context": self.context,
            "decision_history": self.history,
            "evidence": self.evidence,
        }


@dataclass
class LogEntry:
    step: int
    action: str
    time: float
    detail: str

    def __repr__(self) -> str:
        return f"[{self.step:03}] {self.action:22} @{self.time:7.2f}s  {self.detail}"


class CutPlan:
    """Mutable plan the agent revises as evidence accumulates."""

    def __init__(self, audio_path: str, duration: float):
        self.audio_path = audio_path
        self.duration = duration
        self.cuts: List[Cut] = []
        self.log: List[LogEntry] = []
        self.consumed: List[SilenceWindow] = []
        self._step = 0
        self._reanalysis_calls = 0

    def record(self, action: str, time: float, detail: str) -> None:
        self._step += 1
        entry = LogEntry(self._step, action, time, detail)
        self.log.append(entry)
        print(f"  {entry}")

    def note_reanalysis(self) -> None:
        self._reanalysis_calls += 1

    def add(self, proposal: Proposal) -> Cut:
        cut = Cut(
            time=proposal.time,
            original_time=proposal.time,
            status=CutStatus.PROPOSED,
            confidence=proposal.confidence,
            conflict=proposal.conflict,
            trusted_source=proposal.trusted_source,
            rationale=proposal.rationale,
            context=proposal.context,
            evidence=dict(proposal.evidence),
        )
        self.cuts.append(cut)
        self.record("PROPOSED", cut.time, proposal.rationale[:80])
        return cut

    def accept(self, cut: Cut, window: SilenceWindow, note: str) -> None:
        cut.status = CutStatus.ACCEPTED
        cut.history.append(note)
        self.consumed.append(window)
        self.record("ACCEPTED", cut.time, note)

    def shift(self, cut: Cut, new_time: float, window: SilenceWindow, note: str) -> None:
        moved = new_time - cut.time
        cut.history.append(f"moved {moved:+.2f}s: {note}")
        cut.time = new_time
        cut.status = CutStatus.SHIFTED
        self.consumed.append(window)
        self.record("SHIFTED", new_time, f"{moved:+.2f}s — {note}")

    def reject(self, cut: Cut, note: str) -> None:
        cut.status = CutStatus.REJECTED
        cut.history.append(f"rejected: {note}")
        self.record("REJECTED", cut.time, note)

    def is_consumed(self, window: SilenceWindow) -> bool:
        return any(abs(w.start - window.start) < 0.01 for w in self.consumed)

    def too_close_to_existing(self, t: float, min_gap: float) -> Optional[Cut]:
        for cut in self.final_cuts():
            if abs(cut.time - t) < min_gap:
                return cut
        return None

    def final_cuts(self) -> List[Cut]:
        return sorted(
            [c for c in self.cuts if c.status in (CutStatus.ACCEPTED, CutStatus.SHIFTED)],
            key=lambda c: c.time,
        )

    def rejected(self) -> List[Cut]:
        return [c for c in self.cuts if c.status == CutStatus.REJECTED]

    def summary(self) -> dict:
        final = self.final_cuts()
        return {
            "audio": self.audio_path,
            "duration_s": round(self.duration, 2),
            "generated": datetime.now().isoformat(timespec="seconds"),
            "proposed": len(self.cuts),
            "accepted": sum(1 for c in self.cuts if c.status == CutStatus.ACCEPTED),
            "shifted": sum(1 for c in self.cuts if c.status == CutStatus.SHIFTED),
            "rejected": len(self.rejected()),
            "final_cut_count": len(final),
            "targeted_reanalyses": self._reanalysis_calls,
        }

    def to_json(self) -> str:
        return json.dumps({
            "summary": self.summary(),
            "cuts": [c.to_dict() for c in self.final_cuts()],
            "rejected": [c.to_dict() for c in self.rejected()],
            "audit_log": [asdict(e) for e in self.log],
        }, indent=2)