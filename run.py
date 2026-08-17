"""Entry point.

Usage:
    python run.py                         # uses sample/sample.mp4
    python run.py --video path/to.mp4 --transcript path/to.txt
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
    print(f"Extracting audio from {video}")
    subprocess.run(
        ["ffmpeg", "-i", video, "-ac", "1", "-ar", "16000", "-y", wav],
        capture_output=True, check=True,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Plan video cut points from speech.")
    p.add_argument("--video", default="sample/sample.mp4")
    p.add_argument("--transcript", default="sample/transcript_corrected.txt")
    p.add_argument("--timings", default=None,
                   help="Path to word-level timing JSON. If omitted, Whisper "
                        "generates it from the video's audio.")
    p.add_argument("--output", default="output")
    p.add_argument("--threshold-db", type=int, default=-35)
    p.add_argument("--skip-asr", action="store_true",
                   help="reuse existing words.json instead of re-running Whisper")
    args = p.parse_args()

    out = Path(args.output)
    out.mkdir(exist_ok=True)
    wav = str(out / "audio.wav")

    extract_audio(args.video, wav)

    timings_path = args.timings or str(out / "words.json")

    if args.timings:
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