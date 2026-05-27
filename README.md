# Facebook Finance Toolkit

A seven-module toolkit for monetizing a faceless personal-finance presence — from Facebook page content all the way to Fiverr fulfilment and Adobe Stock passive income.

**Strategy & content**

1. **[`STRATEGY.md`](STRATEGY.md)** — 30-day content plan, content pillars, viral hook templates, faceless video format, monetization stacking, and a migration playbook.
2. **[`scraper/`](scraper/)** — pulls today's trending personal-finance content (Google News, Reddit, Hacker News, optional YouTube) into a daily CSV/Markdown report you can use as Reel ideas.
3. **[`dashboard/`](dashboard/)** — a small Flask web app that reads your Facebook Page metrics via the Meta Graph API and ranks your posts by estimated revenue and engagement.

**Production & monetization**

4. **[`shorts/`](shorts/)** — end-to-end faceless YT Shorts / Facebook Reels / TikTok pipeline. Topic → AI script → free TTS voiceover → vertical 1080×1920 H.264 MP4 with overlays + burned captions. One command, no API keys required.
5. **[`publish/`](publish/)** — auto-publish the generated MP4 straight to your Facebook Page as a Reel or classic Video via the Meta Graph API. Stdlib-only, dry-run-safe, and bolted onto `shorts/pipeline.py` with a single `--publish-fb reels` flag.
6. **[`fiverr/`](fiverr/)** — gig audit + three optimized 2026-ready gig templates (long-form YT, Shorts/Reels, done-for-you AI faceless package) plus a 14-day Level-2 revival checklist and Buyer-Request outreach templates.
7. **[`adobe-stock/`](adobe-stock/)** — batch metadata generator for Adobe Stock contributor uploads. Curated keyword libraries for the 4 highest-CPM niches (finance, business, AI/tech, lifestyle), plus a strategy doc on what to actually shoot/render.

> **Niche:** Personal Finance · **Language:** English · **Style:** Faceless (text + stock + AI voice)
> Built to help boost Content Monetization earnings on a Facebook page **and** to pay the bills with Fiverr + Adobe Stock while the page grows.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/xboom96/facebook-finance-toolkit.git
cd facebook-finance-toolkit

# 2. Generate today's content ideas (no auth required)
python3 scraper/run.py --limit 10

# 3. Render a faceless Short from any topic (no API keys needed)
pip install -r shorts/requirements.txt
sudo apt-get install -y ffmpeg   # if not already installed
python3 shorts/pipeline.py --topic "5 subscriptions to cancel today"
# open shorts/output/<date>/<slug>/short.mp4

# 4. Run the dashboard in demo mode (no Facebook auth required)
pip install -r dashboard/requirements.txt
python3 dashboard/app.py --demo
# open http://127.0.0.1:5000

# 5. When you're ready for real data — see SETUP_META_TOKEN.md
python3 dashboard/app.py

# 6. Tag a folder of stock photos for Adobe Stock upload
python3 adobe-stock/prep.py ./my-photos --niche finance --out adobe_stock.csv

# 7. Generate a Short AND publish it straight to your Facebook Page (set token first)
export META_PAGE_ID=…
export META_PAGE_TOKEN=…
python3 shorts/pipeline.py --topic "…" --publish-fb reels
```

---

## 1. Strategy ([`STRATEGY.md`](STRATEGY.md))

A complete 30-day playbook covering:

- 5 content pillars (Save, Earn, Invest, Mistakes, Tools) with target post mix
- 10 viral hook templates
- 60–90 second faceless video structure (Hook → Promise → Value → Example → CTA → Loop)
- Day-by-day topic calendar
- Monetization stacking beyond in-stream ads (affiliates, lead magnets, digital products)
- Compliance traps to avoid Meta restrictions
- Two migration paths from `freegirlss`: fresh page vs. pivot

Use this as your weekly checklist.

---

## 2. Trending-content scraper ([`scraper/run.py`](scraper/run.py))

Pulls trending personal-finance content into a daily report. **No paid APIs required.**

### Sources

| Source | Auth needed | Reliability |
|---|---|---|
| **Google News RSS** | none | ★★★★★ — the primary source |
| **Hacker News** (Algolia API) | none | ★★★★☆ — finance-adjacent stories |
| **Reddit** (public JSON) | none, but Reddit blocks many cloud IPs | ★★★☆☆ — works from residential IPs |
| **YouTube Shorts** | free Google API key in `YOUTUBE_API_KEY` env var | ★★★★☆ — opt-in |

### Usage

```bash
# All sources (Reddit may 403 from cloud/VPN IPs)
python3 scraper/run.py --limit 10

# Skip individual sources
python3 scraper/run.py --skip-reddit --skip-youtube

# Enable YouTube (get a free key at https://console.cloud.google.com/apis/credentials)
export YOUTUBE_API_KEY="AIza..."
python3 scraper/run.py --limit 10
```

### Output

Each run writes two files to `scraper/output/`:

```
scraper/output/trending-2026-05-18.csv   # spreadsheet-friendly
scraper/output/trending-2026-05-18.md    # readable shortlist with hook ideas
```

The Markdown file has one `## Source` section per source with a table of:

| Score | Community | Title | Hook idea | Link |

The **Hook idea** column converts each title into a Reel hook ready to feed into the script prompt in [`docs/prompts.md`](docs/prompts.md).

### Daily workflow

```bash
# Morning
python3 scraper/run.py --limit 10

# Open today's report
xdg-open scraper/output/trending-$(date +%F).md   # or `open` on macOS

# Pick 1 hook → paste into ChatGPT/Claude with the prompt from docs/prompts.md
# → generate script → ElevenLabs voice → CapCut edit → post at 6 PM EST
```

---

## 3. Meta Graph API earnings dashboard ([`dashboard/app.py`](dashboard/app.py))

Small Flask app that shows:

- **Page summary**: name, follower count, picture
- **4 top-line stats**: impressions, reach, avg engagement rate, estimated revenue
- **Top 10 posts by estimated revenue**
- **Top 10 posts by engagement rate**
- **Full recent-post table** with impressions, reach, video views, avg watch time, engagement rate, estimated $

### Run it

```bash
pip install -r dashboard/requirements.txt

# Demo mode (synthetic data, no Facebook auth)
python3 dashboard/app.py --demo

# Real mode — visit http://127.0.0.1:5000/setup, paste Page ID + Access Token
python3 dashboard/app.py
```

See **[SETUP_META_TOKEN.md](SETUP_META_TOKEN.md)** for a step-by-step guide on generating a long-lived Page Access Token.

### About the "estimated revenue" number

Meta does **not** expose per-post in-stream earnings via the public Graph API. The dashboard takes a user-configurable RPM (default $5 per 1,000 impressions) and multiplies it by each post's `post_impressions`. To calibrate:

1. Get your last 30-day in-stream earnings from Meta Creator Studio.
2. Get the same period's total impressions from this dashboard.
3. Compute `RPM = earnings / impressions × 1000`.
4. Update RPM in the dashboard setup page.

Once you've calibrated, the dashboard tells you **which posts earn the most per impression**, so you double down on what works.

---

## 4. Faceless Shorts / Reels pipeline ([`shorts/`](shorts/))

Generates a fully-produced 60–80 second faceless personal-finance Short from
a single topic string. **No API keys required** by default — uses Microsoft
Edge's free Neural TTS for voiceover and FFmpeg for rendering.

```bash
# One-shot from a topic
python3 shorts/pipeline.py --topic "3 money mistakes people make at 30"

# Batch from the scraper output
python3 scraper/run.py --limit 20
python3 shorts/pipeline.py --from-scraper --limit 5
```

Each run produces a folder with `script.md`, per-segment MP3s, captions in
SRT and ASS, a generated background, the final `short.mp4`, and a
`metadata.json` with title/description/hashtags ready to paste into
YouTube/Facebook/TikTok. See [`shorts/README.md`](shorts/README.md) for the
full architecture and roadmap.

---

## 5. Auto-publish to your Facebook Page ([`publish/`](publish/))

Closes the loop between the `shorts/` pipeline and your Facebook Page so a
fresh Short can go from idea to live Reel in a single command:

```bash
# Render + publish in one shot
export META_PAGE_ID=123456789012345
export META_PAGE_TOKEN=EAAG…             # see publish/README.md for how to mint this
python3 shorts/pipeline.py --topic "5 subscriptions to cancel today" --publish-fb reels

# Batch from today's trending hooks → 5 Reels uploaded back-to-back
python3 shorts/pipeline.py --from-scraper --limit 5 --publish-fb reels

# Dry-run first (no Meta calls, just shows what would be uploaded)
python3 -m publish.cli --short shorts/output/<date>/<slug> --as reels --dry-run
```

Supports both the **Reels API** (3-phase resumable upload, native Reel
placement, eligible for Reels Play bonus where available) and the
**classic Videos API** (single multipart upload). See
[`publish/README.md`](publish/README.md) for the 10-minute token setup
guide and failure modes.

---

## 6. Fiverr revival + gigs ([`fiverr/`](fiverr/))

If you already have a Fiverr seller account, this is the fastest path to
cash. It has:

- A day-by-day [revival checklist](fiverr/profile-revival-checklist.md) for
  stalled Level-2 accounts (typical recovery: 14 days).
- Three copy-paste-ready 2026 gig templates: [long-form YT editing](fiverr/gig-1-youtube-faceless-editing.md), [Shorts/Reels](fiverr/gig-2-shorts-reels-tiktok.md), and a [done-for-you AI faceless package](fiverr/gig-3-ai-faceless-video-package.md) that you fulfil with the `shorts/` pipeline above.
- [Outreach templates](fiverr/outreach-templates.md) for Buyer Requests,
  Upwork crossover, and cold DMs.

---

## 7. Adobe Stock contributor pipeline ([`adobe-stock/`](adobe-stock/))

Batch metadata generator + niche keyword libraries for Adobe Stock
contributors. Walks a folder of images/videos and writes the exact CSV
format Adobe accepts for SFTP+CSV uploads.

```bash
python3 adobe-stock/prep.py ./my-photos/finance --niche finance --out adobe_stock.csv
```

See [`adobe-stock/stock-strategy.md`](adobe-stock/stock-strategy.md) for
what actually sells on Adobe Stock right now and a realistic month-by-month
income model.

---

## Project layout

```
facebook-finance-toolkit/
├── README.md                 ← this file
├── STRATEGY.md               ← 30-day content playbook
├── SETUP_META_TOKEN.md       ← how to get a Page Access Token
├── docs/
│   └── prompts.md            ← LLM prompts for Reels & carousels
├── scraper/
│   ├── run.py                ← trending content scraper
│   └── output/               ← daily CSV + Markdown reports
├── dashboard/
│   ├── app.py                ← Flask app
│   ├── requirements.txt
│   └── templates/            ← Jinja2 HTML
├── shorts/                   ← faceless Shorts / Reels pipeline
│   ├── pipeline.py           ← CLI orchestrator
│   ├── script_gen.py         ← topic → script
│   ├── tts.py                ← script → Edge-TTS voiceover
│   ├── render.py             ← FFmpeg + Pillow video renderer
│   └── output/               ← generated MP4s + scripts
├── publish/                  ← Facebook Page auto-publish
│   ├── fb_reels.py           ← Reels API (resumable upload)
│   ├── fb_video.py           ← classic Videos API (multipart)
│   ├── cli.py                ← `python -m publish.cli ...`
│   └── test_smoke.py         ← offline test suite (urlopen mocked)
├── fiverr/                   ← gig templates + revival checklist
└── adobe-stock/              ← batch metadata generator
    ├── prep.py
    └── keywords.py
```

---

## Roadmap (ideas, not yet built)

- Auto-cross-post the picked daily idea to Notion / Trello.
- Pull `creator_studio/in_stream` earnings via the Marketing API once a Business Manager is set up.
- Add Instagram Reels parallel scraping (`graph.instagram.com`).
- Schedule the scraper as a daily cron job and email the Markdown report.
- Auto-upload generated `shorts/output/*/short.mp4` to YouTube via the Data API.
- ✓ Auto-publish Reels via Meta's `/{page-id}/video_reels` Graph API endpoint — shipped in [`publish/`](publish/).
- Mirror to Instagram Reels via the `/{ig-user-id}/media` endpoint (next).
- SFTP-upload generated CSVs straight to the Adobe Stock contributor portal (next).
- Direct SFTP upload step in `adobe-stock/prep.py` (Adobe contributor SFTP credentials).

---

## License

MIT. Use it however you want.

## Disclaimer

This toolkit produces *educational* content guidance. It does not provide financial advice. Meta's monetization rules change frequently — check Meta Creator Hub before scaling.
