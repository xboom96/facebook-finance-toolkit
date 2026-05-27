# `fiverr/` — gig audit + optimized rewrites for faceless / YouTube editors

You already have a **Fiverr Level 2** account in YouTube / faceless channel
editing. This folder is everything you need to revive impressions and get
back to a steady order flow.

## What's in here

| File | What it is | Who it's for |
|---|---|---|
| [`profile-revival-checklist.md`](./profile-revival-checklist.md) | Day-by-day "wake the algorithm up" plan for a stalled Level 2 account. | Existing Level 2 sellers whose orders dropped to 0. |
| [`gig-1-youtube-faceless-editing.md`](./gig-1-youtube-faceless-editing.md) | Optimized gig — long-form faceless YouTube editing. | Highest-paying gig type for editors with HND. |
| [`gig-2-shorts-reels-tiktok.md`](./gig-2-shorts-reels-tiktok.md) | Optimized gig — viral Shorts / Reels / TikTok editing. | Volume gig — fast orders, $25–$50 each. |
| [`gig-3-ai-faceless-video-package.md`](./gig-3-ai-faceless-video-package.md) | Optimized gig — done-for-you AI faceless videos (script + voice + edit). | Premium gig — uses the `shorts/` pipeline in this repo as fulfillment. |
| [`outreach-templates.md`](./outreach-templates.md) | Buyer-Request / cold-DM / Upwork-crossover templates. | Sending 10/day = ~2 orders/week even if your gigs are dead. |

## How to use this folder

1. **First** — work through [`profile-revival-checklist.md`](./profile-revival-checklist.md).
   Most "dead" Level 2 accounts come back to life within 7–14 days of doing
   the checklist properly.
2. **Then** — copy-paste the three gigs in order. Don't replace your existing
   gigs all at once; create them as **new gigs** in different sub-categories
   so Fiverr's algorithm gives you fresh impressions on each.
3. **Daily** — use `outreach-templates.md` for 10 outbound messages a day.
   Outbound is what pays the bills while the algorithm decides whether to
   start ranking your gigs again.

## Realistic numbers

| Week | Expected outcome |
|---|---|
| 1 | 0–1 orders from outreach, gigs still indexed but invisible. |
| 2 | 1–3 orders. Algorithm starts showing your refreshed gigs. |
| 3–4 | 3–5 orders/week. First repeat client. |
| 5–8 | 6–10 orders/week. Promote gig becomes profitable. |
| 3+ months | Level 2 → Top Rated Seller eligibility. |

These assume you respond inside 1 hour during US business hours, deliver on
time, and never have a single cancellation in this period. Cancellations are
the #1 thing that kills a Fiverr revival.

## How this connects to the rest of the repo

The premium gig (#3, AI faceless video package) is fulfilled directly by the
[`shorts/` pipeline](../shorts/README.md) in this repo:

```
client orders gig #3
   ↓
you take their topic / brand
   ↓
python3 shorts/pipeline.py --topic "<their topic>"
   ↓
you tweak the script.md, re-render, deliver short.mp4
```

That gives you a $50–$120 gig you can fulfill in 30–45 minutes per video.
Net margin is essentially 100% — no software, no contractor, no API costs
beyond optional ElevenLabs/OpenAI if you want premium quality.

> See [`STRATEGY.md`](../STRATEGY.md) for the bigger picture: the same
> pipeline you fulfill Fiverr orders with also produces content for your
> own Facebook Reels / YouTube Shorts page, so every gig you fulfill also
> teaches the algorithm what you're good at.
