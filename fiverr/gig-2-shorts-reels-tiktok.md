# Gig 2 — YouTube Shorts / Instagram Reels / TikTok Editing (volume)

> Volume gig: lower price, faster turnaround, more orders per week.
> The math: 4 of these orders/week at $35 = $140/week ≈ Sri Lanka professional salary equivalent. Pair with Gig 1 (long-form) so high-ticket and high-volume coexist on your profile.

---

## Category / Sub-category

- Category: **Video & Animation**
- Sub-category: **Video Editing**
- Service type: **Shorts & Reels**

## Gig metadata

- Tags:
  1. `youtube shorts editor`
  2. `tiktok video editor`
  3. `instagram reels editor`
  4. `vertical video editor`
  5. `viral short editor`

---

## Title (70–80 chars)

```
I will edit your viral YouTube Shorts, TikTok and Instagram Reels
```

Alternatives:

- `I will edit 5 viral YouTube Shorts with captions and broll`
- `I will be your dedicated faceless TikTok and Reels editor`

---

## Description

> **Hi, I'm *Anusha* — a faceless content editor specializing in short-form vertical video for YouTube Shorts, Instagram Reels, and TikTok.**
>
> Short-form is *not* just a shorter version of your long-form video. It is its own format with its own rules. I edit Shorts to maximize **3 metrics that the algorithm actually weights:**
>
> 1. **First-frame retention** — viewers must commit in <1 second.
> 2. **Loop rate** — the ending must invite a rewatch.
> 3. **Watch time / replay** — average view duration on a 60s short must be >40s to get pushed.
>
> ### Every Short I deliver includes
>
> - **A pattern-interrupt hook in the first 15 frames** (zoom, sound, text)
> - **9:16 vertical 1080×1920 export** — never stretched or letterboxed
> - **Word-level animated captions** in your brand colors
> - **B-roll cuts every 1–2 seconds** to maintain attention
> - **A clean royalty-free music bed** beat-matched to your script
> - **A subtle loop edit** so the ending leads back to the hook
> - **Platform-specific exports** — YouTube Shorts (60s), Reels (90s), TikTok (3 min)
>
> ### Niches I edit deeply
>
> - Personal finance / money tips
> - Side hustles & entrepreneurship
> - Motivation / self-improvement
> - Cosmic-horror / scary stories (faceless)
> - Tech & AI tools
>
> ### Working with me
>
> - **Reply time:** ~30 minutes during US business hours
> - **Bulk discount:** the more Shorts in one order, the lower the per-short cost
> - **Source files:** delivered on request (+$5/clip)
>
> *Message me before ordering for a custom quote if you need >10 Shorts, multi-language captions, or a specific niche.*

---

## Packages

|  | **BASIC** | **STANDARD** | **PREMIUM** |
|---|---|---|---|
| **Title** | 1 viral Short | 3 viral Shorts | 5 viral Shorts |
| **Price** | $25 | $60 | $90 |
| **Per-short** | $25 | $20 | $18 |
| **Delivery** | 2 days | 3 days | 4 days |
| **Revisions** | 1 | 2 | Unlimited |
| **1080×1920** | ✓ | ✓ | ✓ |
| **Animated captions** | ✓ | ✓ | ✓ |
| **B-roll** | ✓ | ✓ | ✓ |
| **Music + ducking** | ✓ | ✓ | ✓ |
| **Color grade** | — | ✓ | ✓ |
| **Platform reformats (YT/Reels/TikTok)** | — | ✓ | ✓ |
| **Custom thumbnail** | — | — | ✓ (each) |

### Gig Extras

- **24-hour express delivery**: +$15 (BASIC), +$25 (STANDARD), +$40 (PREMIUM)
- **Additional Short**: $18 each (add up to +10)
- **Source files (CapCut/Premiere)**: $5 per Short
- **Voiceover via ElevenLabs / Edge TTS**: $5 per Short
- **Trending audio sync (TikTok-specific)**: $5 per Short

---

## FAQ

**Q: Do I need to provide voiceover?**
A: Not required. I can generate one with Edge TTS (free) or ElevenLabs (paid — pass-through cost). Just send me the script.

**Q: What about copyright?**
A: All B-roll and music I use is royalty-free and licensed for commercial use, including TikTok / Shorts monetization. I do NOT use copyrighted music unless you provide a license.

**Q: How fast can you deliver in a rush?**
A: 24-hour delivery is available as an extra for any package. Tell me before ordering.

**Q: Can you maintain a series style across multiple orders?**
A: Yes — I keep a project template for repeat clients and apply your captions style, colors, and music bed automatically. Repeat clients get a 10% discount starting the 3rd order.

**Q: Which platforms do you export for?**
A: Default is YouTube Shorts (60s, 1080×1920, 30fps). STANDARD and PREMIUM include Reels (90s, 1080×1920) and TikTok (3 min max). All exports preserve quality.

---

## Gallery

- **Image 1** (hero): A 9:16 phone mockup showing your best Short with the metric badge: `2.4M views · 73% retention`.
- **Image 2** (process): A 3-step infographic — `Script → My edit → Upload`.
- **Image 3** (packages): The BASIC/STANDARD/PREMIUM comparison table.
- **Video** (45–60s showreel): Stack 4–5 of your highest-performing Shorts back-to-back with a quick title card showing views/retention for each.

---

## Tactic — bundle this gig with your own pipeline

Use the [`shorts/`](../shorts/README.md) pipeline in this repo to fulfill
Gig 2 orders **at near-zero marginal cost**. Workflow:

```bash
# Client sends you the topic / script
python3 shorts/pipeline.py --topic "their topic" --voice en-US-AndrewNeural

# Open shorts/output/$(date +%F)/<slug>/short.mp4
# Tweak script.md, swap voice if needed, re-render
# Open in CapCut for any final client-specific tweaks
# Export and deliver
```

This turns a 4-hour edit into a 30-minute edit — meaning you can take
3-4x as many orders before hitting capacity.
