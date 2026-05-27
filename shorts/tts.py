#!/usr/bin/env python3
"""Free voiceover via Microsoft Edge TTS (edge-tts package).

Wraps ``edge_tts.Communicate`` with two helpers:

* :func:`synthesize_segments` — render a list of script segments to per-segment
  MP3 files. Returns the path of each file and its duration in seconds so the
  renderer knows when to swap on-screen overlays.

* :func:`synthesize_combined` — render the full script to one MP3 plus an SRT
  subtitle file (one cue per word). Good when you want TikTok-style word-by-word
  captions burnt in via ``ffmpeg -vf subtitles=``.

No API key required — Edge TTS is free. Recommended voices for the
faceless-finance niche:

* ``en-US-AndrewNeural`` (male, confident)
* ``en-US-GuyNeural`` (male, neutral US)
* ``en-US-JennyNeural`` (female, warm clear)
* ``en-US-AriaNeural`` (female, news anchor)

Run from the CLI:

    python3 shorts/tts.py --voice en-US-AndrewNeural --text "Hello world" out.mp3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import edge_tts

DEFAULT_VOICE = "en-US-AndrewNeural"
DEFAULT_RATE = "+0%"   # speed
DEFAULT_PITCH = "+0Hz"


@dataclass
class SegmentAudio:
    """Audio file generated for a single script segment."""

    role: str
    text: str
    on_screen: str
    path: Path
    duration_s: float
    srt_path: Path | None = None


def _ffprobe_duration(path: Path) -> float:
    """Return media duration in seconds via ffprobe."""
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe not found on PATH. Install ffmpeg.")
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    )
    return float(out.strip())


async def _stream_to_file(
    text: str,
    *,
    voice: str,
    rate: str,
    pitch: str,
    out_audio: Path,
    out_srt: Path | None = None,
) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    sub_maker = edge_tts.SubMaker() if out_srt else None
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    with out_audio.open("wb") as f:
        async for chunk in communicate.stream():
            ctype = chunk["type"]
            if ctype == "audio":
                f.write(chunk["data"])
            elif sub_maker is not None and ctype in ("WordBoundary", "SentenceBoundary"):
                # SubMaker commits to whichever boundary type it sees first,
                # so accept whatever Edge returns (default is SentenceBoundary
                # for most Neural voices as of edge-tts 7.x).
                try:
                    sub_maker.feed(chunk)
                except ValueError:
                    # Mixed boundary types — keep the first kind only.
                    pass
    if out_srt and sub_maker is not None:
        out_srt.parent.mkdir(parents=True, exist_ok=True)
        out_srt.write_text(sub_maker.get_srt(), encoding="utf-8")


def synthesize_segments(
    segments: Iterable[tuple[str, str, str]],
    out_dir: Path,
    *,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    pitch: str = DEFAULT_PITCH,
    make_srt: bool = True,
) -> list[SegmentAudio]:
    """Synthesize one MP3 per (role, text, on_screen) tuple.

    Returns SegmentAudio entries in the same order with measured durations.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[SegmentAudio] = []

    async def _runner() -> None:
        for idx, (role, text, on_screen) in enumerate(segments):
            text = text.strip()
            if not text:
                continue
            audio_path = out_dir / f"seg_{idx:02d}_{role}.mp3"
            srt_path = out_dir / f"seg_{idx:02d}_{role}.srt" if make_srt else None
            await _stream_to_file(
                text,
                voice=voice,
                rate=rate,
                pitch=pitch,
                out_audio=audio_path,
                out_srt=srt_path,
            )
            duration = _ffprobe_duration(audio_path)
            results.append(
                SegmentAudio(
                    role=role,
                    text=text,
                    on_screen=on_screen,
                    path=audio_path,
                    duration_s=duration,
                    srt_path=srt_path,
                )
            )

    asyncio.run(_runner())
    return results


def synthesize_combined(
    text: str,
    out_audio: Path,
    out_srt: Path | None = None,
    *,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    pitch: str = DEFAULT_PITCH,
) -> tuple[Path, Path | None, float]:
    """Render full text to one MP3 plus optional SRT.

    Returns (audio_path, srt_path_or_none, duration_seconds).
    """
    asyncio.run(
        _stream_to_file(
            text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            out_audio=out_audio,
            out_srt=out_srt,
        )
    )
    return out_audio, out_srt, _ffprobe_duration(out_audio)


def list_voices(language_prefix: str = "en-") -> list[dict]:
    """Return Edge voices filtered by locale prefix (e.g. ``en-`` for English)."""
    return asyncio.run(_list_voices(language_prefix))


async def _list_voices(language_prefix: str) -> list[dict]:
    voices = await edge_tts.list_voices()
    return [v for v in voices if v.get("ShortName", "").startswith(language_prefix)]


def main() -> int:
    p = argparse.ArgumentParser(description="Edge TTS helper")
    p.add_argument("--voice", default=DEFAULT_VOICE)
    p.add_argument("--rate", default=DEFAULT_RATE)
    p.add_argument("--pitch", default=DEFAULT_PITCH)
    p.add_argument("--text", help="Inline text to synthesize")
    p.add_argument("--text-file", help="Read text from a file")
    p.add_argument("--srt", help="Write SRT to this path", default=None)
    p.add_argument("--list-voices", action="store_true")
    p.add_argument("out", nargs="?", help="Output MP3 path")
    args = p.parse_args()

    if args.list_voices:
        voices = list_voices()
        # Print short summary
        for v in voices:
            print(
                f"{v['ShortName']}  gender={v.get('Gender')}  "
                f"locale={v.get('Locale')}  style={v.get('VoicePersonalities', [])}"
            )
        return 0

    if not args.out:
        p.error("output path is required unless --list-voices")
    text = args.text
    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
    if not text:
        p.error("--text or --text-file required")

    out_audio = Path(args.out)
    out_srt = Path(args.srt) if args.srt else None
    audio_path, srt_path, duration = synthesize_combined(
        text,
        out_audio=out_audio,
        out_srt=out_srt,
        voice=args.voice,
        rate=args.rate,
        pitch=args.pitch,
    )
    json.dump(
        {
            "audio": str(audio_path),
            "srt": str(srt_path) if srt_path else None,
            "duration_s": duration,
        },
        sys.stdout,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
