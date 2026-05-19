# LLM Prompts for Faceless Personal-Finance Reels

Paste these into ChatGPT / Claude. Replace `{TOPIC}` with the daily trending topic from `scraper/run.py`.

---

## 1. Reel script prompt

```
You are a Facebook Reels scriptwriter for a personal-finance page.
Audience: US adults 22–45 who feel financially stuck and want practical tips.
Tone: punchy, confident, no jargon, no get-rich-quick promises.
Format: 60–80 seconds of voiceover, ~150–180 words.

Topic: {TOPIC}

Output exactly this structure:

HOOK (3 seconds, ≤12 words):
[hook line — must create curiosity or pattern interrupt]

ON-SCREEN TEXT FOR HOOK:
[same line, ALL CAPS, ≤8 words]

VOICEOVER (60–75 seconds):
[script body with 3 numbered tips. Each tip 2–3 sentences. Include one concrete dollar figure.]

CTA (5 seconds):
[Follow for daily money tips. Comment "BUDGET" for my free template.]

3 B-ROLL SUGGESTIONS:
1. [search term for Pexels]
2. [search term for Pexels]
3. [search term for Pexels]

3 HASHTAGS:
#[hashtag1] #[hashtag2] #[hashtag3]
```

---

## 2. Carousel prompt (for Sunday posts)

```
Write a 7-slide Facebook carousel on the topic: {TOPIC}.

Slide 1: hook + curiosity gap (≤10 words on screen).
Slides 2–6: one tip per slide (≤25 words each).
Slide 7: CTA — "Save this. Follow for daily money tips."

Each slide should make sense on its own (people swipe out).
No financial advice claims. Educational framing only.
```

---

## 3. Caption / description prompt

```
Write a Facebook Reel caption for the topic: {TOPIC}.

Requirements:
- First line is a hook ≤80 chars.
- Body is 3–5 short lines, scannable.
- End with one open-ended question to drive comments.
- Add a "Not financial advice — for education only" disclaimer.
- 3 hashtags at the end.
- Total length ≤500 chars.
```

---

## 4. ElevenLabs voice settings (recommended)

- **Voice**: "Brian" (en-US, calm authoritative) or "Rachel" (en-US, warm clear).
- **Stability**: 0.55
- **Similarity**: 0.75
- **Style exaggeration**: 0.10 (low — keep it natural)
- **Speaker boost**: ON

---

## 5. CapCut workflow (after generating voice + script)

1. New project → 9:16 vertical.
2. Import voiceover MP3.
3. Generate auto-captions → style: large white text, black drop-shadow, centered bottom-third.
4. Drop B-roll from Pexels matching each section.
5. Add 1 zoom/pan keyframe per clip (subtle motion = higher retention).
6. Royalty-free background music at -18 dB.
7. Export 1080p, 30fps, MP4.
