"""Propose candidate cut points from the transcript and from word timings.

The two sources are generated independently and never merged here. Keeping
them apart is what makes disagreement visible to the conflict stage.

The transcript is a claim about meaning: punctuation asserts that a thought
ended. The timings are a claim about when words were spoken. Neither is a
measurement of the audio.
"""

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Literal


# Minimum inter-word gap to propose a cut from timing data.
MIN_TIMING_GAP_S = 0.40

# A single word longer than this indicates the aligner absorbed a pause
# into the word rather than reporting a gap. Observed: "ship" spanning
# 31.28–36.92 across a 5.5s silence.
IMPLAUSIBLE_WORD_S = 1.50

# Semantic weight by punctuation mark. A full stop is a strong claim that
# a thought ended; a comma is a weak one.
PUNCT_STRENGTH = {
    ".": 0.90, "?": 0.90, "!": 0.90,
    ";": 0.60, ":": 0.55,
    ",": 0.35,
}


@dataclass
class Candidate:
    time: float
    source: Literal["transcript", "timing"]
    strength: float
    reason: str
    context: str = ""
    evidence: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"[{self.source:10}] {self.time:7.2f}s  s={self.strength:.2f}  {self.reason}"


def _normalise(token: str) -> str:
    return re.sub(r"[^\w']", "", token).lower()


def load_words(path: str = "output/words.json") -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_transcript(path: str = "sample/transcript_corrected.txt") -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def align_transcript_to_words(transcript: str, words: List[dict]) -> List[dict]:
    """Map each transcript token onto a timed word.

    The corrected transcript is an independent artifact — a human may have
    fixed ASR errors, so the token sequences differ. Rather than assume
    they match, align them with a sequence matcher and only trust tokens
    that align. Unmatched tokens (human corrections) carry no timing and
    are skipped, which is the honest outcome.
    """
    t_tokens = transcript.split()
    t_norm = [_normalise(t) for t in t_tokens]
    w_norm = [_normalise(w["word"]) for w in words]

    aligned = []
    matcher = SequenceMatcher(None, t_norm, w_norm, autojunk=False)

    for t_i, w_i, size in matcher.get_matching_blocks():
        for k in range(size):
            aligned.append({
                "token": t_tokens[t_i + k],
                "start": words[w_i + k]["start"],
                "end": words[w_i + k]["end"],
                "probability": words[w_i + k].get("probability", 1.0),
                "index": t_i + k,
            })

    matched = len(aligned)
    print(f"  Aligned {matched}/{len(t_tokens)} transcript tokens "
          f"({100 * matched / len(t_tokens):.0f}%)")
    return aligned


def from_transcript(aligned: List[dict]) -> List[Candidate]:
    """Propose a cut after every token carrying terminal punctuation."""
    candidates = []

    for i, tok in enumerate(aligned):
        trailing = tok["token"][-1] if tok["token"] else ""
        if trailing not in PUNCT_STRENGTH:
            continue

        strength = PUNCT_STRENGTH[trailing]

        # Low ASR confidence on the word weakens the punctuation claim.
        if tok["probability"] < 0.5:
            strength *= 0.8

        following = aligned[i + 1]["token"] if i + 1 < len(aligned) else "<end>"
        candidates.append(Candidate(
            time=tok["end"],
            source="transcript",
            strength=round(strength, 2),
            reason=f"'{trailing}' after \"{tok['token']}\"",
            context=f"...{tok['token']} | {following}...",
            evidence={"mark": trailing, "word_probability": tok["probability"]},
        ))

    return candidates


def from_timing(words: List[dict]) -> List[Candidate]:
    """Propose a cut wherever the timings show a gap between words.

    Also flags words of implausible duration. These are alignment failures
    where a pause was absorbed into a word, so no gap is reported despite a
    real silence being present — the timing source failing silently.
    """
    candidates = []

    for i in range(len(words) - 1):
        cur, nxt = words[i], words[i + 1]
        gap = nxt["start"] - cur["end"]

        if gap >= MIN_TIMING_GAP_S:
            strength = min(0.75, 0.30 + gap * 0.30)
            candidates.append(Candidate(
                time=round(cur["end"] + gap / 2, 3),
                source="timing",
                strength=round(strength, 2),
                reason=f"{gap:.2f}s gap between words",
                context=f"...{cur['word']} | {nxt['word']}...",
                evidence={"gap_s": round(gap, 3)},
            ))

        duration = cur["end"] - cur["start"]
        if duration > IMPLAUSIBLE_WORD_S:
            candidates.append(Candidate(
                time=round(cur["start"] + 0.3, 3),
                source="timing",
                strength=0.20,
                reason=f"suspect alignment: \"{cur['word']}\" spans {duration:.2f}s",
                context=f"...{cur['word']}...",
                evidence={"word_duration_s": round(duration, 3),
                          "span": [cur["start"], cur["end"]]},
            ))

    return candidates


if __name__ == "__main__":
    words = load_words()
    transcript = load_transcript()

    print("Aligning corrected transcript to word timings...")
    aligned = align_transcript_to_words(transcript, words)

    t_cands = from_transcript(aligned)
    g_cands = from_timing(words)

    print(f"\nTranscript proposed {len(t_cands)} candidates:")
    for c in t_cands:
        print(f"  {c}")

    print(f"\nTiming proposed {len(g_cands)} candidates:")
    for c in g_cands:
        print(f"  {c}")

    print(f"\nTotal: {len(t_cands) + len(g_cands)} candidates before conflict analysis.")