"""Detect and classify disagreements between the three sources.

Resolution principle, applied throughout:

    The transcript decides WHETHER a cut belongs somewhere.
    The audio decides WHERE it can actually land.

Semantics propose, acoustics dispose. A cut may be moved to nearby silence,
but never invented where the audio gives no support, and never kept when its
semantic justification is absent.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from .audio import SilenceWindow, nearest_window, window_containing
from .candidates import Candidate


# Transcript candidates within this distance of a silence window are treated
# as ordinary alignment drift, not conflict. Observed drift: 0.08-0.30s.
DRIFT_TOLERANCE_S = 0.35

# A silence must be at least this long to support a cut on its own.
SUBSTANTIAL_SILENCE_S = 0.60

# Words that rarely end a thought. A long pause adjacent to one of these is
# a hesitation, not a sentence boundary. Derived from observation: every
# unexplained pause in the sample recording is bounded by one of these.
FUNCTION_WORDS = {
    # auxiliaries and copulas
    "is", "was", "are", "were", "be", "been", "being", "am",
    "has", "have", "had", "do", "does", "did", "will", "would",
    "can", "could", "should", "may", "might", "must", "shall",
    # conjunctions
    "and", "or", "but", "so", "because", "although", "though",
    "while", "whereas", "yet", "nor",
    # prepositions
    "of", "to", "in", "for", "on", "with", "at", "by", "from",
    "about", "into", "through", "during", "before", "after",
    "between", "under", "over", "like", "as",
    # articles and determiners
    "the", "a", "an", "this", "that", "these", "those", "some",
    "any", "each", "every", "which", "what",
    # pronouns in subject position
    "i", "you", "he", "she", "it", "we", "they",
}

# Words that rarely END a thought. A pause after one of these is a stall.
TRAILING_FUNCTION_WORDS = FUNCTION_WORDS  # the existing set

# Words that rarely BEGIN a thought. Much narrower — sentences routinely
# start with "this", "the", "I", "they". They do not start with "and" or "for".
LEADING_FUNCTION_WORDS = {
    "and", "or", "but", "nor", "so", "yet", "because", "although",
    "though", "while", "whereas", "of", "to", "for", "with", "at",
    "by", "from", "into", "as", "than",
}

FILLERS = {"uh", "um", "er", "ah", "mm", "hmm", "like", "yeah"}


class ConflictType(Enum):
    AGREEMENT = "agreement"
    ALIGNMENT_DRIFT = "alignment_drift"
    SEMANTICS_WITHOUT_ACOUSTICS = "semantics_without_acoustics"
    ACOUSTICS_WITHOUT_SEMANTICS = "acoustics_without_semantics"
    TIMING_UNRELIABLE = "timing_unreliable"


@dataclass
class Proposal:
    """A candidate cut after conflict analysis, before audio verification."""
    time: float
    conflict: ConflictType
    confidence: float
    trusted_source: str
    rationale: str
    sources: List[str] = field(default_factory=list)
    context: str = ""
    silence: Optional[SilenceWindow] = None
    evidence: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (f"{self.time:7.2f}s  c={self.confidence:.2f}  "
                f"{self.conflict.value:28} {self.rationale}")


def _clean(word: str) -> str:
    return word.strip().strip(".,;:!?\"'").lower()


def words_around(words: List[dict], window: SilenceWindow) -> Tuple[str, str]:
    """The last word ending before a silence and the first starting after it.

    Word timings are unreliable inside long pauses (the aligner stretches
    words across them), so a word overlapping the window is attributed to
    whichever side its midpoint falls nearer.
    """
    before, after = "", ""

    for w in words:
        mid = (w["start"] + w["end"]) / 2
        if w["end"] <= window.start or mid < window.start:
            before = _clean(w["word"])
        elif not after and (w["start"] >= window.end or mid > window.start):
            after = _clean(w["word"])

    return before, after


def classify_transcript_candidate(cand: Candidate,
                                  silences: List[SilenceWindow]) -> Proposal:
    """A punctuation mark asserts a boundary. Does the audio support it?"""
    containing = window_containing(silences, cand.time)
    if containing:
        return Proposal(
            time=cand.time,
            conflict=ConflictType.AGREEMENT,
            confidence=min(0.95, cand.strength + 0.05),
            trusted_source="both",
            rationale=f"{cand.reason}, inside {containing.duration:.2f}s silence",
            sources=["transcript"],
            context=cand.context,
            silence=containing,
            evidence=cand.evidence,
        )

    near = nearest_window(silences, cand.time, DRIFT_TOLERANCE_S)
    if near:
        if cand.time < near.start:
            offset, relation = near.start - cand.time, "begins"
        else:
            offset, relation = cand.time - near.end, "ended"
        return Proposal(
            time=cand.time,
            conflict=ConflictType.ALIGNMENT_DRIFT,
            confidence=cand.strength,
            trusted_source="audio",
            rationale=(f"{cand.reason}; nearest silence {relation} "
                       f"{offset:.2f}s away — routine drift, snap to audio"),
            sources=["transcript"],
            context=cand.context,
            silence=near,
            evidence={**cand.evidence, "drift_s": round(offset, 3),
                      "relation": relation},
        )

    # Punctuation with no acoustic support anywhere nearby.
    wider = nearest_window(silences, cand.time, 0.80)
    return Proposal(
        time=cand.time,
        conflict=ConflictType.SEMANTICS_WITHOUT_ACOUSTICS,
        confidence=cand.strength * 0.4,
        trusted_source="audio",
        rationale=(f"{cand.reason} but no silence within "
                   f"{DRIFT_TOLERANCE_S}s — punctuation may reflect grammar "
                   f"rather than delivery"),
        sources=["transcript"],
        context=cand.context,
        silence=wider,
        evidence=cand.evidence,
    )


def find_unexplained_silences(silences: List[SilenceWindow],
                              transcript_proposals: List[Proposal],
                              words: List[dict]) -> List[Proposal]:
    """Substantial silences that no punctuation accounts for.

    These are the hard cases: strong acoustic evidence, absent semantic
    support. Either the transcript is missing punctuation, or the speaker
    hesitated mid-clause. The adjacent words decide which.
    """
    claimed = {id(p.silence) for p in transcript_proposals if p.silence}
    proposals = []

    for window in silences:
        if id(window) in claimed or window.duration < SUBSTANTIAL_SILENCE_S:
            continue

        before, after = words_around(words, window)
        stalls_before = before in TRAILING_FUNCTION_WORDS or before in FILLERS
        stalls_after = after in LEADING_FUNCTION_WORDS or after in FILLERS

        if stalls_before or stalls_after:
            culprit = before if stalls_before else after
            side = "preceded" if stalls_before else "followed"
            proposals.append(Proposal(
                time=window.midpoint,
                conflict=ConflictType.ACOUSTICS_WITHOUT_SEMANTICS,
                confidence=0.15,
                trusted_source="transcript",
                rationale=(f"{window.duration:.2f}s silence but {side} by "
                           f"\"{culprit}\" — hesitation mid-clause, not a boundary"),
                sources=["audio"],
                context=f"...{before} | {after}...",
                silence=window,
                evidence={"before": before, "after": after,
                          "duration_s": round(window.duration, 2),
                          "verdict": "hesitation"},
            ))
        else:
            # Content words either side: the transcript may simply be missing
            # a mark here. Usable, but never as strong as explicit punctuation.
            confidence = min(0.55, 0.30 + window.duration * 0.08)
            proposals.append(Proposal(
                time=window.midpoint,
                conflict=ConflictType.ACOUSTICS_WITHOUT_SEMANTICS,
                confidence=round(confidence, 2),
                trusted_source="audio",
                rationale=(f"{window.duration:.2f}s silence between content words "
                           f"\"{before}\" and \"{after}\" — transcript may be "
                           f"missing punctuation"),
                sources=["audio"],
                context=f"...{before} | {after}...",
                silence=window,
                evidence={"before": before, "after": after,
                          "duration_s": round(window.duration, 2),
                          "verdict": "possible missing punctuation"},
            ))

    return proposals


def check_timing_claims(timing_candidates: List[Candidate],
                        silences: List[SilenceWindow]) -> List[Proposal]:
    """Timing gaps the audio does not corroborate.

    These are not used as cut points. They are recorded because a timing
    claim contradicted by the waveform is evidence about how far the
    alignment can be trusted.
    """
    unsupported = []

    for cand in timing_candidates:
        if "suspect alignment" in cand.reason:
            continue
        if nearest_window(silences, cand.time, DRIFT_TOLERANCE_S):
            continue

        unsupported.append(Proposal(
            time=cand.time,
            conflict=ConflictType.TIMING_UNRELIABLE,
            confidence=0.0,
            trusted_source="audio",
            rationale=f"{cand.reason}, but waveform shows no silence — discarded",
            sources=["timing"],
            context=cand.context,
            evidence=cand.evidence,
        ))

    return unsupported


def analyse(transcript_candidates: List[Candidate],
            timing_candidates: List[Candidate],
            silences: List[SilenceWindow],
            words: List[dict]) -> List[Proposal]:
    """Full conflict analysis across all three sources."""
    proposals = [classify_transcript_candidate(c, silences)
                 for c in transcript_candidates]

    proposals += find_unexplained_silences(silences, proposals, words)
    proposals += check_timing_claims(timing_candidates, silences)

    return sorted(proposals, key=lambda p: p.time)


if __name__ == "__main__":
    from .audio import find_silences, get_duration
    from .candidates import (align_transcript_to_words, from_timing,
                             from_transcript, load_transcript, load_words)

    wav = "output/audio.wav"
    duration = get_duration(wav)
    silences = find_silences(wav, duration_s=duration)

    words = load_words()
    aligned = align_transcript_to_words(load_transcript(), words)

    proposals = analyse(from_transcript(aligned), from_timing(words),
                        silences, words)

    by_type = {}
    for p in proposals:
        by_type.setdefault(p.conflict, []).append(p)

    for conflict_type in ConflictType:
        group = by_type.get(conflict_type, [])
        if not group:
            continue
        print(f"\n{'=' * 78}\n{conflict_type.value.upper()}  ({len(group)})\n{'=' * 78}")
        for p in group:
            print(f"{p}")
            print(f"          {p.context}")

    print(f"\n{len(proposals)} proposals total.")