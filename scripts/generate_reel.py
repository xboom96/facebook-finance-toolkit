#!/usr/bin/env python3
"""Generate a 9:16 Reel video end-to-end from a script JSON file.

Pipeline:
1. Load a script JSON (hook, sections[], cta) — see scripts/reel-template.json.
2. Generate voiceover with gTTS (free) -> single MP3.
3. Probe segment durations with ffprobe so captions and section headers stay
   in sync with the audio.
4. Assemble a 1080x1920 video with:
   - Animated dark gradient background
   - A big hook card at the top during the first segment
   - A static lower-third with the section number + section text
   - Per-section caption text drawn in white with a black stroke
   - Final CTA card during the last segment
5. Mux the voiceover audio.

Dependencies: gtts, ffmpeg, ffprobe.

Usage:
    python scripts/generate_reel.py scripts/reel-template.json output.mp4
    # or with options
    python scripts/generate_reel.py scripts/reel-template.json out.mp4 \
        --tts-lang en --tts-tld co.uk
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from gtts import gTTS

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

WIDTH = 1080
HEIGHT = 1920
FPS = 30

# Use whichever bold sans-serif font is most likely to be installed.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
    "C:\\Windows\\Fonts\\arialbd.ttf",  # Windows
]


def find_font() -> str:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return path
    raise RuntimeError("No bold sans-serif font found; install fonts-dejavu.")


def ensure_tool(name: str) -> None:
    if not shutil.which(name):
        raise RuntimeError(f"Required tool not found on PATH: {name}")


@dataclass
class Section:
    """One section of the Reel — a chunk of voiceover with its own caption."""

    text: str            # what the voice says (also the caption text)
    header: str          # a short on-screen label, e.g. "1. STREAMING APPS"
    duration: float = 0.0  # filled in after probing the synthesized audio


@dataclass
class Script:
    topic: str           # used for filename, log output
    hook: str            # 0-3s big text card
    sections: list[Section]
    cta: str             # final 3-5s call-to-action text


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def load_script(path: Path) -> Script:
    with path.open() as f:
        data = json.load(f)
    return Script(
        topic=data["topic"],
        hook=data["hook"],
        sections=[Section(text=s["text"], header=s["header"]) for s in data["sections"]],
        cta=data["cta"],
    )


def synth_voice(text: str, out: Path, lang: str = "en", tld: str = "us") -> None:
    """Generate an MP3 using gTTS."""
    tts = gTTS(text=text, lang=lang, tld=tld, slow=False)
    tts.save(str(out))


def probe_duration(path: Path) -> float:
    """Return the audio duration in seconds via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def ffescape(text: str) -> str:
    """Escape a string for use inside an ffmpeg drawtext text= field."""
    # See https://ffmpeg.org/ffmpeg-filters.html#Notes-on-filtergraph-escaping
    text = text.replace("\\", "\\\\")
    text = text.replace(":", r"\:")
    text = text.replace("'", r"\u2019")  # smart quote — drawtext mangles raw '
    text = text.replace("%", r"\%")
    return text


def split_into_lines(text: str, max_chars: int = 22) -> list[str]:
    """Wrap text into lines, breaking on word boundaries, max ~max_chars wide."""
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        candidate = (cur + " " + w).strip()
        if len(candidate) <= max_chars:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# -----------------------------------------------------------------------------
# ffmpeg filter graph
# -----------------------------------------------------------------------------


def build_filtergraph(script: Script, total_duration: float, font: str,
                      hook_duration: float = 3.0,
                      cta_duration: float = 3.5) -> str:
    """Return the filter_complex string for ffmpeg.

    Timeline layout:
        [0, hook_duration]            -> big centered hook card
        [hook_duration, total - cta]  -> sections cycle through, header + body
        [total - cta, total]          -> green CTA card
    """
    parts: list[str] = []

    # 1) Background: dark navy gradient (top) -> near-black (bottom).
    parts.append(
        f"gradients=s={WIDTH}x{HEIGHT}:c0=0x0E2533:c1=0x070A12:x0=0:y0=0:"
        f"x1=0:y1={HEIGHT}:r={FPS}:d={total_duration},format=yuv420p[base]"
    )

    # 2) Layered text. We'll keep adding drawtext filters in a chain.
    chain_in = "[base]"
    chain_out_idx = 0

    def add_drawtext(text: str, *, x: str, y: str, fontsize: int, color: str,
                     borderw: int, enable_expr: str | None = None,
                     box: bool = False, box_color: str = "0x00000088",
                     line_spacing: int = 10) -> None:
        nonlocal chain_in, chain_out_idx
        chain_out_idx += 1
        out_label = f"v{chain_out_idx}"
        text_arg = "text=" + "'" + ffescape(text) + "'"
        enable = f":enable='{enable_expr}'" if enable_expr else ""
        box_args = f":box=1:boxcolor={box_color}:boxborderw=24" if box else ""
        parts.append(
            f"{chain_in}drawtext=fontfile={font}:{text_arg}:fontcolor={color}:"
            f"fontsize={fontsize}:x={x}:y={y}:borderw={borderw}:bordercolor=black:"
            f"line_spacing={line_spacing}{box_args}{enable}[{out_label}]"
        )
        chain_in = f"[{out_label}]"

    # Sections are aligned to their actual audio timing so captions stay in sync.
    # Section i plays from section_start[i] until section_start[i] + sec.duration.
    # During the first hook_duration seconds AND the last cta_duration seconds,
    # the caption/header are hidden behind the hook/CTA overlay.
    sec_starts: list[float] = []
    cursor = 0.0
    for sec in script.sections:
        sec_starts.append(cursor)
        cursor += sec.duration
    sections_end = cursor  # CTA voice starts here

    cta_start = sections_end
    # Pad CTA visual a touch longer than the voice if there's time left.
    cta_visual_end = total_duration

    # ---- Section headers + captions (drawn BEFORE the overlay layers so the
    # hook/CTA can sit on top during their windows)
    for sec, start in zip(script.sections, sec_starts):
        end = start + sec.duration
        # Skip drawing inside the hook window OR the CTA window
        visible_start = max(start, hook_duration)
        visible_end = min(end, cta_start)
        if visible_start >= visible_end:
            continue
        if sec.header:
            add_drawtext(
                sec.header,
                x="(w-text_w)/2",
                y="h*0.18",
                fontsize=82,
                color="0x4ADE80",  # emerald-400
                borderw=6,
                enable_expr=f"between(t,{visible_start:.3f},{visible_end:.3f})",
            )
        if sec.text:
            cap_lines = split_into_lines(sec.text, max_chars=22)
            cap_text = "\n".join(cap_lines)
            add_drawtext(
                cap_text,
                x="(w-text_w)/2",
                y="(h-text_h)/2",
                fontsize=68,
                color="white",
                borderw=6,
                enable_expr=f"between(t,{visible_start:.3f},{visible_end:.3f})",
                line_spacing=18,
            )

    # ---- Big centered hook card during [0, hook_duration]
    # Draw a dark box behind it so the section caption is fully covered.
    parts.append(
        f"{chain_in}drawbox=x=0:y=0:w={WIDTH}:h={HEIGHT}:color=0x070A12@0.95:t=fill:"
        f"enable='between(t,0,{hook_duration:.3f})'[hbg]"
    )
    chain_in = "[hbg]"

    hook_lines = split_into_lines(script.hook, max_chars=14)
    hook_text = "\n".join(hook_lines)
    add_drawtext(
        hook_text,
        x="(w-text_w)/2",
        y="(h-text_h)/2",
        fontsize=120,
        color="white",
        borderw=10,
        enable_expr=f"between(t,0,{hook_duration:.3f})",
        line_spacing=22,
    )

    # ---- CTA card: covers the screen during [cta_start, total]
    parts.append(
        f"{chain_in}drawbox=x=0:y=0:w={WIDTH}:h={HEIGHT}:color=0x000000@0.92:t=fill:"
        f"enable='between(t,{cta_start:.3f},{cta_visual_end:.3f})'[cbg]"
    )
    chain_in = "[cbg]"

    cta_lines = split_into_lines(script.cta, max_chars=18)
    cta_text = "\n".join(cta_lines)
    add_drawtext(
        cta_text,
        x="(w-text_w)/2",
        y="(h-text_h)/2",
        fontsize=110,
        color="0x4ADE80",
        borderw=10,
        enable_expr=f"between(t,{cta_start:.3f},{cta_visual_end:.3f})",
        line_spacing=18,
    )

    # ---- Bottom banner: page brand
    add_drawtext(
        "MONEYHABITS DAILY",
        x="(w-text_w)/2",
        y="h*0.92",
        fontsize=42,
        color="white",
        borderw=3,
    )

    # Final label is chain_in (e.g. "[v12]")
    parts.append(f"{chain_in}format=yuv420p[vout]")
    return ";".join(parts)


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------


def generate_reel(
    script_path: Path,
    out_path: Path,
    *,
    tts_lang: str = "en",
    tts_tld: str = "us",
) -> Path:
    ensure_tool("ffmpeg")
    ensure_tool("ffprobe")
    font = find_font()
    script = load_script(script_path)

    workdir = Path(tempfile.mkdtemp(prefix="reel_"))
    print(f"[1/5] Working in {workdir}")

    # 1) Synthesize voice per section so we know exact durations.
    print("[2/5] Synthesizing voice (gTTS)...")
    section_audios: list[Path] = []
    for i, sec in enumerate(script.sections, start=1):
        ap = workdir / f"sec{i}.mp3"
        synth_voice(sec.text, ap, lang=tts_lang, tld=tts_tld)
        # Caption window MUST equal the real audio duration so captions stay
        # in sync. No padding here — `-c copy` concat plays segments
        # back-to-back without gaps.
        sec.duration = probe_duration(ap)
        print(f"    section {i}: {sec.duration:.2f}s")
        section_audios.append(ap)

    # Synthesize CTA separately
    cta_audio = workdir / "cta.mp3"
    synth_voice(script.cta, cta_audio, lang=tts_lang, tld=tts_tld)
    cta_dur = probe_duration(cta_audio)
    print(f"    cta: {cta_dur:.2f}s")

    # 2) Concatenate all audio into one track
    print("[3/5] Concatenating audio...")
    audio_list = workdir / "audio_list.txt"
    with audio_list.open("w") as f:
        for a in section_audios:
            f.write(f"file '{a}'\n")
        f.write(f"file '{cta_audio}'\n")
    full_audio = workdir / "voice.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(audio_list),
         "-c", "copy", str(full_audio)],
        check=True, capture_output=True,
    )
    total = probe_duration(full_audio)
    print(f"    total duration: {total:.2f}s")

    # 3) Build filter graph — sections fit between hook and CTA windows.
    print("[4/5] Rendering video...")
    filtergraph = build_filtergraph(
        script, total, font, hook_duration=3.0, cta_duration=cta_dur
    )

    # 4) Single ffmpeg call to build video + mux audio
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:r={FPS}:d={total:.3f}",
        "-i", str(full_audio),
        "-filter_complex", filtergraph,
        "-map", "[vout]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    # 5) Cleanup
    print(f"[5/5] Done: {out_path}")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script_json", type=Path)
    parser.add_argument("output_mp4", type=Path)
    parser.add_argument("--tts-lang", default="en")
    parser.add_argument("--tts-tld", default="us",
                        help="gTTS top-level domain controls accent: us, co.uk, com.au, ca")
    args = parser.parse_args()

    try:
        generate_reel(args.script_json, args.output_mp4,
                      tts_lang=args.tts_lang, tts_tld=args.tts_tld)
    except subprocess.CalledProcessError as exc:
        print("FFMPEG FAILED", file=sys.stderr)
        print(exc.stderr.decode("utf-8", errors="replace") if exc.stderr else exc, file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
