"""Verification loop.

Every proposal is checked against the waveform before it is kept. A cut may
be accepted, moved to nearby silence, or rejected outright. Decisions are
made in confidence order so that stronger evidence claims silence windows
first, and each decision constrains the ones that follow.

When the audio does not clearly support or refute a proposal, the agent
re-analyses that specific window at a stricter threshold rather than
guessing — a second look at the evidence, not a second guess.
"""

from typing import List, Optional

from .audio import (SilenceWindow, find_silences, nearest_window,
                    window_containing)
from .conflicts import ConflictType, Proposal
from .state import Cut, CutPlan

# A cut may be moved this far to reach real silence. Beyond it, the
# proposal is about a different moment than the evidence supports.
MAX_SHIFT_S = 0.75

# Two cuts closer than this produce a clip too short to be useful.
MIN_CLIP_S = 1.50

# Below this, evidence is too weak to cut on regardless of audio support.
MIN_CONFIDENCE = 0.30

# Windows shorter than this are re-examined before being trusted.
UNCERTAIN_WINDOW_S = 0.50


def reanalyse(plan: CutPlan, window: SilenceWindow,
              threshold_db: int = -40) -> Optional[SilenceWindow]:
    """Re-measure a specific window at a stricter threshold.

    Called when a window is short enough that its edges may be an artefact
    of the default threshold. If the silence survives a stricter test, it
    is real; if it collapses, it was borderline energy, not a pause.
    """
    plan.note_reanalysis()
    windows = find_silences(
        plan.audio_path,
        threshold_db=threshold_db,
        min_duration=0.10,
        start=max(0.0, window.start - 0.5),
        end=window.end + 0.5,
    )
    if not windows:
        return None
    return max(windows, key=lambda w: w.duration)


def verify_one(plan: CutPlan, cut: Cut, silences: List[SilenceWindow]) -> None:
    """Test a single proposal against the audio and decide its fate."""

    # 1. Evidence too weak to act on, whatever the audio says.
    if cut.confidence < MIN_CONFIDENCE:
        plan.reject(cut, f"confidence {cut.confidence:.2f} below threshold "
                         f"{MIN_CONFIDENCE} — {cut.conflict.value}")
        return

    # 2. Does the audio contain silence at the proposed time?
    window = window_containing(silences, cut.time)

    if window is None:
        window = nearest_window(silences, cut.time, MAX_SHIFT_S)
        if window is None:
            plan.reject(cut, f"no silence within {MAX_SHIFT_S}s — transcript "
                             f"asserts a boundary the audio does not support")
            return

    # 3. Already claimed by a stronger cut?
    if plan.is_consumed(window):
        plan.reject(cut, f"silence at {window.start:.2f}s already used by a "
                         f"higher-confidence cut")
        return

    # 4. Short window: look again before trusting it.
    if window.duration < UNCERTAIN_WINDOW_S:
        confirmed = reanalyse(plan, window)
        if confirmed is None:
            plan.reject(cut, f"{window.duration:.2f}s window did not survive "
                             f"re-analysis at -40dB — not true silence")
            return
        plan.record("RE-ANALYSED", window.midpoint,
                    f"{window.duration:.2f}s @-35dB → "
                    f"{confirmed.duration:.2f}s @-40dB, confirmed")
        window = confirmed

    # 5. Would this cut leave an unusably short clip?
    neighbour = plan.too_close_to_existing(window.midpoint, MIN_CLIP_S)
    if neighbour is not None:
        plan.reject(cut, f"would leave a {abs(window.midpoint - neighbour.time):.2f}s "
                         f"clip against the cut at {neighbour.time:.2f}s")
        return

    # 6. Accept, landing just after speech stops rather than mid-pause.
    #    Midpoint would place the cut deep inside dead air: an 8.76s full stop
    #    would move to 11.19s, leaving 2.4s of silence at the end of the clip.
    #    A small trailing pad preserves natural breathing room without it.
    TRAILING_PAD_S = 0.15
    target = round(min(window.start + TRAILING_PAD_S, window.midpoint), 3)

    # Distinguish padding from correction. A cut already inside real silence
    # is confirmed by the audio; the pad is cosmetic. A cut outside it had to
    # be corrected, which is a substantive change of plan.
    was_inside = window.contains(cut.time)

    if was_inside:
        plan.accept(cut, window, f"confirmed inside {window.duration:.2f}s silence; "
                                 f"padded {target - cut.time:+.2f}s")
        cut.time = target
    else:
        plan.shift(cut, target, window,
                   f"corrected {target - cut.time:+.2f}s into "
                   f"{window.duration:.2f}s silence ({window.start:.2f}–{window.end:.2f})")


def run(proposals: List[Proposal], silences: List[SilenceWindow],
        audio_path: str, duration: float) -> CutPlan:
    """Verify all proposals, strongest evidence first."""
    plan = CutPlan(audio_path, duration)

    # Discard timing claims the waveform already contradicted.
    actionable = [p for p in proposals if p.conflict != ConflictType.TIMING_UNRELIABLE]

    print(f"\nVerifying {len(actionable)} proposals against the waveform")
    print("=" * 78)

    ordered = sorted(actionable, key=lambda p: -p.confidence)
    for proposal in ordered:
        cut = plan.add(proposal)
        verify_one(plan, cut, silences)

    return plan


if __name__ == "__main__":
    from .audio import find_silences, get_duration
    from .candidates import (align_transcript_to_words, from_timing,
                             from_transcript, load_transcript, load_words)
    from .conflicts import analyse

    wav = "output/audio.wav"
    duration = get_duration(wav)
    silences = find_silences(wav, duration_s=duration)
    words = load_words()
    aligned = align_transcript_to_words(load_transcript(), words)

    proposals = analyse(from_transcript(aligned), from_timing(words), silences, words)
    plan = run(proposals, silences, wav, duration)

    s = plan.summary()
    print("\n" + "=" * 78)
    print(f"Proposed {s['proposed']} · accepted {s['accepted']} · "
          f"shifted {s['shifted']} · rejected {s['rejected']}")
    print(f"Targeted re-analyses: {s['targeted_reanalyses']}")
    print(f"\nFinal cut points ({s['final_cut_count']}):")
    for c in plan.final_cuts():
        moved = f" (moved {c.time - c.original_time:+.2f}s)" if c.was_moved else ""
        print(f"  {c.time:7.2f}s  c={c.confidence:.2f}{moved}")