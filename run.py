"""Entry point.

Orchestration only. This file contains no decision logic — it wires the
modules together in order and prints progress. Every judgement about where a
cut belongs lives in conflicts.py and verify.py, so this file can be read
top to bottom as a description of the pipeline.

Usage:
    python run.py                                  # defaults to the sample
    python run.py --video x.mp4 --transcript y.txt --timings z.json
"""

import argparse
import subprocess
from pathlib import Path

from src.audio import find_silences, get_duration
from src.candidates import (align_transcript_to_words, from_timing,
                            from_transcript, load_transcript, load_words)
from src.conflicts import analyse
from src.report import write_json, write_markdown
from src.transcribe import transcribe
from src.verify import run as verify_all


def extract_audio(video: str, wav: str) -> None:
    """Pull a mono 16kHz WAV out of the video for analysis.

    -ac 1 collapses to mono: stereo would require deciding how to combine
    channels before measuring energy, and a single speaker gains nothing
    from two.

    -ar 16000 matches what Whisper expects internally, so the same file
    serves both silence detection and transcription. No second extraction.

    check=True raises on a non-zero exit rather than continuing with a
    missing or truncated WAV, which would otherwise surface much later as an
    empty silence list. capture_output suppresses ffmpeg's banner.
    """
    
    print(f"Extracting audio from {video}")
    subprocess.run(
        ["ffmpeg", "-i", video, "-ac", "1", "-ar", "16000", "-y", wav],
        capture_output=True, check=True,
    )

# The three inputs the brief specifies, each supplied explicitly:
    #   --video       the source recording
    #   --transcript  punctuated text (a human-corrected artifact)
    #   --timings     word-level timings from speech recognition
    #
    # --transcript and --timings are deliberately separate arguments rather
    # than both being derived from one Whisper run. They are independent
    # artifacts: a human may have corrected the text, so its token sequence
    # differs from the ASR output. Keeping them separate is what makes their
    # disagreement visible rather than assumed away.
def main() -> None:
    p = argparse.ArgumentParser(description="Plan video cut points from speech.")
    p.add_argument("--video", default="sample/sample.mp4")
    p.add_argument("--transcript", default="sample/transcript_corrected.txt")
    p.add_argument("--timings", default=None,
                   help="Path to word-level timing JSON. If omitted, Whisper "
                        "generates it from the video's audio.")
    p.add_argument("--output", default="output")
    
    # Overriding the threshold is exposed because it is the single most
    # consequential tuning parameter, and the right value depends on the
    # recording's noise floor. -35dB is correct for this sample, not in
    # general. See README for the sweep that chose it.
    p.add_argument("--threshold-db", type=int, default=-35)
    
    # Whisper takes several minutes on CPU and its output is deterministic
    # for a given file, so re-running it while iterating on the decision
    # logic is wasted time. Development convenience only — the default path
    # runs the full pipeline from scratch.
    p.add_argument("--skip-asr", action="store_true",
                   help="reuse existing words.json instead of re-running Whisper")
    args = p.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    wav = str(out / "audio.wav")

    # Extraction is unconditional: the WAV is derived from the video, and
    # regenerating it is cheap compared to the risk of analysing a stale
    # file left over from a previous run ag
    extract_audio(args.video, wav)

    # Three ways to obtain timing data, in priority order:
    #   1. supplied explicitly    — trust it, no ASR needed
    #   2. --skip-asr and cached  — reuse what is on disk
    #   3. otherwise              — run Whisper
    timings_path = args.timings or str(out / "words.json")

    if args.timings:
        if not Path(args.timings).exists():
            raise FileNotFoundError(f"Timing file not found: {args.timings}")
        print(f"Using supplied timing data from {args.timings}")
    elif not args.skip_asr or not Path(timings_path).exists():
        transcribe(wav, args.output)

    duration = get_duration(wav)
    print(f"\nAnalysing audio ({duration:.1f}s) at {args.threshold_db}dB")
    silences = find_silences(wav, threshold_db=args.threshold_db, duration_s=duration)
    print(f"Found {len(silences)} usable silence windows")

    words = load_words(timings_path)
    aligned = align_transcript_to_words(load_transcript(args.transcript), words)

    proposals = analyse(from_transcript(aligned), from_timing(words), silences, words)
    print(f"Generated {len(proposals)} proposals across all sources")

    plan = verify_all(proposals, silences, wav, duration)

    write_json(plan, str(out / "cuts.json"))
    write_markdown(plan, str(out / "decisions.md"))

    s = plan.summary()
    print(f"\n{s['final_cut_count']} cut points · {s['rejected']} rejected · "
          f"{s['targeted_reanalyses']} re-analyses")


if __name__ == "__main__":
    main()