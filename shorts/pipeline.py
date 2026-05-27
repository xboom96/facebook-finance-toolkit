#!/usr/bin/env python3
"""End-to-end pipeline: topic -> script -> voiceover -> vertical 9:16 MP4.

Reads a topic (from CLI, the latest scraper CSV, or stdin) and produces a
ready-to-upload faceless Reel/Short under ``shorts/output/``.

Examples
--------

# 1. Single topic via CLI:
python3 shorts/pipeline.py --topic "5 subscriptions to cancel today"

# 2. Pull today's top trending hook from the scraper's CSV:
python3 shorts/pipeline.py --from-scraper --limit 1

# 3. Batch — generate 5 Reels from today's top trending hooks:
python3 shorts/pipeline.py --from-scraper --limit 5

# 4. Override voice or script mode:
python3 shorts/pipeline.py --topic "..." --voice en-US-GuyNeural --mode offline

Outputs (per topic) under ``shorts/output/YYYY-MM-DD/<slug>/``:

    script.json     — the structured script
    script.md       — human-readable script
    seg_*.mp3       — per-segment voiceover audio
    seg_*.srt       — per-segment word-by-word captions
    combined.srt    — full word-by-word SRT (used for burned captions)
    short.mp4       — final 1080x1920 H.264 video, ready to upload
    metadata.json   — title, hashtags, b-roll suggestions

Dependencies: ``ffmpeg``, ``pip install edge-tts pillow``.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

# Allow running both as a module (python -m shorts.pipeline) and as a script.
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from script_gen import Script, build_script  # noqa: E402
from tts import (  # noqa: E402
    DEFAULT_PITCH,
    DEFAULT_RATE,
    DEFAULT_VOICE,
    SegmentAudio,
    synthesize_segments,
)
from render import RenderSegment, render_short  # noqa: E402


OUTPUT_ROOT = THIS_DIR / "output"
SCRAPER_OUTPUT = THIS_DIR.parent / "scraper" / "output"


def _slug(text: str, max_len: int = 60) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text[:max_len] or "short"


def _latest_scraper_csv() -> Path | None:
    if not SCRAPER_OUTPUT.exists():
        return None
    csvs = sorted(SCRAPER_OUTPUT.glob("trending-*.csv"))
    return csvs[-1] if csvs else None


def _topics_from_csv(csv_path: Path, limit: int) -> list[str]:
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            hook = (r.get("hook_idea") or r.get("title") or "").strip()
            score = int(r.get("score") or 0)
            if hook:
                rows.append((score, hook))
    # Sort by engagement score descending; fall back to insertion order.
    rows.sort(key=lambda x: x[0], reverse=True)
    out: list[str] = []
    seen: set[str] = set()
    for _score, hook in rows:
        key = hook.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(hook)
        if len(out) >= limit:
            break
    return out


def _merge_srt(per_segment: list[SegmentAudio], out_path: Path) -> Path | None:
    """Concatenate per-segment SRTs into a single SRT with shifted timestamps.

    Each segment's SRT starts at 00:00, so we shift cues by the cumulative
    duration of earlier segments. The result is suitable for ``-vf subtitles=``
    against the combined audio track.
    """
    cues_out: list[str] = []
    cue_idx = 1
    offset_s = 0.0
    timestamp_re = re.compile(
        r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
    )

    def shift(ts: tuple[str, ...], by: float) -> str:
        h, m, s, ms = int(ts[0]), int(ts[1]), int(ts[2]), int(ts[3])
        total = h * 3600 + m * 60 + s + ms / 1000.0 + by
        total = max(total, 0.0)
        hh = int(total // 3600)
        mm = int((total % 3600) // 60)
        ss = int(total % 60)
        mss = int(round((total - int(total)) * 1000))
        if mss == 1000:
            ss += 1
            mss = 0
        return f"{hh:02d}:{mm:02d}:{ss:02d},{mss:03d}"

    for seg in per_segment:
        srt_path = seg.srt_path
        if not srt_path or not Path(srt_path).exists():
            offset_s += seg.duration_s
            continue
        body = Path(srt_path).read_text(encoding="utf-8").strip()
        # Split into individual cues by blank lines.
        for block in re.split(r"\n\s*\n", body):
            block = block.strip()
            if not block:
                continue
            lines = block.splitlines()
            if len(lines) < 2:
                continue
            # Drop the cue index line if present.
            ts_line_idx = 0 if "-->" in lines[0] else 1
            if ts_line_idx >= len(lines):
                continue
            m = timestamp_re.search(lines[ts_line_idx])
            if not m:
                continue
            new_start = shift(m.group(1, 2, 3, 4), offset_s)
            new_end = shift(m.group(5, 6, 7, 8), offset_s)
            text_lines = lines[ts_line_idx + 1 :]
            cues_out.append(
                f"{cue_idx}\n{new_start} --> {new_end}\n" + "\n".join(text_lines)
            )
            cue_idx += 1
        offset_s += seg.duration_s

    if not cues_out:
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(cues_out) + "\n", encoding="utf-8")
    return out_path


def render_one(
    topic: str,
    *,
    out_root: Path = OUTPUT_ROOT,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    pitch: str = DEFAULT_PITCH,
    mode: str = "offline",
    title: str = "MONEY 60",
    burn_captions: bool = True,
    seed: int | None = None,
) -> Path:
    today = dt.date.today().isoformat()
    work_dir = out_root / today / _slug(topic)
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {topic} ===")
    print(f"  out: {work_dir}")

    # 1. Script
    script: Script = build_script(topic, mode=mode, seed=seed)
    (work_dir / "script.json").write_text(
        json.dumps(script.to_dict(), indent=2), encoding="utf-8"
    )
    md_lines = [f"# {script.topic}", ""]
    for seg in script.segments:
        md_lines.append(f"## [{seg.role}]")
        if seg.on_screen:
            md_lines.append(f"**On-screen:** {seg.on_screen}")
        md_lines.append(seg.voiceover)
        md_lines.append("")
    md_lines.append(f"**Hashtags:** {' '.join(script.hashtags)}")
    md_lines.append(f"**B-roll terms:** {', '.join(script.broll_terms)}")
    (work_dir / "script.md").write_text("\n".join(md_lines), encoding="utf-8")

    # 2. Voiceover (one MP3 per segment + per-segment SRT)
    print("  > synthesizing voiceover via edge-tts ...")
    tts_segments = [
        (s.role, s.voiceover, s.on_screen)
        for s in script.segments
        if s.voiceover.strip()
    ]
    audio_segs: list[SegmentAudio] = synthesize_segments(
        tts_segments,
        out_dir=work_dir,
        voice=voice,
        rate=rate,
        pitch=pitch,
        make_srt=burn_captions,
    )
    durations = {s.role: s.duration_s for s in audio_segs}
    total_s = sum(s.duration_s for s in audio_segs)
    print(f"  > total voiceover: {total_s:.1f}s across {len(audio_segs)} segments")

    # 3. Combined SRT (optional)
    combined_srt: Path | None = None
    if burn_captions:
        combined_srt = _merge_srt(audio_segs, work_dir / "combined.srt")

    # 4. Render
    render_segs = [
        RenderSegment(
            role=s.role,
            audio_path=s.path,
            duration_s=s.duration_s,
            on_screen=s.on_screen,
        )
        for s in audio_segs
    ]
    out_path = work_dir / "short.mp4"
    render_short(
        render_segs,
        out_path=out_path,
        captions_srt=combined_srt,
        title=title,
        work_dir=work_dir / "_work",
    )

    # 5. Upload metadata
    metadata = {
        "topic": script.topic,
        "title": script.hook[:100],
        "description": (
            script.segments[0].voiceover.strip() + "\n\n"
            + "Not financial advice. Educational only.\n\n"
            + " ".join(script.hashtags)
        )[:2200],
        "hashtags": script.hashtags,
        "broll_terms": script.broll_terms,
        "duration_s": round(total_s, 2),
        "voice": voice,
        "segments": [asdict(s) for s in audio_segs if not s.srt_path or True],
        "durations": durations,
        "video_path": str(out_path),
    }
    # Pathlib objects in dataclass dump
    for seg in metadata["segments"]:
        seg["path"] = str(seg.get("path"))
        if seg.get("srt_path"):
            seg["srt_path"] = str(seg["srt_path"])
    (work_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str), encoding="utf-8"
    )

    print(f"  ✓ wrote {out_path} ({total_s:.1f}s)")
    return out_path


def main() -> int:
    p = argparse.ArgumentParser(description="Faceless Short pipeline")
    p.add_argument("--topic", help="Single topic / hook idea", default=None)
    p.add_argument(
        "--from-scraper",
        action="store_true",
        help="Pull today's top hooks from scraper/output/trending-*.csv",
    )
    p.add_argument("--limit", type=int, default=1, help="How many shorts to generate")
    p.add_argument("--voice", default=DEFAULT_VOICE)
    p.add_argument("--rate", default=DEFAULT_RATE)
    p.add_argument("--pitch", default=DEFAULT_PITCH)
    p.add_argument("--mode", choices=["offline", "openai"], default="offline")
    p.add_argument(
        "--title",
        default="MONEY 60",
        help="Brand title rendered at the top of every short",
    )
    p.add_argument(
        "--no-captions",
        action="store_true",
        help="Skip burning word-by-word captions",
    )
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    topics: list[str] = []
    if args.topic:
        topics.append(args.topic)
    if args.from_scraper:
        csv_path = _latest_scraper_csv()
        if not csv_path:
            print(
                "  ! No scraper CSV found under scraper/output/. "
                "Run `python3 scraper/run.py` first.",
                file=sys.stderr,
            )
            return 2
        topics.extend(_topics_from_csv(csv_path, args.limit))
    if not topics:
        p.error("provide --topic and/or --from-scraper")

    topics = topics[: max(args.limit, 1)] if args.from_scraper else topics

    for t in topics:
        try:
            render_one(
                t,
                voice=args.voice,
                rate=args.rate,
                pitch=args.pitch,
                mode=args.mode,
                title=args.title,
                burn_captions=not args.no_captions,
                seed=args.seed,
            )
        except Exception as exc:  # keep batch going
            print(f"  ! failed on '{t}': {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
