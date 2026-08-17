"""Audio analysis tool.

This is the agent's only source of direct evidence about the recording.
The transcript and word timings are claims; this module makes measurements.

Designed to be called on demand — including repeatedly on a narrow window
with a different threshold when the agent is uncertain about a decision.
"""

import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional


# Two silences separated by less than this are treated as one.
# Justified by observed sub-10ms artefacts (e.g. a 1.4ms "speech" gap at
# 3.835s) caused by transients briefly crossing the threshold.
MERGE_GAP_S = 0.05

# Silences shorter than this are not usable as cut points.
MIN_SILENCE_S = 0.25

# Cuts are never placed within this distance of the start or end of the file.
EDGE_MARGIN_S = 2.0

# Default threshold, chosen by sweep — see README.
DEFAULT_THRESHOLD_DB = -35


@dataclass
class SilenceWindow:
    start: float
    end: float
    threshold_db: int

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def midpoint(self) -> float:
        return (self.start + self.end) / 2

    def contains(self, t: float) -> bool:
        return self.start <= t <= self.end

    def __repr__(self) -> str:
        return f"Silence({self.start:.2f}-{self.end:.2f}, {self.duration:.2f}s)"


def _run_silencedetect(wav_path: str, threshold_db: int, min_duration: float,
                       start: Optional[float], end: Optional[float]) -> str:
    """Call ffmpeg and return its stderr, where silencedetect writes."""
    cmd = ["ffmpeg"]
    if start is not None:
        cmd += ["-ss", str(start)]
    if end is not None and start is not None:
        cmd += ["-t", str(end - start)]
    cmd += [
        "-i", wav_path,
        "-af", f"silencedetect=noise={threshold_db}dB:d={min_duration}",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stderr


def _parse(stderr: str, threshold_db: int, offset: float) -> List[SilenceWindow]:
    """Turn ffmpeg's stderr into SilenceWindow objects.

    silencedetect emits start and end on separate lines, so they are paired
    as they appear. An unclosed final start means silence ran to end of file.
    """
    windows = []
    pending_start = None

    for line in stderr.splitlines():
        m_start = re.search(r"silence_start:\s*(-?[\d.]+)", line)
        m_end = re.search(r"silence_end:\s*([\d.]+)", line)
        if m_start:
            pending_start = max(0.0, float(m_start.group(1)))
        elif m_end and pending_start is not None:
            windows.append(SilenceWindow(
                start=pending_start + offset,
                end=float(m_end.group(1)) + offset,
                threshold_db=threshold_db,
            ))
            pending_start = None

    return windows


def _merge_adjacent(windows: List[SilenceWindow]) -> List[SilenceWindow]:
    """Join windows separated by less than MERGE_GAP_S.

    A 1.4ms gap is not speech. Without this, a single pause can appear as
    two windows and the agent may snap a cut to the wrong one.
    """
    if not windows:
        return []

    merged = [windows[0]]
    for w in windows[1:]:
        last = merged[-1]
        if w.start - last.end < MERGE_GAP_S:
            merged[-1] = SilenceWindow(last.start, w.end, last.threshold_db)
        else:
            merged.append(w)
    return merged


def find_silences(wav_path: str,
                  threshold_db: int = DEFAULT_THRESHOLD_DB,
                  min_duration: float = MIN_SILENCE_S,
                  start: Optional[float] = None,
                  end: Optional[float] = None,
                  duration_s: Optional[float] = None) -> List[SilenceWindow]:
    """Measure silence directly from the waveform.

    start/end restrict analysis to a window, which is how the agent
    re-examines a specific moment it is unsure about.
    """
    offset = start or 0.0
    stderr = _run_silencedetect(wav_path, threshold_db, min_duration, start, end)
    windows = _merge_adjacent(_parse(stderr, threshold_db, offset))

     # Drop windows that touch the file edges — a cut there removes nothing.
    if duration_s:
        windows = [w for w in windows
                   if w.start > EDGE_MARGIN_S and w.end < duration_s - EDGE_MARGIN_S]

    return [w for w in windows if w.duration >= min_duration]


def get_duration(wav_path: str) -> float:
    """Length of the audio file in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def window_containing(windows: List[SilenceWindow], t: float) -> Optional[SilenceWindow]:
    """The silence window containing time t, if any."""
    for w in windows:
        if w.contains(t):
            return w
    return None


def nearest_window(windows: List[SilenceWindow], t: float,
                   max_distance: float) -> Optional[SilenceWindow]:
    """Closest silence window within max_distance of t, measured to its edge."""
    best, best_dist = None, max_distance
    for w in windows:
        dist = 0.0 if w.contains(t) else min(abs(w.start - t), abs(w.end - t))
        if dist < best_dist:
            best, best_dist = w, dist
    return best


if __name__ == "__main__":
    wav = "output/audio.wav"
    duration = get_duration(wav)
    print(f"Duration: {duration:.2f}s\n")

    silences = find_silences(wav, duration_s=duration)
    print(f"Found {len(silences)} usable silence windows at {DEFAULT_THRESHOLD_DB}dB:")
    for w in silences:
        print(f"  {w}")

    total = sum(w.duration for w in silences)
    print(f"\nTotal silence: {total:.1f}s ({100 * total / duration:.0f}% of recording)")

    # Demonstrate targeted re-analysis: the 5.5s hesitation region.
    print("\nRe-analysing 29–38s at a stricter threshold:")
    for w in find_silences(wav, threshold_db=-40, start=29.0, end=38.0):
        print(f"  {w}")