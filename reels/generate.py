#!/usr/bin/env python3
"""Viral Facebook Reels script generator.

Turn a single idea into a ready-to-shoot Reel package. Give it a niche, a
topic, a publish date and a target duration, and it returns everything you
need to film a faceless short:

- A scroll-stopping **hook** (spoken + on-screen) with the reason it works.
- A full **voiceover script** structured for retention
  (Hook -> Promise -> Value beats -> Proof -> CTA -> Loop).
- **Visual ideas** / B-roll search terms for every beat.
- A **title**, **caption** and **description** tuned for the feed.
- A set of **tags** (hashtags) mixing niche, topic and reach keywords.
- A music + pacing suggestion and a viral checklist.

It is **niche-agnostic** — finance, fitness, travel, cooking, tech, anything.
Generation is fully **offline and deterministic** (seedable), so the same
inputs always produce the same package. No API key required.

CLI:

    python3 reels/generate.py --niche "personal finance" \\
        --topic "3 money mistakes that keep you broke" \\
        --date 2026-05-29 --duration 60

    # JSON output (for piping into other tools)
    python3 reels/generate.py --niche fitness --topic "morning routine" --json

    # Reproducible output
    python3 reels/generate.py --topic "save $5k this year" --seed 42
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import random
import re
import sys
from dataclasses import dataclass, field

# Spoken words per second for an energetic faceless Reel voiceover.
WORDS_PER_SECOND = 2.6

# Generic stop words stripped when turning a topic into keywords/hashtags.
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "to", "of", "in", "on", "for",
    "with", "your", "you", "this", "that", "these", "those", "is", "are",
    "be", "at", "by", "it", "as", "from", "how", "why", "what", "when",
    "do", "does", "my", "i", "we", "they", "will", "can", "should", "if",
}

# ---------------------------------------------------------------------------
# Template banks (niche-agnostic). {topic} and {niche} are filled in later.
# ---------------------------------------------------------------------------

HOOK_TEMPLATES: list[tuple[str, str, str]] = [
    (
        "Stop scrolling — you're doing {topic_low} completely wrong.",
        "YOU'RE DOING IT WRONG",
        "A direct callout + a 'you' accusation forces a pattern interrupt in the first second.",
    ),
    (
        "Nobody in {niche_low} talks about this, but it changes everything about {topic_low}.",
        "NOBODY TALKS ABOUT THIS",
        "Curiosity gap + insider framing makes the viewer feel they'll miss out if they scroll.",
    ),
    (
        "If I had to restart {niche_low} from zero, this is exactly how I'd handle {topic_low}.",
        "IF I STARTED OVER",
        "The 'start from zero' frame promises a shortcut and triggers FOMO.",
    ),
    (
        "Here's the truth about {topic_low} that took me years to figure out.",
        "THE TRUTH ABOUT THIS",
        "A 'hard-won truth' promise sets up authority and a payoff worth staying for.",
    ),
    (
        "Most people quit {niche_low} because of one mistake with {topic_low}. Here it is.",
        "THE #1 MISTAKE",
        "Loss aversion: naming a mistake makes viewers stay to check if they're guilty of it.",
    ),
    (
        "I tested {topic_low} so you don't have to — and the result shocked me.",
        "I TESTED IT SO YOU DON'T",
        "First-person experiment + an unresolved 'shocking' result keeps people watching.",
    ),
    (
        "Save this before it's gone: the fastest way to win at {topic_low}.",
        "SAVE THIS NOW",
        "An explicit save command boosts the share/save signal the algorithm rewards.",
    ),
]

PROMISE_TEMPLATES = [
    "In the next {duration}s I'll break down {topic_low} into steps you can use today — no fluff.",
    "By the end of this you'll know exactly how to handle {topic_low}, even if you're starting from scratch.",
    "Stick around — point number {last_point} is the one almost everyone gets wrong.",
    "I'll keep it simple: {count} things that actually move the needle on {topic_low}.",
]

# Value-beat angles. Each is (spoken_lead, on_screen_caption, visual_term).
# {n} is the spoken position word, filled at build time so audio matches text.
VALUE_ANGLES: list[tuple[str, str, str]] = [
    (
        "number {n}: stop chasing perfect and start with the smallest version you can do today. "
        "Momentum beats motivation every single time.",
        "START SMALL TODAY",
        "hands writing a short checklist close-up",
    ),
    (
        "number {n}: the mistake almost everyone makes is overcomplicating it. "
        "Cut your plan in half — the simple version is the one you'll actually stick to.",
        "KEEP IT STUPID SIMPLE",
        "person decluttering a messy desk into a clean one",
    ),
    (
        "number {n}: track it. What gets measured gets better. "
        "A free note on your phone is enough to spot the pattern holding you back.",
        "TRACK IT FOR 7 DAYS",
        "phone screen showing a simple tracking app or notes",
    ),
    (
        "number {n}: copy what already works. Find one person two steps ahead of you and "
        "model their system instead of reinventing the wheel.",
        "STEAL WHAT WORKS",
        "split-screen comparison of before and after",
    ),
    (
        "number {n}: protect your first hour. The way you start sets the tone for everything that follows, "
        "so guard it from distractions.",
        "OWN YOUR FIRST HOUR",
        "sunrise time-lapse over a calm workspace",
    ),
    (
        "number {n}: ignore the noise. Most advice online is built for clicks, not results. "
        "Pick one method and give it 30 days before you judge it.",
        "IGNORE THE NOISE",
        "scrolling social feed then phone placed face-down",
    ),
    (
        "number {n}: build the habit, not the goal. Goals get you started, "
        "but a tiny daily system is what carries you across the finish line.",
        "SYSTEMS BEAT GOALS",
        "calendar with a growing streak of checkmarks",
    ),
]

PROOF_TEMPLATES = [
    "Quick proof: when I applied this to {topic_low}, the difference showed up within a week — small change, big result.",
    "Real example: someone I coached used exactly this on {topic_low} and went from stuck to unstoppable in a month.",
    "And before you say it won't work for you — this works in any situation, because it fixes the root cause, not the symptom.",
]

CTA_TEMPLATES = [
    "Follow for more {niche_low} that actually works, and comment the word GO if you want the full guide.",
    "Hit follow so you don't lose this, and share it with someone who needs to hear it.",
    "Save this for later and follow for a new {niche_low} tip every single day.",
]

LOOP_TEMPLATES = [
    "Because once you fix {topic_low}, everything else gets easier — so watch it again and start with step one.",
    "And that's why most people get {topic_low} wrong... but now you won't.",
    "Do this and you'll never look at {topic_low} the same way again.",
]

CAPTION_OPENERS = [
    "The {topic_low} mistake that's costing you more than you think 👇",
    "Save this if you've ever struggled with {topic_low}.",
    "Nobody told you this about {topic_low} — so I will.",
    "Steal my {count}-step approach to {topic_low}.",
]

CAPTION_CLOSERS = [
    "Which one are you trying first? Drop it in the comments 👇",
    "What's the hardest part of {topic_low} for you?",
    "Tag someone who needs this today.",
    "Did this help? Let me know what to break down next.",
]

TITLE_TEMPLATES = [
    "{count} {niche_title} Tips for {topic_title} (That Actually Work)",
    "The Truth About {topic_title} Nobody Tells You",
    "How to Master {topic_title} in {duration} Seconds",
    "{topic_title}: Stop Making This Mistake",
    "Do This for {topic_title} Before {year} Ends",
]

MUSIC_SUGGESTIONS = [
    "Upbeat lo-fi / trending audio at -18 dB under the voiceover (let the VO lead).",
    "Punchy trending pop loop; cut the beat drop to land on point number 1.",
    "Calm cinematic build that rises into the CTA for an emotional payoff.",
    "Trending 'storytime' background audio — keep it low so captions stay readable.",
]

# Reach hashtags that aren't tied to a niche.
GENERIC_TAGS = ["reels", "reelsvideo", "viral", "fyp", "explore", "trending", "reelsviral"]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Hook:
    spoken: str
    on_screen: str
    why_it_works: str


@dataclass
class Segment:
    role: str  # hook | promise | value | proof | cta | loop
    label: str
    seconds: int
    voiceover: str
    on_screen: str
    visual: str


@dataclass
class ReelPackage:
    niche: str
    topic: str
    date: str
    duration_seconds: int
    best_time_to_post: str
    title: str
    hook: Hook
    segments: list[Segment]
    caption: str
    description: str
    tags: list[str]
    visual_ideas: list[str]
    music: str
    viral_checklist: list[str] = field(default_factory=list)

    def voiceover_script(self) -> str:
        """Full spoken script, segment by segment."""
        return "\n\n".join(s.voiceover.strip() for s in self.segments if s.voiceover.strip())

    def word_count(self) -> int:
        return len(self.voiceover_script().split())

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["voiceover_script"] = self.voiceover_script()
        data["word_count"] = self.word_count()
        return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NUMBER_WORDS = ["one", "two", "three", "four", "five", "six", "seven"]


def keywords(text: str, *, limit: int = 6) -> list[str]:
    """Extract meaningful keywords from free text."""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9']+", text.lower())
    out: list[str] = []
    for w in words:
        if w in STOP_WORDS or len(w) < 3:
            continue
        if w not in out:
            out.append(w)
        if len(out) >= limit:
            break
    return out


def hashtagify(text: str) -> str:
    return "#" + re.sub(r"[^a-z0-9]", "", text.lower())


def points_for_duration(duration: int) -> int:
    """How many value beats fit in the target duration."""
    if duration <= 20:
        return 1
    if duration <= 35:
        return 2
    if duration <= 55:
        return 3
    if duration <= 80:
        return 4
    if duration <= 110:
        return 5
    return 6


def best_time_to_post(date_iso: str) -> str:
    """Heuristic best posting window for Facebook Reels by weekday."""
    try:
        d = dt.date.fromisoformat(date_iso)
    except ValueError:
        return "6:00–9:00 PM local time"
    weekday = d.weekday()  # Mon=0
    windows = {
        0: "6:00–9:00 AM (Monday commute scroll)",
        1: "11:00 AM–1:00 PM (Tuesday lunch peak)",
        2: "11:00 AM–1:00 PM (midweek lunch peak)",
        3: "12:00–3:00 PM (Thursday afternoon)",
        4: "1:00–4:00 PM (Friday wind-down)",
        5: "9:00–11:00 AM (Saturday morning)",
        6: "5:00–8:00 PM (Sunday evening reset)",
    }
    return windows.get(weekday, "6:00–9:00 PM local time")


def words_to_seconds(text: str) -> int:
    return max(1, round(len(text.split()) / WORDS_PER_SECOND))


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate(
    niche: str,
    topic: str,
    *,
    date: str | None = None,
    duration: int = 60,
    seed: int | None = None,
) -> ReelPackage:
    """Build a complete, ready-to-shoot Reel package from the inputs."""
    niche = (niche or "this niche").strip()
    topic = (topic or "this topic").strip()
    duration = max(10, int(duration))
    date_iso = (date or dt.date.today().isoformat()).strip()

    # Deterministic per (inputs, seed) so the same call reproduces output.
    if seed is None:
        seed = abs(hash((niche.lower(), topic.lower(), date_iso, duration))) % (2**31)
    rng = random.Random(seed)

    topic_low = topic.rstrip(".!?").lower()
    niche_low = niche.lower()
    topic_title = topic.rstrip(".!?").title()
    niche_title = niche.title()
    try:
        year = dt.date.fromisoformat(date_iso).year
    except ValueError:
        year = dt.date.today().year

    count = points_for_duration(duration)
    fmt = dict(
        topic_low=topic_low,
        niche_low=niche_low,
        topic_title=topic_title,
        niche_title=niche_title,
        duration=duration,
        count=count,
        last_point=NUMBER_WORDS[count - 1],
        year=year,
    )

    # --- Hook -------------------------------------------------------------
    hook_spoken, hook_screen, hook_why = rng.choice(HOOK_TEMPLATES)
    hook = Hook(
        spoken=hook_spoken.format(**fmt),
        on_screen=hook_screen,
        why_it_works=hook_why.format(**fmt),
    )

    segments: list[Segment] = [
        Segment("hook", "Hook (0–3s)", 3, hook.spoken, hook.on_screen,
                "extreme close-up of face/subject or a bold text card; fast zoom-in"),
    ]

    # --- Promise ----------------------------------------------------------
    promise = rng.choice(PROMISE_TEMPLATES).format(**fmt)
    segments.append(
        Segment("promise", "Promise / stakes (3–8s)", words_to_seconds(promise),
                promise, "HERE'S THE PLAN",
                "quick montage preview of the payoff; rapid cuts to set pace")
    )

    # --- Value beats ------------------------------------------------------
    angles = rng.sample(VALUE_ANGLES, k=min(count, len(VALUE_ANGLES)))
    for i, (spoken, caption, visual) in enumerate(angles):
        n = NUMBER_WORDS[i]
        vo = spoken.format(n=n, **fmt)
        segments.append(
            Segment("value", f"Point {i + 1}", words_to_seconds(vo), vo,
                    f"{i + 1}. {caption}", visual)
        )

    # --- Proof (only if there's room) ------------------------------------
    if duration >= 45:
        proof = rng.choice(PROOF_TEMPLATES).format(**fmt)
        segments.append(
            Segment("proof", "Proof / example", words_to_seconds(proof), proof,
                    "RECEIPTS", "screen-recording or before/after that backs up the claim")
        )

    # --- CTA --------------------------------------------------------------
    cta = rng.choice(CTA_TEMPLATES).format(**fmt)
    segments.append(
        Segment("cta", "Call to action", words_to_seconds(cta), cta,
                "FOLLOW + COMMENT 'GO'", "point-to-follow-button gesture; arrow graphic")
    )

    # --- Loop -------------------------------------------------------------
    loop = rng.choice(LOOP_TEMPLATES).format(**fmt)
    segments.append(
        Segment("loop", "Loop back (last 3s)", 3, loop, hook.on_screen,
                "reuse the opening shot so the end blends into the start (seamless loop)")
    )

    # --- Title ------------------------------------------------------------
    title = rng.choice(TITLE_TEMPLATES).format(**fmt)
    if len(title) > 90:
        title = title[:87] + "..."

    # --- Caption ----------------------------------------------------------
    opener = rng.choice(CAPTION_OPENERS).format(**fmt)
    closer = rng.choice(CAPTION_CLOSERS).format(**fmt)
    tags = build_tags(niche, topic, rng)
    caption = (
        f"{opener}\n\n"
        f"Here's the {count}-step breakdown 👇\n"
        f"{chr(10).join('• ' + s.on_screen.split('. ', 1)[-1].title() for s in segments if s.role == 'value')}\n\n"
        f"{closer}\n\n"
        f"For education/entertainment only.\n\n"
        f"{' '.join('#' + t for t in tags[:8])}"
    )

    # --- Description ------------------------------------------------------
    description = (
        f"{topic_title} — {niche_title} Reel.\n"
        f"In this short we cover {count} practical takes on {topic_low}, from the hook to a clear next step. "
        f"Follow for daily {niche_low} content. Save and share if it helped.\n\n"
        f"{' '.join('#' + t for t in tags[:10])}"
    )

    # --- Visual ideas (deduped, ordered) ---------------------------------
    visual_ideas: list[str] = []
    for s in segments:
        if s.visual and s.visual not in visual_ideas:
            visual_ideas.append(s.visual)
    for kw in keywords(f"{topic} {niche}", limit=4):
        term = f"stock B-roll: {kw} (search Pexels/Pixabay)"
        if term not in visual_ideas:
            visual_ideas.append(term)

    checklist = [
        "Hook lands in the first 1–2 seconds (no slow intro).",
        "On-screen captions on every line — most people watch on mute.",
        "9:16 vertical, 1080p, faces/subject framed in the safe zone.",
        "One pattern interrupt (zoom, cut, sound) every 3–5 seconds.",
        "End seamlessly loops back to the opening shot to boost watch time.",
        "Single clear CTA — don't ask for follow AND share AND save at once.",
    ]

    return ReelPackage(
        niche=niche,
        topic=topic,
        date=date_iso,
        duration_seconds=duration,
        best_time_to_post=best_time_to_post(date_iso),
        title=title,
        hook=hook,
        segments=segments,
        caption=caption,
        description=description,
        tags=tags,
        visual_ideas=visual_ideas,
        music=rng.choice(MUSIC_SUGGESTIONS),
        viral_checklist=checklist,
    )


def build_tags(niche: str, topic: str, rng: random.Random) -> list[str]:
    """Mix niche + topic keywords with high-reach generic tags."""
    tags: list[str] = []
    niche_kw = keywords(niche, limit=3)
    topic_kw = keywords(topic, limit=5)
    # niche as a single compact tag, e.g. "personal finance" -> personalfinance
    compact_niche = re.sub(r"[^a-z0-9]", "", niche.lower())
    if compact_niche:
        tags.append(compact_niche)
    for kw in niche_kw + topic_kw:
        if kw not in tags:
            tags.append(kw)
    pool = GENERIC_TAGS[:]
    rng.shuffle(pool)
    for t in pool:
        if t not in tags:
            tags.append(t)
        if len(tags) >= 15:
            break
    return tags[:15]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_markdown(pkg: ReelPackage) -> str:
    lines: list[str] = [
        f"# Reel package — {pkg.topic}",
        "",
        f"- **Niche:** {pkg.niche}",
        f"- **Topic:** {pkg.topic}",
        f"- **Date:** {pkg.date}",
        f"- **Duration:** {pkg.duration_seconds}s  ·  ~{pkg.word_count()} words of voiceover",
        f"- **Best time to post:** {pkg.best_time_to_post}",
        "",
        "## Title",
        pkg.title,
        "",
        "## Hook (first 3 seconds)",
        f"- **Spoken:** {pkg.hook.spoken}",
        f"- **On-screen:** {pkg.hook.on_screen}",
        f"- **Why it works:** {pkg.hook.why_it_works}",
        "",
        "## Voiceover script",
    ]
    for s in pkg.segments:
        lines.append(f"\n**{s.label}** _(~{s.seconds}s)_")
        lines.append(f"- 🎙️ {s.voiceover}")
        lines.append(f"- 🖥️ On-screen: `{s.on_screen}`")
        lines.append(f"- 🎬 Visual: {s.visual}")

    lines += [
        "",
        "## Visual ideas / B-roll",
    ]
    lines += [f"- {v}" for v in pkg.visual_ideas]
    lines += [
        "",
        f"## Music & pacing",
        f"- {pkg.music}",
        "",
        "## Caption",
        "```",
        pkg.caption,
        "```",
        "",
        "## Description",
        "```",
        pkg.description,
        "```",
        "",
        "## Tags",
        " ".join("#" + t for t in pkg.tags),
        "",
        "## Viral checklist",
    ]
    lines += [f"- [ ] {c}" for c in pkg.viral_checklist]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--niche", default="personal finance",
                        help="content niche, e.g. 'fitness', 'travel', 'personal finance'")
    parser.add_argument("--topic", required=True, help="the specific Reel topic / idea")
    parser.add_argument("--date", default=None, help="publish date YYYY-MM-DD (default: today)")
    parser.add_argument("--duration", type=int, default=60, help="target length in seconds")
    parser.add_argument("--seed", type=int, default=None, help="seed for reproducible output")
    parser.add_argument("--json", action="store_true", help="output JSON instead of Markdown")
    args = parser.parse_args(argv)

    pkg = generate(
        args.niche,
        args.topic,
        date=args.date,
        duration=args.duration,
        seed=args.seed,
    )

    if args.json:
        print(json.dumps(pkg.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(render_markdown(pkg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
