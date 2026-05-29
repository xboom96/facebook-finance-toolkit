#!/usr/bin/env python3
"""Web app for the viral Facebook Reels script generator.

A tiny Flask UI on top of ``reels/generate.py``. Fill in niche, topic, date
and duration, hit generate, and get the full Reel package (hook, voiceover
script, visual ideas, caption, title, description, tags) rendered on screen.
Everything runs offline — no API key or login required.

Usage:
    pip install -r reels/requirements.txt
    python3 reels/app.py
    # open http://127.0.0.1:5001
"""
from __future__ import annotations

import argparse
import datetime as dt
import json

from flask import Flask, Response, render_template, request

from generate import generate

app = Flask(__name__)

DURATIONS = [15, 30, 45, 60, 90, 120]
EXAMPLE_NICHES = [
    "personal finance", "fitness", "travel", "cooking", "tech",
    "productivity", "parenting", "real estate", "beauty",
]


def _parse_form() -> dict:
    return {
        "niche": (request.values.get("niche") or "personal finance").strip(),
        "topic": (request.values.get("topic") or "").strip(),
        "date": (request.values.get("date") or dt.date.today().isoformat()).strip(),
        "duration": _safe_int(request.values.get("duration"), 60),
        "seed": _safe_int(request.values.get("seed"), None),
    }


def _safe_int(value: str | None, default: int | None) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


@app.route("/", methods=["GET", "POST"])
def index():
    form = _parse_form()
    pkg = None
    error = None
    if request.method == "POST":
        if not form["topic"]:
            error = "Please enter a topic for the Reel."
        else:
            pkg = generate(
                form["niche"],
                form["topic"],
                date=form["date"],
                duration=form["duration"] or 60,
                seed=form["seed"],
            )
    return render_template(
        "index.html",
        form=form,
        pkg=pkg,
        error=error,
        durations=DURATIONS,
        example_niches=EXAMPLE_NICHES,
        today=dt.date.today().isoformat(),
    )


@app.route("/api/generate")
def api_generate():
    """JSON endpoint: /api/generate?niche=...&topic=...&date=...&duration=60"""
    form = _parse_form()
    if not form["topic"]:
        return Response(
            json.dumps({"error": "topic is required"}),
            status=400,
            mimetype="application/json",
        )
    pkg = generate(
        form["niche"],
        form["topic"],
        date=form["date"],
        duration=form["duration"] or 60,
        seed=form["seed"],
    )
    return Response(
        json.dumps(pkg.to_dict(), indent=2, ensure_ascii=False),
        mimetype="application/json",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    print(f"Starting Reels generator on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
