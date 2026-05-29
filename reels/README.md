# Viral Reels Script Generator (`reels/`)

Turn one idea into a complete, ready-to-shoot Facebook Reel package. Give it a
**niche**, a **topic**, a **publish date** and a **target duration**, and it
returns everything you need for a faceless short:

- A scroll-stopping **hook** (spoken + on-screen) and *why it works*
- A full **voiceover script** structured for retention
  (Hook → Promise → Value beats → Proof → CTA → Loop)
- **Visual ideas** / B-roll search terms for every beat
- A **title**, **caption** and **description** tuned for the feed
- A set of **tags** (hashtags) mixing niche, topic and reach keywords
- A **music & pacing** suggestion and a **viral checklist**

It is **niche-agnostic** (finance, fitness, travel, cooking, tech, …) and runs
fully **offline & deterministic** — no API key, no login. Same inputs (and
seed) always produce the same package.

---

## CLI

```bash
python3 reels/generate.py \
  --niche "personal finance" \
  --topic "3 money mistakes that keep you broke" \
  --date 2026-05-29 \
  --duration 60

# JSON output (pipe into other tools)
python3 reels/generate.py --niche fitness --topic "morning routine" --json

# Reproducible output
python3 reels/generate.py --topic "save $5k this year" --seed 42
```

| Flag | Default | Meaning |
|---|---|---|
| `--niche` | `personal finance` | content niche |
| `--topic` | *(required)* | the specific Reel idea |
| `--date` | today | publish date `YYYY-MM-DD` (drives best-time-to-post) |
| `--duration` | `60` | target length in seconds (scales the number of beats) |
| `--seed` | random | seed for reproducible output |
| `--json` | off | emit JSON instead of Markdown |

The number of value beats scales with duration: ≤20s → 1, ≤35s → 2, ≤55s → 3,
≤80s → 4, ≤110s → 5, else 6. A proof/example beat is added for clips ≥45s.

---

## Web app

```bash
pip install -r reels/requirements.txt
python3 reels/app.py
# open http://127.0.0.1:5001
```

Fill in niche / topic / date / duration, hit **Generate script**, and the full
package renders on screen with copy buttons for the caption, description and
tags. There's also a JSON endpoint:

```
GET /api/generate?niche=travel&topic=cheap+flights+hack&duration=30
```

---

## How it fits the toolkit

Use [`scraper/run.py`](../scraper/run.py) to find a trending **topic**, drop it
into this generator to get a full **script package**, then film it faceless
(stock B-roll + AI voice + captions) per [`STRATEGY.md`](../STRATEGY.md). The
generator is the bridge between "what should I post?" and "here's the script".
