# `shorts/` — faceless YouTube Short / FB Reel pipeline

End-to-end pipeline that turns a single topic into a ready-to-upload
1080×1920 vertical video in 30–60 seconds of compute. No paid APIs, no
voice talent, no editing software required.

```
topic / hook  →  script_gen.py  →  tts.py (edge-tts)  →  render.py (ffmpeg)  →  short.mp4
```

---

## What you get per run

For every topic, `pipeline.py` writes under `shorts/output/YYYY-MM-DD/<slug>/`:

| File | Purpose |
|---|---|
| `script.md` / `script.json` | The structured script (hook, promise, 3 tips, example, CTA, loop). |
| `seg_*.mp3` | Per-segment Edge TTS voiceover. |
| `seg_*.srt` | Per-segment word-by-word subtitles. |
| `combined.srt` | Full word-by-word SRT, used for burned captions. |
| `_work/bg.png` | Generated 1080×1920 dark-gradient background. |
| `_work/combined.mp3` | Full concatenated voiceover. |
| `short.mp4` | **Final 1080×1920 H.264 MP4 — upload this.** |
| `metadata.json` | Title, description, hashtags, b-roll terms — paste into FB/YT. |

---

## Setup (one time)

```bash
# System dependency
sudo apt-get install -y ffmpeg fonts-dejavu-core

# Python dependencies
pip install -r shorts/requirements.txt
```

The pipeline auto-detects `DejaVuSans-Bold.ttf`. Override with `--font` if you
want a more "FinanceBro" look (e.g. drop Inter / Bebas Neue into
`shorts/assets/` and pass its path).

---

## Quick start

### 1. Single topic

```bash
python3 shorts/pipeline.py --topic "5 subscriptions to cancel today"
```

### 2. Top-trending topic from today's scraper output

```bash
# Refresh today's trending finance topics
python3 scraper/run.py --limit 10

# Generate 5 Reels from the top 5 hooks
python3 shorts/pipeline.py --from-scraper --limit 5
```

### 3. Override the voice

```bash
python3 shorts/tts.py --list-voices | grep en-US

# Examples (free, no auth)
python3 shorts/pipeline.py --topic "..." --voice en-US-AndrewNeural  # default — male confident
python3 shorts/pipeline.py --topic "..." --voice en-US-GuyNeural     # male neutral
python3 shorts/pipeline.py --topic "..." --voice en-US-JennyNeural   # female warm
python3 shorts/pipeline.py --topic "..." --voice en-US-AriaNeural    # female news anchor
```

### 4. Higher-quality scripts via OpenAI (optional)

```bash
export OPENAI_API_KEY="sk-..."
python3 shorts/pipeline.py --topic "..." --mode openai
```

Falls back to the offline template script automatically if the API call fails.

---

## Daily workflow (15 minutes/day)

```bash
# Morning — pull today's trending finance topics
python3 scraper/run.py --limit 10

# Generate 3 Shorts back-to-back
python3 shorts/pipeline.py --from-scraper --limit 3

# Open today's output folder
xdg-open shorts/output/$(date +%F)/
```

For each generated short:

1. Open `metadata.json` → copy the title + description into FB/YT/TikTok.
2. (Optional) Replace the static background with stock B-roll from Pexels
   using the suggested `broll_terms` — drop it into `_work/bg_video.mp4`
   and re-run with `--bg-video` (see "advanced" below).
3. Upload `short.mp4`.

Three uploads/day across FB Reels + YT Shorts + Instagram Reels =
**90 pieces of content/month** with ~10 minutes of work per video. This
is how faceless channels actually compound.

---

## Architecture

`pipeline.py` orchestrates four steps:

1. **`script_gen.py`** — turn a topic into a structured `Script`.
   - **Offline mode (default)** assembles a deterministic 60–80s script
     from templates that follow [`STRATEGY.md`](../STRATEGY.md).
   - **OpenAI mode** calls `gpt-4o-mini` for a freshly written script
     when `OPENAI_API_KEY` is set.

2. **`tts.py`** — wraps [`edge-tts`](https://github.com/rany2/edge-tts).
   - Free Microsoft Edge Neural voices — no auth.
   - Produces one MP3 + one word-level SRT per segment.

3. **`render.py`** — assembles the final MP4 with `ffmpeg`.
   - 1080×1920 H.264, 30 fps, AAC audio.
   - `drawtext` overlays for big on-screen hook text per segment.
   - `subtitles=` filter burns the word-by-word SRT for TikTok-style
     captions.
   - `zoompan` adds subtle motion to fight the "static image" penalty.

4. **`pipeline.py`** — glues it together and writes `metadata.json`.

Each module is also runnable on its own — useful when you want to
debug script content without re-rendering, or render a custom video
from a manually edited script.

---

## Compliance & policy

The script templates in `script_gen.py` deliberately:

- Frame everything as **educational** ("here's what worked", "the math
  says..."), never as financial advice.
- Avoid words Meta flags: "free money", "easy money", "guaranteed",
  "passive income with no work".
- Include the disclaimer **"Not financial advice. Educational only."**
  in every generated description.

See [`STRATEGY.md` §7 — Compliance traps](../STRATEGY.md) for the full list.

---

## Roadmap

- [ ] Optional Pexels API integration — auto-download matching B-roll
      per segment and use it as background instead of the static gradient.
- [ ] Optional royalty-free background music mixer.
- [ ] Auto-upload via Meta Reels Publishing API + YouTube Data API.
- [ ] A/B test mode — generate the same topic with 3 different hooks
      and pick the winner from CTR data via the existing dashboard.
