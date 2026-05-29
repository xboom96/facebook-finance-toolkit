# Facebook Finance Toolkit

A 4-part toolkit for transitioning a Facebook page into a high-CPM personal-finance niche:

1. **[`STRATEGY.md`](STRATEGY.md)** — 30-day content plan, content pillars, viral hook templates, faceless video format, monetization stacking, and a migration playbook.
2. **[`scraper/`](scraper/)** — pulls today's trending personal-finance content (Google News, Reddit, Hacker News, optional YouTube) into a daily CSV/Markdown report you can use as Reel ideas.
3. **[`reels/`](reels/)** — a viral Reels **script generator** (CLI + Flask app). Input niche, topic, date and duration → get a full Reel package: hook, voiceover script, visual ideas, caption, title, description and tags. Offline, no API key.
4. **[`dashboard/`](dashboard/)** — a small Flask web app that reads your Facebook Page metrics via the Meta Graph API and ranks your posts by estimated revenue and engagement.

> **Niche:** Personal Finance · **Language:** English · **Style:** Faceless (text + stock + AI voice)
> Built to help boost Content Monetization earnings on a Facebook page.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/xboom96/facebook-finance-toolkit.git
cd facebook-finance-toolkit

# 2. Generate today's content ideas (no auth required)
python3 scraper/run.py --limit 10

# 3. Turn an idea into a full Reel script package (no auth required)
python3 reels/generate.py --niche "personal finance" --topic "3 money mistakes that keep you broke" --duration 60
# ...or run the web app:
pip install -r reels/requirements.txt
python3 reels/app.py            # open http://127.0.0.1:5001

# 4. Run the dashboard in demo mode (no Facebook auth required)
pip install -r dashboard/requirements.txt
python3 dashboard/app.py --demo
# open http://127.0.0.1:5000

# 5. When you're ready for real data — see SETUP_META_TOKEN.md
python3 dashboard/app.py
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

# Pick 1 hook → feed it to the Reels generator → script → AI voice → CapCut edit → post
python3 reels/generate.py --topic "<picked hook>" --duration 60
```

---

## 3. Viral Reels script generator ([`reels/`](reels/))

Turn a single idea into a complete, ready-to-shoot Reel package. **No API key, no login.**

Inputs: **niche**, **topic**, **date**, **duration** → outputs a scroll-stopping
**hook** (with *why it works*), a full **voiceover script** (Hook → Promise →
Value beats → Proof → CTA → Loop), **visual ideas / B-roll**, a **title**,
**caption**, **description**, **tags**, plus a music/pacing suggestion and a
viral checklist. It is niche-agnostic and fully deterministic (seedable).

```bash
# CLI (Markdown)
python3 reels/generate.py --niche "personal finance" \
  --topic "3 money mistakes that keep you broke" --date 2026-05-29 --duration 60

# CLI (JSON)
python3 reels/generate.py --niche fitness --topic "morning routine" --json

# Web app
pip install -r reels/requirements.txt
python3 reels/app.py            # open http://127.0.0.1:5001
# JSON API: /api/generate?niche=travel&topic=cheap+flights+hack&duration=30
```

The number of value beats scales with the target duration, and a proof beat is
added for clips ≥45s. See [`reels/README.md`](reels/README.md) for full docs.

---

## 4. Meta Graph API earnings dashboard ([`dashboard/app.py`](dashboard/app.py))

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
├── reels/
│   ├── generate.py           ← viral Reel script generator (CLI)
│   ├── app.py                ← Flask web app
│   ├── requirements.txt
│   └── templates/            ← Jinja2 HTML
└── dashboard/
    ├── app.py                ← Flask app
    ├── requirements.txt
    └── templates/            ← Jinja2 HTML
```

---

## Roadmap (ideas, not yet built)

- Auto-cross-post the picked daily idea to Notion / Trello.
- Pull `creator_studio/in_stream` earnings via the Marketing API once a Business Manager is set up.
- Add Instagram Reels parallel scraping (`graph.instagram.com`).
- Schedule the scraper as a daily cron job and email the Markdown report.

---

## License

MIT. Use it however you want.

## Disclaimer

This toolkit produces *educational* content guidance. It does not provide financial advice. Meta's monetization rules change frequently — check Meta Creator Hub before scaling.
