# Step-by-Step: From Zero to First Earning Reel

A complete beginner walkthrough. **Total time: ~3 hours over 2 days**, then 30–45 min/day.

> Do these in order. Skip nothing on the first pass.

---

## DAY 1 — Setup (about 2 hours total)

### Part A — Computer setup (15 min)

#### Step 1. Install Python (skip if you already have it)

- Open <https://www.python.org/downloads/>
- Click the big yellow **Download Python 3.x** button.
- Run the installer.
  - **Windows**: tick the box "Add Python to PATH" before clicking Install Now.
  - **Mac**: just click through.
- Test it: open Terminal (Mac) or Command Prompt (Windows) and type:
  ```
  python3 --version
  ```
  You should see something like `Python 3.12.x`.

#### Step 2. Download the toolkit

You have two options — pick one:

**Option A (easy):** Go to <https://github.com/xboom96/facebook-finance-toolkit> → click the green **Code** button → **Download ZIP**. Unzip it on your Desktop.

**Option B (uses git):** In a terminal:
```bash
cd ~/Desktop
git clone https://github.com/xboom96/facebook-finance-toolkit.git
cd facebook-finance-toolkit
```

#### Step 3. Install the dashboard dependency

In a terminal, inside the `facebook-finance-toolkit` folder:
```bash
pip install -r dashboard/requirements.txt
```

If you see permission errors, try `pip install --user -r dashboard/requirements.txt`.

#### Step 4. Test that everything works (no Facebook login yet)

```bash
python3 scraper/run.py --limit 5 --skip-reddit
```
You should see "Wrote 38 items" or similar. Open the file in `scraper/output/trending-YYYY-MM-DD.md` — that's your first batch of Reel ideas.

```bash
python3 dashboard/app.py --demo
```
Open <http://127.0.0.1:5000> in your browser. You should see a dark dashboard with fake numbers. **Press Ctrl+C in the terminal to stop it.**

If both worked, your computer is ready. Move on.

---

### Part B — Create the new Facebook page (30 min)

#### Step 5. Pick a page name

From `STRATEGY.md` section 1, pick **one**:
- MoneyHabits Daily
- The Wealth Lab
- Frugal & Free
- Cashflow Tips
- Smart Money Daily
- The 1% Saver
- Wallet Wins

Or invent your own — must include a money/finance word.

#### Step 6. Create the page

1. Go to <https://www.facebook.com/pages/create>
2. **Page name**: your pick from above.
3. **Category**: type "Personal Blog" → pick it. (You can also pick "Education" or "Finance & Investment.")
4. **Bio**: paste this and edit:
   ```
   Daily money tips to save more, earn more, and retire earlier.
   New video every day at 6 PM EST.
   Not financial advice — educational only.
   ```
5. Click **Create Page**.

#### Step 7. Add profile + cover photos

- **Profile photo**: open <https://www.canva.com/> → search "Facebook profile" → use a green/dark background with a $ symbol or coin icon. Download, upload to your page.
- **Cover photo**: in Canva, search "Facebook cover" → simple text "Daily Money Tips · New Video at 6 PM EST." Download, upload.

#### Step 8. Page settings — make it monetization-ready

1. On your page, click **Settings**.
2. **Page Info**: confirm your category is set. Add a website link if you have one.
3. **Monetization**: check **Eligibility**. You won't be eligible yet (need 5,000 followers + 60,000 watch minutes in last 60 days), but bookmark this page — you'll check back weekly.

---

### Part C — Create the content tools accounts (45 min)

#### Step 9. ChatGPT / Claude (free)

You probably already have one of these. If not:
- ChatGPT: <https://chat.openai.com/> → sign up free.
- Claude: <https://claude.ai/> → sign up free.

#### Step 10. ElevenLabs (AI voice — free tier)

1. Go to <https://elevenlabs.io/> → **Sign Up**.
2. Free tier gives you 10,000 chars/month — enough for ~10 Reels.
3. After login, click **Voice Library** → pick voice **"Brian"** (English-US, male, calm) or **"Rachel"** (English-US, female, warm) → click **Add to my voices**.

#### Step 11. CapCut (video editor — free)

1. Go to <https://www.capcut.com/> → download for your computer.
2. Install + open it.
3. You can also use the mobile app, but the desktop version is faster for batch editing.

#### Step 12. Pexels (free B-roll)

No signup needed. Just go to <https://www.pexels.com/videos/> when you need stock footage. Search e.g. "money", "calculator", "savings", "stocks".

You're done with setup. Take a break.

---

## DAY 2 — Make your first 3 Reels (about 90 min)

### Part D — Get today's trending topics (5 min)

#### Step 13. Run the scraper

In a terminal, inside the toolkit folder:
```bash
python3 scraper/run.py --limit 10 --skip-reddit
```
Open `scraper/output/trending-YYYY-MM-DD.md` (today's date). Skim the **Hook idea** column.

#### Step 14. Pick 3 hooks

From the scraper output AND from `STRATEGY.md` section 5 (the 30-day calendar), pick **3** topics:
- 1 from pillar **Save Money**
- 1 from pillar **Earn More / Side Hustles**
- 1 from pillar **Mistakes / Warnings**

Write them in a notes file. Example:
```
Reel 1 (Save):     "5 subscriptions to cancel today (save $1,200/year)"
Reel 2 (Earn):     "5 weekend gigs that pay $500+"
Reel 3 (Mistake):  "3 money mistakes that keep you poor"
```

---

### Part E — Generate scripts (15 min)

#### Step 15. Get the prompt template

Open `docs/prompts.md` in the toolkit → copy the **Reel script prompt** (it's the first one).

#### Step 16. Generate 3 scripts

For each of your 3 topics:
1. Open ChatGPT/Claude → paste the prompt.
2. Replace `{TOPIC}` with your Reel topic.
3. Send → you'll get a HOOK + ON-SCREEN TEXT + VOICEOVER + CTA + B-ROLL suggestions + hashtags.
4. Copy the output into a notes file. Save as `reel-1.txt`, `reel-2.txt`, `reel-3.txt`.

---

### Part F — Generate voice (10 min)

#### Step 17. Create voiceover MP3s

1. Go to <https://elevenlabs.io/speech-synthesis>.
2. Select voice: **Brian** or **Rachel**.
3. Settings: **Stability 0.55**, **Similarity 0.75**, **Style 0.10**, **Speaker boost ON**.
4. Paste the **VOICEOVER** section from `reel-1.txt`.
5. Click **Generate** → **Download MP3**.
6. Repeat for reel-2 and reel-3.

You now have 3 voice files: `reel-1.mp3`, `reel-2.mp3`, `reel-3.mp3`.

---

### Part G — Download B-roll (15 min)

#### Step 18. Get stock footage

For each Reel, the script gave you 3 B-roll search terms.

For each term:
1. Go to <https://www.pexels.com/videos/>.
2. Search the term.
3. Pick a vertical or square video, 5–10 seconds, ideally with people/money/numbers.
4. Click **Free Download** → choose **Original** or **HD**.

Aim for 3–5 short clips per Reel.

---

### Part H — Edit the Reel in CapCut (15 min per Reel)

#### Step 19. Edit Reel #1

1. Open CapCut → **New Project**.
2. Click the aspect ratio button (top right) → **9:16 (TikTok)**. This is the Reel format.
3. Import the voice MP3 + all B-roll clips.
4. Drag the voice MP3 to the timeline (bottom track).
5. Drag B-roll clips above the voice, trimming each to match a section of the voiceover.
6. **Auto captions**: top menu → **Text → Auto-Captions → English → Start**. CapCut will transcribe the voice.
7. Style the captions:
   - Font: **Montserrat Bold** or **Bebas Neue**.
   - Size: large (60–80 pt).
   - Color: white, with black drop shadow or outline.
   - Position: centered, in the lower-middle third.
8. Add the ON-SCREEN HOOK TEXT at second 0–3, big and bold.
9. Add 1 zoom or pan keyframe to each B-roll (subtle motion = better retention).
10. Add royalty-free background music: **Audio → Music → Trending** → pick something at ~-18 dB volume.
11. **Export**: top right → **Export** → 1080p, 30fps → Save.

Repeat for Reel #2 and #3.

---

### Part I — Schedule your first week of posts (10 min)

#### Step 20. Upload to Meta Business Suite

1. Go to <https://business.facebook.com/>.
2. Switch to your new page (top left).
3. Left sidebar → **Content** → **Create post** → choose **Reel**.
4. Upload `reel-1.mp4`.
5. **Caption**: paste the caption your LLM generated (also generate one if you didn't).
6. **Schedule**: pick tomorrow at **6:00 PM EST** (Facebook lets you schedule).
7. Click **Schedule**.

Repeat for Reel #2 (day after) and Reel #3 (day after that).

---

## DAY 3 ONWARDS — Daily rhythm (30–45 min/day)

Every day:

1. **Morning** — Run the scraper:
   ```bash
   python3 scraper/run.py --limit 10 --skip-reddit
   ```
   Pick tomorrow's topic from the report or from the 30-day calendar in STRATEGY.md.

2. **Write 1 script** with ChatGPT/Claude using `docs/prompts.md`.

3. **Generate voice** in ElevenLabs.

4. **Download 3 B-rolls** from Pexels.

5. **Edit in CapCut** (~15 min).

6. **Schedule** for 6 PM EST the next day.

7. **Engage** — open your page during/after a post goes live and reply to every comment in the first hour. Facebook's algorithm rewards fast engagement.

---

## WEEKLY — Track what works (15 min)

Once you have a **Page Access Token** (see step 21 below), run the dashboard each Sunday:

```bash
python3 dashboard/app.py
```

Open <http://127.0.0.1:5000/setup>, paste your Page ID + token, set RPM to 5 (start), then look at:

- **Top posts by engagement rate** — which content style is winning?
- **Top posts by estimated revenue** — which posts had the most impressions?
- **Avg watch time** — anything under 15 sec is a bad hook. Anything over 30 sec is a winner — make more like that.

Double down on whatever wins.

---

### Step 21 (do this in week 2) — Connect the dashboard to your real page

Open `SETUP_META_TOKEN.md` and follow the steps. Summary:

1. Create a Meta Developer app at <https://developers.facebook.com/apps/>.
2. Use Graph API Explorer to generate a token with `pages_show_list`, `pages_read_engagement`, `read_insights`.
3. Convert to long-lived user token, then page token (commands are in the doc).
4. Paste **Page ID** + **Page Access Token** into the dashboard `/setup` page.

You only do this once.

---

## When you'll hit each milestone (realistic timeline)

| Day | Milestone |
|---|---|
| Day 1 | Page created, tools installed |
| Day 2 | First 3 Reels scheduled |
| Day 7 | 7 Reels posted, you have your first follower data |
| Day 14 | 200–800 followers if posts are consistent + watchable |
| Day 30 | 1,500–4,000 followers + you've identified your best-performing pillar |
| Day 60 | 5,000+ followers, eligible for monetization |
| Day 90 | First $$ from in-stream ads if approved |

These are *realistic* numbers for a faceless finance niche starting from zero. They depend mostly on:
1. **Consistency** — 1 Reel/day, every day.
2. **Hook quality** — first 3 seconds. Use the 10 templates in `STRATEGY.md`.
3. **Retention** — Reels under 25 sec watch time die. Keep value dense.
4. **English-speaking audience** — your captions + voice + audience country all matter.

---

## What to do if something doesn't work

| Problem | Fix |
|---|---|
| Scraper says "0 items" | Try `python3 scraper/run.py --skip-reddit` (Reddit blocks some IPs). Google News alone gives 24+. |
| Dashboard `pip install` fails | Try `python3 -m pip install --user flask` |
| Dashboard "Could not reach Meta Graph API" | Token expired or wrong page ID. Regenerate via `SETUP_META_TOKEN.md`. |
| ElevenLabs out of characters | Wait until next month (free tier resets) or upgrade to Starter ($5/mo). |
| CapCut crashes on export | Export at 720p first, see if 1080p worked. Update to latest version. |
| No views on first 5 Reels | Normal. New pages get throttled. Keep posting daily; pickup usually starts day 7–14. |
| Posts get policy strikes | Check Meta Business Suite → Monetization → Policy Issues. Avoid "guaranteed money" / "passive income" language. Stay educational. |

---

That's it. The whole flow is: **scrape → script → voice → B-roll → edit → schedule → engage → measure → repeat.**

If you get stuck at any step, message me with the step number and a screenshot of the error.
