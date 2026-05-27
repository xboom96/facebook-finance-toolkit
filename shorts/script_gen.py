#!/usr/bin/env python3
"""Generate a 60-80s faceless Reel script from a hook / topic.

Two modes:

* **offline** (default) — deterministic templated script. No API key required.
  Uses the structures defined in ``STRATEGY.md`` (Hook → Promise → 3 tips →
  Example → CTA → Loop). Good enough as a first draft for the Shorts pipeline.

* **openai** — calls the OpenAI API for higher-quality scripts.
  Activated when ``OPENAI_API_KEY`` is set in the environment AND
  ``--mode openai`` is passed to the CLI. Falls back to offline mode
  automatically if the call fails.

Output is a :class:`Script` dataclass that the renderer can consume directly.

CLI:

    python3 shorts/script_gen.py "5 subscriptions to cancel today"
    python3 shorts/script_gen.py --mode openai "Compound interest at $5/day"
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import random
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ScriptSegment:
    """A single block of voiceover with optional on-screen overlay text."""

    role: str  # "hook" | "promise" | "tip" | "example" | "cta" | "loop"
    voiceover: str
    on_screen: str = ""  # short caption that lives on top of the video


@dataclass
class Script:
    topic: str
    segments: list[ScriptSegment]
    hashtags: list[str]
    broll_terms: list[str] = field(default_factory=list)

    @property
    def hook(self) -> str:
        for s in self.segments:
            if s.role == "hook":
                return s.voiceover
        return self.topic

    def full_text(self) -> str:
        return "\n\n".join(s.voiceover.strip() for s in self.segments if s.voiceover.strip())

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "hashtags": self.hashtags,
            "broll_terms": self.broll_terms,
            "segments": [dataclasses.asdict(s) for s in self.segments],
        }


# ---------------------------------------------------------------------------
# Offline mode — template-based script
# ---------------------------------------------------------------------------


HOOK_TEMPLATES = [
    "Here's something most people get wrong about {topic_low}.",
    "If you're stuck financially, this one thing about {topic_low} matters most.",
    "Let me show you the truth about {topic_low} in 60 seconds.",
    "Stop scrolling — this is the {topic_low} tip that actually works.",
    "I wish someone told me this about {topic_low} when I was 20.",
]

ON_SCREEN_HOOK = [
    "WATCH THIS",
    "DO NOT SCROLL",
    "60-SECOND MONEY TIP",
    "THE TRUTH ABOUT MONEY",
    "MOST PEOPLE GET THIS WRONG",
]

PROMISE_TEMPLATES = [
    "By the end of this video you'll know exactly how to fix it.",
    "Here is what the data actually says — not what TikTok tells you.",
    "Three things you can do this week to take back control.",
]

NUMBER_WORDS = ["one", "two", "three", "four", "five"]

# Tip body templates — DO NOT hardcode position numbers. The pipeline
# numbers them in build_offline_script based on draw order so the spoken
# "number one / two / three" always matches the on-screen "1./2./3.".
TIP_TEMPLATES = [
    (
        "track every dollar for 30 days. Apps like Monarch or a free "
        "Google Sheet work fine. The average person who does this cuts "
        "spending by twelve percent in the first month — that is about "
        "three thousand dollars a year on a fifty-thousand-dollar salary.",
        "TRACK EVERY DOLLAR · 30 DAYS",
    ),
    (
        "automate your savings the day your paycheck lands. Move at "
        "least ten percent into a high-yield savings account before you "
        "can touch it. If you wait until the end of the month, the "
        "money is already gone.",
        "AUTOMATE BEFORE YOU SPEND",
    ),
    (
        "kill one recurring subscription this week. Most Americans have "
        "eight active subscriptions and forget about three. Cutting one "
        "twelve-dollar charge saves a hundred and forty-four dollars a "
        "year — and compounds when you invest it.",
        "CUT 1 SUBSCRIPTION TODAY",
    ),
    (
        "pay yourself first. Treat savings like rent. It is a "
        "non-negotiable bill that you owe future-you. Future-you will "
        "thank present-you in twenty years.",
        "PAY YOURSELF FIRST",
    ),
    (
        "increase income before you cut more lattes. A four-thousand-"
        "dollar raise compounds far more than skipping Starbucks ever "
        "will. Spend an hour a week on a high-paying skill.",
        "RAISE > LATTES",
    ),
    (
        "open a high-yield savings account today. Big banks pay zero "
        "point zero one percent. Online banks pay over four percent. "
        "On ten thousand dollars that is four hundred dollars a year "
        "for clicking a button.",
        "HYSA > BIG BANK",
    ),
]

EXAMPLE_TEMPLATES = [
    "Quick example: invest five dollars a day in an S and P 500 index "
    "fund from age twenty-two. At a seven-percent average return that is "
    "roughly four hundred and twenty thousand dollars by age sixty-five.",
    "Real numbers: a one-hundred-dollar monthly subscription you keep "
    "for ten years equals twelve thousand dollars — plus the compound "
    "growth you lost.",
    "Concrete case: cutting your phone bill from ninety to thirty dollars "
    "saves seven hundred and twenty dollars a year. Invested over thirty "
    "years that is more than seventy thousand dollars.",
]

CTA_TEMPLATES = [
    "Follow for daily money tips. Comment 'BUDGET' and I will send you my "
    "free fifty-thirty-twenty template.",
    "Save this video and share it with one friend who needs to see it. "
    "Follow for one money tip every single day.",
]

LOOP_TEMPLATES = [
    "Remember — most people get this wrong. Don't be most people.",
    "It is not about how much you earn. It is about how much you keep.",
    "Money loves people who pay attention. Pay attention.",
]

HASHTAG_POOL = [
    "#PersonalFinance",
    "#MoneyTips",
    "#FinancialFreedom",
    "#FIRE",
    "#Investing101",
    "#BudgetTips",
    "#SaveMoney",
    "#WealthBuilding",
    "#SideHustle",
    "#PassiveIncome",
    "#MoneyMindset",
    "#FrugalLiving",
]

BROLL_POOL = [
    "wallet cash money",
    "stock market chart green",
    "person typing laptop budget",
    "coins stacking",
    "credit card swipe",
    "city skyline business",
    "calculator finance spreadsheet",
    "bank vault dollars",
    "shopping cart receipt",
    "saving piggy bank",
]


def _normalize_topic(topic: str) -> str:
    topic = topic.strip()
    topic = re.sub(r"\s+", " ", topic)
    return topic


def _topic_low(topic: str) -> str:
    t = _normalize_topic(topic).rstrip(".!?")
    # Avoid double "the" awkwardness in templates.
    if t.lower().startswith("the "):
        return t[4:].lower()
    return t.lower()


def build_offline_script(topic: str, *, seed: int | None = None) -> Script:
    rng = random.Random(seed if seed is not None else hash(topic) & 0xFFFFFFFF)
    topic = _normalize_topic(topic)
    low = _topic_low(topic)

    hook_text = rng.choice(HOOK_TEMPLATES).format(topic_low=low)
    hook_overlay = rng.choice(ON_SCREEN_HOOK)
    promise_text = rng.choice(PROMISE_TEMPLATES)

    tips = rng.sample(TIP_TEMPLATES, k=3)
    example_text = rng.choice(EXAMPLE_TEMPLATES)
    cta_text = rng.choice(CTA_TEMPLATES)
    loop_text = rng.choice(LOOP_TEMPLATES)
    hashtags = rng.sample(HASHTAG_POOL, k=5)
    broll = rng.sample(BROLL_POOL, k=4)

    segments: list[ScriptSegment] = [
        ScriptSegment("hook", hook_text, hook_overlay),
        ScriptSegment("promise", promise_text, "STAY WITH ME"),
    ]
    for i, (vo, overlay) in enumerate(tips):
        word = NUMBER_WORDS[i] if i < len(NUMBER_WORDS) else str(i + 1)
        voice_line = f"Number {word}: {vo}"
        overlay_line = f"{i + 1}. {overlay}"
        segments.append(ScriptSegment(f"tip_{i+1}", voice_line, overlay_line))
    segments.append(ScriptSegment("example", example_text, "THE MATH"))
    segments.append(ScriptSegment("cta", cta_text, "FOLLOW DAILY MONEY TIPS"))
    segments.append(ScriptSegment("loop", loop_text, ""))

    return Script(topic=topic, segments=segments, hashtags=hashtags, broll_terms=broll)


# ---------------------------------------------------------------------------
# OpenAI mode (optional)
# ---------------------------------------------------------------------------


OPENAI_SYSTEM_PROMPT = (
    "You are a Facebook Reels scriptwriter for a faceless personal-finance page. "
    "Audience: US adults 22-45 who feel financially stuck. "
    "Tone: punchy, confident, no jargon, no get-rich-quick promises. "
    "Output strict JSON only, no commentary."
)

OPENAI_USER_PROMPT = """Topic: {topic}

Write a 60-80 second faceless Reel script.

Return JSON matching exactly this schema:

{{
  "segments": [
    {{"role": "hook",    "voiceover": "...", "on_screen": "ALL CAPS <= 8 words"}},
    {{"role": "promise", "voiceover": "...", "on_screen": "ALL CAPS <= 6 words"}},
    {{"role": "tip_1",   "voiceover": "...", "on_screen": "1. <= 5 words"}},
    {{"role": "tip_2",   "voiceover": "...", "on_screen": "2. <= 5 words"}},
    {{"role": "tip_3",   "voiceover": "...", "on_screen": "3. <= 5 words"}},
    {{"role": "example", "voiceover": "...", "on_screen": "THE MATH"}},
    {{"role": "cta",     "voiceover": "...", "on_screen": "FOLLOW DAILY MONEY TIPS"}},
    {{"role": "loop",    "voiceover": "...", "on_screen": ""}}
  ],
  "hashtags": ["#tag1","#tag2","#tag3","#tag4","#tag5"],
  "broll_terms": ["pexels search 1","pexels search 2","pexels search 3","pexels search 4"]
}}

Hook must create curiosity in <= 12 spoken words.
Each tip must include one concrete dollar figure.
Never promise guaranteed returns. Educational framing only.
"""


def build_openai_script(topic: str, *, model: str = "gpt-4o-mini") -> Script | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        # Lazy import so the module works without the dependency.
        from urllib.request import Request, urlopen  # noqa: WPS433

        payload = {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                {"role": "user", "content": OPENAI_USER_PROMPT.format(topic=topic)},
            ],
            "temperature": 0.7,
        }
        req = Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        segments = [
            ScriptSegment(
                role=s.get("role", f"seg_{i}"),
                voiceover=s.get("voiceover", "").strip(),
                on_screen=s.get("on_screen", "").strip(),
            )
            for i, s in enumerate(parsed.get("segments", []))
            if s.get("voiceover")
        ]
        if not segments:
            return None
        return Script(
            topic=topic,
            segments=segments,
            hashtags=[h for h in parsed.get("hashtags", []) if isinstance(h, str)][:5],
            broll_terms=[b for b in parsed.get("broll_terms", []) if isinstance(b, str)][:4],
        )
    except Exception as exc:  # pragma: no cover - network path
        print(f"  ! OpenAI script generation failed: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_script(topic: str, *, mode: str = "offline", seed: int | None = None) -> Script:
    """Build a Script from a topic string. Falls back to offline mode on failure."""
    topic = _normalize_topic(topic)
    if not topic:
        raise ValueError("topic is empty")
    if mode == "openai":
        result = build_openai_script(topic)
        if result is not None:
            return result
        print("  ! Falling back to offline template script.", file=sys.stderr)
    return build_offline_script(topic, seed=seed)


def _iter_lines(script: Script) -> Iterable[str]:
    yield f"# Topic: {script.topic}"
    yield ""
    for s in script.segments:
        yield f"## [{s.role}]"
        if s.on_screen:
            yield f"ON-SCREEN: {s.on_screen}"
        yield s.voiceover
        yield ""
    yield f"Hashtags: {' '.join(script.hashtags)}"
    yield f"B-roll: {', '.join(script.broll_terms)}"


def main() -> int:
    p = argparse.ArgumentParser(description="Generate a faceless Reel script.")
    p.add_argument("topic", help="Topic / hook idea")
    p.add_argument("--mode", choices=["offline", "openai"], default="offline")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--json", action="store_true", help="Output JSON instead of markdown")
    args = p.parse_args()

    script = build_script(args.topic, mode=args.mode, seed=args.seed)
    if args.json:
        json.dump(script.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for line in _iter_lines(script):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
