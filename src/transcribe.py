"""Run speech recognition to produce a transcript and word-level timings.

These are two separate artifacts on purpose. The transcript carries
punctuation, which is a claim about where sentences end. The word timings
carry start/end times, which are a claim about when words were spoken.
Whisper produces them by different mechanisms, so they can disagree.
"""

import json
from pathlib import Path
from faster_whisper import WhisperModel


def transcribe(audio_path: str, output_dir: str = "output", model_size: str = "base"):
    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    print(f"Loading Whisper model '{model_size}'...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"Transcribing {audio_path} (this takes a few minutes)...")
    segments, info = model.transcribe(audio_path, word_timestamps=True)

    words = []
    text_parts = []

    for segment in segments:
        text_parts.append(segment.text.strip())
        for w in segment.words:
            words.append({
                "word": w.word.strip(),
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "probability": round(w.probability, 3),
            })
        print(f"  [{segment.start:6.2f}s] {segment.text.strip()}")

    transcript = " ".join(text_parts)

    (out / "words.json").write_text(json.dumps(words, indent=2), encoding="utf-8")
    (out / "transcript.txt").write_text(transcript, encoding="utf-8")

    print(f"\nWrote {len(words)} words to {out / 'words.json'}")
    print(f"Wrote transcript to {out / 'transcript.txt'}")
    print(f"Detected language: {info.language} (confidence {info.language_probability:.2f})")

    return words, transcript


if __name__ == "__main__":
    transcribe("output/audio.wav")