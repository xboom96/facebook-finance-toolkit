#!/usr/bin/env python3
"""Render a vertical 9:16 faceless Reel from a script + per-segment audio.

The renderer needs **ffmpeg** and **Pillow**. No other system deps.

Outputs ``1080x1920`` H.264 MP4 at 30 fps with:

* A pre-generated dark gradient background (PNG produced by Pillow).
* Large bold on-screen captions per segment (``drawtext`` filter).
* Burned-in word-by-word captions from the combined SRT (``subtitles`` filter)
  — TikTok-style, optional.
* Concatenated voiceover MP3.

Usage as a library:

    from shorts.render import render_short
    render_short(segments, out_path=Path("out.mp4"), captions_srt=srt_path)

CLI usage is provided by ``shorts/pipeline.py``.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw

# Default canvas
WIDTH = 1080
HEIGHT = 1920
FPS = 30

# Default font — DejaVu Sans Bold is bundled on most Linux distros and works
# fine inside Devin environments. Override via env or --font.
DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Visual theme (dark + finance-green accent — high CPM look).
BG_TOP = (15, 22, 38)      # deep navy
BG_BOTTOM = (5, 10, 20)    # near black
ACCENT = (16, 185, 129)    # finance green


@dataclass
class RenderSegment:
    """One on-screen overlay for the duration of an audio clip."""

    role: str
    audio_path: Path
    duration_s: float
    on_screen: str = ""


# ---------------------------------------------------------------------------
# Background image
# ---------------------------------------------------------------------------


def make_background(path: Path, *, title: str = "") -> None:
    """Render a 1080x1920 vertical-gradient PNG with an optional title at top."""
    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        r = int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio)
        g = int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio)
        b = int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Accent bar at top — gives the visual brand identity
    draw.rectangle([(0, 0), (WIDTH, 12)], fill=ACCENT)

    # Optional brand title near the top
    if title:
        try:
            from PIL import ImageFont

            font = ImageFont.truetype(DEFAULT_FONT, 56)
            bbox = draw.textbbox((0, 0), title, font=font)
            tw = bbox[2] - bbox[0]
            draw.text(((WIDTH - tw) / 2, 80), title, font=font, fill=(230, 230, 230))
        except Exception:
            # Font not available; skip the title rather than crash.
            pass

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------


def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH")


def _escape_drawtext(text: str) -> str:
    """Escape a string for use inside an ffmpeg drawtext ``text=`` value.

    See https://ffmpeg.org/ffmpeg-filters.html#Notes-on-filtergraph-escaping
    """
    # Order matters: backslash first.
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\u2019")  # straight quote -> typographic
    text = text.replace("%", "\\%")
    text = text.replace(",", "\\,")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace(";", "\\;")
    return text


def _escape_filter_path(path: str) -> str:
    """Escape a filesystem path for use as the *value* of a filter option."""
    # In ffmpeg filter syntax, colons separate option=value pairs, single quotes
    # delimit the option value, and backslashes start escapes. We turn each of
    # those into the right escaped form so a Windows-style or absolute path
    # round-trips correctly.
    return path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def _wrap_text(text: str, *, max_chars_per_line: int = 14) -> str:
    """Wrap text by inserting ``\\n`` line breaks at word boundaries.

    Default of 14 chars/line keeps a 72pt bold line inside a 1080px canvas
    with comfortable margins.
    """
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        candidate = (current + " " + w).strip()
        if len(candidate) <= max_chars_per_line or not current:
            current = candidate
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return "\n".join(lines)


def _build_drawtext_chain(
    segments: Iterable[RenderSegment],
    *,
    font: str,
) -> str:
    """Build a chained drawtext filter showing each on_screen during its window."""
    chain_parts: list[str] = []
    t = 0.0
    for seg in segments:
        end = t + seg.duration_s
        if seg.on_screen.strip():
            wrapped = _wrap_text(seg.on_screen.strip())
            escaped = _escape_drawtext(wrapped)
            chain_parts.append(
                "drawtext="
                f"fontfile='{font}':"
                f"text='{escaped}':"
                "fontcolor=white:"
                "fontsize=72:"
                "borderw=5:"
                "bordercolor=black@0.85:"
                "line_spacing=14:"
                "x=(w-text_w)/2:"
                "y=h*0.16:"
                f"enable='between(t,{t:.3f},{end:.3f})'"
            )
        t = end
    if not chain_parts:
        # Always have at least a no-op so the filter graph is valid.
        return "null"
    return ",".join(chain_parts)


def _concat_audio(audio_paths: list[Path], out_path: Path) -> Path:
    """Concatenate MP3s with the ffmpeg concat demuxer."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in audio_paths:
            f.write(f"file '{p.resolve()}'\n")
        list_path = Path(f.name)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                str(out_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        # Fallback: re-encode (covers MP3s with mismatched headers).
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(out_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    finally:
        list_path.unlink(missing_ok=True)
    return out_path


# ---------------------------------------------------------------------------
# SRT -> ASS conversion (so FontSize is pixel-accurate via PlayRes)
# ---------------------------------------------------------------------------


_SRT_TS_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def _srt_time_to_ass(h: int, m: int, s: int, ms: int) -> str:
    """ASS uses centiseconds: H:MM:SS.cc (no leading zero on hours)."""
    cs = ms // 10
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _srt_to_ass(
    src_srt: Path,
    out_ass: Path,
    *,
    play_res_x: int,
    play_res_y: int,
    font_name: str = "DejaVu Sans",
    font_size: int = 56,
    primary_color: str = "&H00FFFFFF",   # AABBGGRR — white
    outline_color: str = "&H00000000",   # black outline
    margin_v: int = 320,
    bold: bool = True,
) -> Path:
    """Convert an SRT file to an ASS file with a known PlayRes.

    ASS ``FontSize`` is measured against ``PlayResY`` (not pixels). By matching
    PlayRes to the output canvas we make the font size effectively pixel-accurate
    and avoid the "tiny text balloons to giant text" problem.
    """
    out_ass.parent.mkdir(parents=True, exist_ok=True)
    src_text = src_srt.read_text(encoding="utf-8")

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        f"PlayResX: {play_res_x}\n"
        f"PlayResY: {play_res_y}\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font_name},{font_size},{primary_color},&H000000FF,"
        f"{outline_color},&H80000000,{-1 if bold else 0},0,0,0,100,100,0,0,1,"
        f"4,0,2,60,60,{margin_v},1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    events: list[str] = []
    blocks = src_text.strip().split("\n\n")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        m = _SRT_TS_RE.search(block)
        if not m:
            continue
        start = _srt_time_to_ass(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        end = _srt_time_to_ass(int(m.group(5)), int(m.group(6)), int(m.group(7)), int(m.group(8)))
        # Lines after the timestamp line are the cue text.
        lines = block.splitlines()
        ts_idx = next((i for i, ln in enumerate(lines) if "-->" in ln), 1)
        text = " ".join(lines[ts_idx + 1 :]).strip()
        if not text:
            continue
        # Escape ASS special chars.
        text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        text = text.replace("\n", "\\N")
        events.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
        )

    out_ass.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return out_ass


# ---------------------------------------------------------------------------
# Public renderer
# ---------------------------------------------------------------------------


def render_short(
    segments: list[RenderSegment],
    out_path: Path,
    *,
    bg_image: Path | None = None,
    captions_srt: Path | None = None,
    font: str = DEFAULT_FONT,
    title: str = "MONEY 60",
    work_dir: Path | None = None,
) -> Path:
    """Assemble the final vertical MP4.

    * ``segments`` — one entry per audio clip with its on-screen overlay text.
    * ``captions_srt`` — optional SRT (e.g. word-by-word from edge-tts SubMaker)
      to burn in at the bottom as TikTok-style captions.
    * ``bg_image`` — override the auto-generated background.
    """
    _require_ffmpeg()
    if not segments:
        raise ValueError("no segments provided to render_short")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = work_dir or out_path.parent / "_work"
    work.mkdir(parents=True, exist_ok=True)

    # 1. Background.
    bg = bg_image
    if bg is None:
        bg = work / "bg.png"
        make_background(bg, title=title)

    # 2. Concatenate audio.
    audio_paths = [s.audio_path for s in segments]
    combined_audio = _concat_audio(audio_paths, work / "combined.mp3")

    # 3. Build filter graph.
    total = sum(s.duration_s for s in segments)

    drawtext_chain = _build_drawtext_chain(segments, font=font)

    # Subtle kenburns-style slow zoom to fight platform "static image" detection.
    # zoompan needs a fixed number of frames; we drive it by the total duration.
    frames = max(int(total * FPS), 1)
    zoom_filter = (
        "zoompan=z='min(zoom+0.0006,1.12)'"
        ":d=" + str(frames) +
        f":s={WIDTH}x{HEIGHT}:fps={FPS}"
    )

    video_filters: list[str] = [
        f"scale={WIDTH}:{HEIGHT}",
        "format=yuv420p",
        zoom_filter,
        drawtext_chain,
    ]

    if captions_srt and Path(captions_srt).exists():
        # libass sizes FontSize against the script's PlayRes, NOT pixels.
        # The default SRT->ASS conversion uses PlayRes 384x288, so a "FontSize=28"
        # gets scaled ~6.7x at 1920px tall. We side-step this by converting the
        # SRT to a proper ASS file with PlayRes matching the canvas, so font
        # sizes are effectively pixel-accurate.
        ass_path = work / "combined.ass"
        _srt_to_ass(
            Path(captions_srt),
            ass_path,
            play_res_x=WIDTH,
            play_res_y=HEIGHT,
            font_name="DejaVu Sans",
            font_size=56,
            margin_v=420,
            bold=True,
        )
        ass_arg = _escape_filter_path(str(ass_path.resolve()))
        video_filters.append(f"subtitles='{ass_arg}'")

    vf = ",".join(v for v in video_filters if v and v != "null")

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(bg),
        "-i",
        str(combined_audio),
        "-vf",
        vf,
        "-t",
        f"{total:.3f}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-r",
        str(FPS),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    print("  $", " ".join(shlex.quote(c) for c in cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed:\n" + proc.stderr.decode("utf-8", errors="replace")[-4000:]
        )
    return out_path


def main() -> int:
    p = argparse.ArgumentParser(description="Render a vertical 9:16 short from JSON spec")
    p.add_argument(
        "spec",
        help="Path to JSON spec produced by pipeline.py "
        "(list of {role, audio_path, duration_s, on_screen})",
    )
    p.add_argument("--out", required=True)
    p.add_argument("--srt", default=None)
    p.add_argument("--font", default=DEFAULT_FONT)
    p.add_argument("--title", default="MONEY 60")
    args = p.parse_args()

    raw = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    segments = [
        RenderSegment(
            role=s["role"],
            audio_path=Path(s["audio_path"]),
            duration_s=float(s["duration_s"]),
            on_screen=s.get("on_screen", ""),
        )
        for s in raw
    ]
    render_short(
        segments,
        Path(args.out),
        captions_srt=Path(args.srt) if args.srt else None,
        font=args.font,
        title=args.title,
    )
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
