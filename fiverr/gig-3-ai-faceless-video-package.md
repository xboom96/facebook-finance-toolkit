# Gig 3 — Done-for-You AI Faceless Video Package (premium)

> The premium tier. You take **only the topic** from the buyer and deliver a fully scripted, voiced, edited video. Highest margin on Fiverr because the buyer is paying for the *system*, not just edit hours. Fulfilled by the `shorts/` pipeline in this repo.

---

## Category / Sub-category

- Category: **Video & Animation**
- Sub-category: **Spokespersons & Testimonials** → **Faceless Videos**
  - (If "Faceless Videos" is unavailable in your region, use Video Editing → YouTube Videos.)

## Gig metadata

- Tags:
  1. `faceless youtube video`
  2. `ai voiceover video`
  3. `done for you youtube`
  4. `youtube automation video`
  5. `viral faceless content`

---

## Title (70–80 chars)

```
I will create your faceless YouTube video with script voice and edit
```

Alternatives:

- `I will produce a done for you faceless YouTube short or long video`
- `I will be your AI faceless YouTube video producer end to end`

---

## Description

> **Hi, I'm *Anusha* — a faceless video producer with an HND in Post-Production Technology and a proprietary AI-assisted pipeline that delivers a complete YouTube-ready video in 24–48 hours.**
>
> Most "faceless video" gigs on Fiverr only do the edit. You still have to write the script, generate the voice, find the B-roll, and design the thumbnail. **This gig does all of it.** You give me a topic (or a niche) and you get back a finished MP4 ready to upload.
>
> ### What you get
>
> Every video I deliver includes:
>
> 1. **A retention-engineered script** — Hook → Promise → 3 Tips → Example → CTA → Loop, written in your brand voice. (See my showreel for examples.)
> 2. **A natural AI voiceover** — your choice of male/female, US/UK/AU accent, calm or energetic delivery. Uses Edge TTS (free) or ElevenLabs (paid, +$10 per video for premium voices).
> 3. **A 9:16 vertical edit (for Shorts/Reels/TikTok)** OR **a 16:9 long-form edit (for YouTube)** — your choice.
> 4. **Animated word-level captions** burned in.
> 5. **B-roll matched to each script beat** (Pexels/Storyblocks licensed).
> 6. **A custom thumbnail** designed in Canva.
> 7. **Upload metadata** — title, description, hashtags, tags — copy-pasted into a doc.
>
> ### Niches I specialize in (because the script templates are pre-built)
>
> - Personal finance / investing / side hustles
> - Motivation / self-improvement / discipline
> - Tech / AI / productivity
> - History / mystery / unsolved stories
> - "Top X" listicle channels
>
> If your niche isn't listed, message me first — I'll quote you a script-research add-on so the output still feels native to your audience.
>
> ### Working with me
>
> - You provide just the **topic** (or a list of topics for a multi-video order)
> - I deliver **draft script for approval first**, then voice + edit
> - **Two free revisions** at every stage (script, voice, final edit)
> - **48-hour standard delivery**; 24h available as an extra
> - **Bulk discount** kicks in at 5+ videos

---

## Packages

|  | **BASIC — Single Short** | **STANDARD — 3-Video Bundle** | **PREMIUM — Channel Starter (10 videos)** |
|---|---|---|---|
| **Price** | $60 | $150 | $450 |
| **Per-video** | $60 | $50 | $45 |
| **Length** | 60 sec | 60–90 sec each | 60–90 sec each |
| **Delivery** | 3 days | 5 days | 10 days |
| **Revisions** | 2 | 2 per video | 2 per video |
| **Script writing** | ✓ | ✓ | ✓ |
| **AI voiceover (Edge TTS)** | ✓ | ✓ | ✓ |
| **9:16 vertical edit** | ✓ | ✓ | ✓ |
| **Animated captions** | ✓ | ✓ | ✓ |
| **B-roll sourcing** | ✓ | ✓ | ✓ |
| **Custom thumbnail** | ✓ | ✓ (each) | ✓ (each) |
| **Upload metadata pack** | ✓ | ✓ | ✓ |
| **ElevenLabs premium voice** | — | — | ✓ (1 voice, all 10) |
| **Channel banner + intro** | — | — | ✓ |

### Gig Extras

- **24-hour express delivery**: +$30 (BASIC), +$60 (STANDARD), +$150 (PREMIUM)
- **ElevenLabs premium voice (per video)**: +$10
- **Long-form 16:9 (5+ minutes) instead of Short**: +$50 per video
- **Source files (Premiere/CapCut)**: +$25 per video
- **Niche research (1-page audience + competitor brief)**: +$40

---

## FAQ

**Q: How is this different from your other gigs?**
A: My other gigs are pure editing — you provide the script and voiceover. This gig is **fully done-for-you**: you only provide the topic. I write, voice, edit, and design the thumbnail.

**Q: Is the AI voice good enough to monetize?**
A: Yes. Edge TTS (free, Microsoft Neural) and ElevenLabs (paid) both pass YouTube's "valuable original content" requirements when paired with original scripts and edits. I never reuse scripts between clients.

**Q: Can I keep using my own brand voice across all 10 videos?**
A: Absolutely — the PREMIUM package locks in one voice across the bundle. You can also send me 2–3 reference videos and I'll match the tone.

**Q: What if I want a niche you don't list?**
A: Message me first. I'll either quote a small script-research add-on ($40) or recommend a specialist if it's outside my expertise.

**Q: Will my channel get monetized?**
A: I produce content that meets YouTube's monetization standards (original content, licensed assets, no policy violations). Channel-level approval still depends on your audience size and watch hours — I can't guarantee that.

**Q: Do you guarantee views?**
A: No — anyone who guarantees views is lying. I do guarantee a video that follows every retention best-practice I've used to hit 60%+ retention on my own channels and client work.

---

## Gallery

- **Image 1** (hero): A 9:16 phone mockup of your best AI-produced Short with a metric overlay: `1.4M views, 71% retention, 100% AI-produced`.
- **Image 2** (the system): A 4-step infographic — `Topic → AI Script → AI Voice → Final Edit`.
- **Image 3** (packages): The BASIC/STANDARD/PREMIUM comparison.
- **Video** (60s showreel): 3 fully AI-produced Shorts from different niches back-to-back. End with a card: "Order BASIC for a single video. Order PREMIUM for a 10-video channel starter."

---

## Internal fulfillment cheat-sheet (your eyes only)

```bash
# 1. Receive order, confirm topic with client in chat
# 2. Pick voice
python3 shorts/tts.py --list-voices | grep en-US

# 3. Generate
python3 shorts/pipeline.py \
    --topic "<client topic>" \
    --voice en-US-AndrewNeural \
    --mode openai  # if you have an OpenAI key, otherwise offline

# 4. Review shorts/output/$(date +%F)/<slug>/script.md
#    Edit the .md if needed, then re-render that specific topic.

# 5. Open shorts/output/$(date +%F)/<slug>/short.mp4
#    If client wants a different look, open it in CapCut for final tweaks.

# 6. Generate thumbnail in Canva (15 min).

# 7. Open shorts/output/$(date +%F)/<slug>/metadata.json
#    Copy title/description/hashtags into a Google Doc for the client.

# 8. Deliver short.mp4 + thumbnail.png + metadata.txt via Fiverr.
```

**Time per video at your skill level:** ~25 minutes after the first 3
videos. **Margin:** ~$55–$65/video on the BASIC tier. **Throughput:** 6–8
videos/day is sustainable. **Theoretical cap:** $400/day net.
