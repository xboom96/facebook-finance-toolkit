"""Niche-specific keyword libraries for Adobe Stock contributor uploads.

Adobe Stock allows up to 49 keywords per asset and ranks the **first 10**
heaviest in search. Each library here is ordered: the first 10 are the
high-volume search terms; the remainder add long-tail discoverability.

Sources behind the lists:

* Adobe Stock contributor portal — top-searched terms by category (2025).
* Shutterstock keyword research tools (cross-pollinates well).
* Manual filtering of suggestions that have very low buyer intent.
"""
from __future__ import annotations

KEYWORD_LIBRARIES: dict[str, list[str]] = {
    # ---------------------------------------------------------------
    # Personal finance / investing (high CPM, evergreen demand)
    # ---------------------------------------------------------------
    "finance": [
        "finance", "money", "investment", "savings", "budget",
        "wealth", "financial", "dollar", "cash", "currency",
        "stock market", "trading", "economy", "banking", "credit",
        "loan", "debt", "retirement", "401k", "ira",
        "compound interest", "passive income", "side hustle", "frugal",
        "saving money", "personal finance", "financial freedom",
        "financial planning", "wealth management", "income",
        "expense", "tax", "accounting", "spreadsheet", "calculator",
        "bank", "credit card", "wallet", "purse", "coins",
        "piggy bank", "vault", "safe", "deposit", "withdrawal",
        "growth", "profit", "loss", "interest rate", "inflation",
    ],

    # ---------------------------------------------------------------
    # Corporate / business / office
    # ---------------------------------------------------------------
    "business": [
        "business", "office", "meeting", "team", "corporate",
        "professional", "businessman", "businesswoman", "executive",
        "manager",
        "laptop", "computer", "monitor", "desk", "workplace",
        "remote work", "work from home", "co-working", "startup",
        "entrepreneur",
        "leadership", "strategy", "planning", "presentation",
        "negotiation",
        "handshake", "deal", "contract", "agreement", "partnership",
        "growth", "success", "achievement", "goal", "innovation",
        "productivity", "workflow", "schedule", "calendar", "deadline",
        "email", "communication", "collaboration", "brainstorm",
        "whiteboard",
        "skyscraper", "city", "downtown", "boardroom", "conference",
    ],

    # ---------------------------------------------------------------
    # AI / tech (fastest-growing buyer demand in 2025)
    # ---------------------------------------------------------------
    "ai-tech": [
        "artificial intelligence", "ai", "machine learning",
        "deep learning", "neural network",
        "automation", "robot", "robotics", "humanoid", "android",
        "data", "big data", "analytics", "algorithm", "code",
        "software", "developer", "programming", "cybersecurity",
        "encryption",
        "cloud computing", "server", "data center", "network",
        "internet of things",
        "blockchain", "cryptocurrency", "bitcoin", "ethereum", "web3",
        "metaverse", "virtual reality", "augmented reality", "vr", "ar",
        "smartphone", "tablet", "wearable", "smartwatch", "innovation",
        "futuristic", "technology", "digital", "transformation", "saas",
        "chip", "circuit", "processor", "gpu", "semiconductor",
    ],

    # ---------------------------------------------------------------
    # Lifestyle / frugal living (good for "personal finance" page B-roll)
    # ---------------------------------------------------------------
    "lifestyle": [
        "lifestyle", "home", "family", "cooking", "groceries",
        "shopping", "supermarket", "kitchen", "meal prep", "healthy food",
        "minimalism", "organized", "decluttered", "tidy", "clean",
        "savings goal", "frugal living", "budget meals", "diy", "homemade",
        "coffee", "morning routine", "productivity", "habits", "journal",
        "fitness", "yoga", "meditation", "wellness", "self care",
        "reading", "books", "library", "study", "learning",
        "travel", "vacation", "weekend", "trip", "explore",
        "coupon", "discount", "sale", "deal", "thrifty",
        "garden", "plants", "indoor plants", "herb garden", "balcony",
    ],
}


def get_keywords(niche: str) -> list[str]:
    """Return up to 49 keywords for the given niche, falling back to ``business``."""
    return KEYWORD_LIBRARIES.get(niche.lower(), KEYWORD_LIBRARIES["business"])[:49]


def keywords_from_filename(filename: str) -> list[str]:
    """Extract candidate keywords from a filename like ``coins-stack-finance-001.jpg``.

    Strips numbers, file extensions, common separators, and short tokens.
    """
    import os
    import re

    base = os.path.splitext(os.path.basename(filename))[0]
    parts = re.split(r"[-_\s\.]+", base.lower())
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        # Skip purely numeric or single-letter tokens.
        if len(p) < 3 or p.isdigit():
            continue
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out
