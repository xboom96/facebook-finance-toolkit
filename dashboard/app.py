#!/usr/bin/env python3
"""Facebook Page Earnings Dashboard.

A small Flask app that queries Meta Graph API for your Page and shows:
- Page-level reach, impressions, follower count
- Per-post: reach, impressions, engagement, video views, avg watch time
- Estimated RPM (revenue per 1k impressions) — user-configurable assumption
- Top posts by engagement and by estimated revenue

Usage:
    pip install -r requirements.txt
    python app.py
    # then open http://127.0.0.1:5000

Or run in demo mode (no Meta credentials needed):
    python app.py --demo

Required environment / form values:
    META_PAGE_ID         e.g. 123456789012345
    META_PAGE_TOKEN      page access token (see SETUP_META_TOKEN.md)
    META_GRAPH_VERSION   default v19.0

Why a Page Access Token (not user)?
    Page tokens are scoped to the Page and can read read_insights and
    pages_read_engagement without re-auth. See SETUP_META_TOKEN.md for
    a step-by-step guide.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, redirect, render_template, request, session, url_for

GRAPH_BASE = "https://graph.facebook.com"
DEFAULT_VERSION = "v19.0"
DEFAULT_RPM_USD = 5.0  # $5 per 1k impressions — adjust per niche


@dataclass
class PostMetric:
    post_id: str
    created_time: str
    message: str
    permalink: str
    impressions: int
    reach: int
    engaged_users: int
    video_views: int
    video_avg_time_watched_ms: int
    reactions: int
    comments: int
    shares: int

    @property
    def engagement_rate(self) -> float:
        if not self.reach:
            return 0.0
        return round(self.engaged_users / self.reach * 100, 2)

    def estimated_revenue(self, rpm_usd: float) -> float:
        return round(self.impressions / 1000.0 * rpm_usd, 2)

    @property
    def avg_watch_seconds(self) -> float:
        return round(self.video_avg_time_watched_ms / 1000.0, 1)


def graph_get(path: str, params: dict[str, Any], *, retries: int = 3) -> dict:
    """GET against Meta Graph API. Returns parsed JSON, raises on hard failure."""
    qs = urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{GRAPH_BASE}/{path.lstrip('/')}?{qs}"
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_err = exc
    raise RuntimeError(f"Graph API request failed: {last_err}") from last_err


def fetch_page_summary(page_id: str, token: str, version: str) -> dict[str, Any]:
    fields = "name,fan_count,followers_count,about,link,picture{url}"
    return graph_get(
        f"{version}/{page_id}",
        {"fields": fields, "access_token": token},
    )


def fetch_recent_posts(
    page_id: str, token: str, version: str, limit: int = 25
) -> list[PostMetric]:
    """Return recent posts with insights merged in."""
    post_fields = "id,message,permalink_url,created_time"
    insight_metrics = (
        "post_impressions,"
        "post_impressions_unique,"
        "post_engaged_users,"
        "post_video_views,"
        "post_video_avg_time_watched,"
        "post_reactions_by_type_total,"
        "post_clicks"
    )
    fields = (
        f"{post_fields},"
        f"insights.metric({insight_metrics}),"
        "reactions.summary(true),"
        "comments.summary(true),"
        "shares"
    )
    data = graph_get(
        f"{version}/{page_id}/posts",
        {"fields": fields, "limit": limit, "access_token": token},
    )
    out: list[PostMetric] = []
    for post in data.get("data", []):
        insights = {i["name"]: i for i in post.get("insights", {}).get("data", [])}

        def metric(name: str, default: int = 0) -> int:
            try:
                vals = insights[name]["values"]
                if not vals:
                    return default
                val = vals[0].get("value", default)
                if isinstance(val, dict):
                    return int(sum(v for v in val.values() if isinstance(v, (int, float))))
                return int(val)
            except (KeyError, IndexError, TypeError, ValueError):
                return default

        out.append(
            PostMetric(
                post_id=post.get("id", ""),
                created_time=post.get("created_time", ""),
                message=(post.get("message") or "")[:140],
                permalink=post.get("permalink_url", ""),
                impressions=metric("post_impressions"),
                reach=metric("post_impressions_unique"),
                engaged_users=metric("post_engaged_users"),
                video_views=metric("post_video_views"),
                video_avg_time_watched_ms=metric("post_video_avg_time_watched"),
                reactions=int(post.get("reactions", {}).get("summary", {}).get("total_count", 0) or 0),
                comments=int(post.get("comments", {}).get("summary", {}).get("total_count", 0) or 0),
                shares=int((post.get("shares") or {}).get("count", 0) or 0),
            )
        )
    return out


def demo_data() -> tuple[dict[str, Any], list[PostMetric]]:
    """Return synthetic data so the UI works without Meta credentials."""
    page = {
        "name": "MoneyHabits Daily (DEMO)",
        "fan_count": 12_487,
        "followers_count": 13_204,
        "about": "Daily money tips. Demo mode — wire up META_PAGE_TOKEN for real data.",
        "link": "https://facebook.com/example",
        "picture": {"data": {"url": ""}},
    }
    titles = [
        "5 subscriptions to cancel today (save $1,200/year)",
        "3 money mistakes that keep you poor",
        "If you invest $5/day from age 22 you'll have $1.2M",
        "This side hustle made me $2,400 last month",
        "I tried 5 budgeting apps — this one won",
        "How I cut my grocery bill by 40%",
        "Why your bank account is empty every payday",
        "The 1% trick that lets you retire 10 years earlier",
        "5 ways to make $100 this weekend",
        "10 things broke people waste money on",
        "I made $80k and still felt broke. Here's why.",
        "Index funds explained in 60 seconds",
        "How to negotiate a $10k raise",
        "The free spreadsheet that changed my finances",
        "The 24-hour rule that saved me $5k last year",
    ]
    rng = random.Random(7)
    posts: list[PostMetric] = []
    for i, title in enumerate(titles):
        reach = rng.randint(3_000, 220_000)
        impressions = int(reach * rng.uniform(1.05, 1.45))
        engaged = int(reach * rng.uniform(0.015, 0.08))
        vid_views = int(reach * rng.uniform(0.6, 1.1))
        posts.append(
            PostMetric(
                post_id=f"demo_{i}",
                created_time=(dt.date.today() - dt.timedelta(days=i)).isoformat(),
                message=title,
                permalink="https://facebook.com/demo",
                impressions=impressions,
                reach=reach,
                engaged_users=engaged,
                video_views=vid_views,
                video_avg_time_watched_ms=int(rng.uniform(8_000, 42_000)),
                reactions=int(engaged * rng.uniform(0.4, 0.7)),
                comments=int(engaged * rng.uniform(0.05, 0.15)),
                shares=int(engaged * rng.uniform(0.02, 0.08)),
            )
        )
    return page, posts


# ----------------------- Flask app -----------------------

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_hex(16))
app.config["DEMO_MODE"] = False


@app.route("/")
def index():
    if app.config["DEMO_MODE"]:
        return redirect(url_for("dashboard"))
    if not session.get("page_id") or not session.get("token"):
        return redirect(url_for("setup"))
    return redirect(url_for("dashboard"))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    error = None
    if request.method == "POST":
        page_id = request.form.get("page_id", "").strip()
        token = request.form.get("token", "").strip()
        rpm = request.form.get("rpm", str(DEFAULT_RPM_USD)).strip()
        version = request.form.get("version", DEFAULT_VERSION).strip() or DEFAULT_VERSION
        if not page_id or not token:
            error = "Both Page ID and Access Token are required."
        else:
            # quick validation
            try:
                summary = fetch_page_summary(page_id, token, version)
                if "error" in summary:
                    error = f"Meta API error: {summary['error'].get('message')}"
                else:
                    session["page_id"] = page_id
                    session["token"] = token
                    session["version"] = version
                    try:
                        session["rpm"] = float(rpm)
                    except ValueError:
                        session["rpm"] = DEFAULT_RPM_USD
                    return redirect(url_for("dashboard"))
            except Exception as exc:
                error = f"Could not reach Meta Graph API: {exc}"
    return render_template(
        "setup.html",
        error=error,
        default_rpm=DEFAULT_RPM_USD,
        default_version=DEFAULT_VERSION,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("setup"))


@app.route("/dashboard")
def dashboard():
    rpm = float(session.get("rpm", DEFAULT_RPM_USD))
    if app.config["DEMO_MODE"]:
        page, posts = demo_data()
    else:
        if not session.get("page_id") or not session.get("token"):
            return redirect(url_for("setup"))
        try:
            page = fetch_page_summary(
                session["page_id"], session["token"], session.get("version", DEFAULT_VERSION)
            )
            posts = fetch_recent_posts(
                session["page_id"], session["token"], session.get("version", DEFAULT_VERSION)
            )
        except Exception as exc:
            return render_template("error.html", error=str(exc))

    total_impressions = sum(p.impressions for p in posts)
    total_reach = sum(p.reach for p in posts)
    total_engaged = sum(p.engaged_users for p in posts)
    total_revenue = round(total_impressions / 1000.0 * rpm, 2)
    avg_eng_rate = round(total_engaged / total_reach * 100, 2) if total_reach else 0.0

    by_revenue = sorted(posts, key=lambda p: p.estimated_revenue(rpm), reverse=True)
    by_engagement = sorted(posts, key=lambda p: p.engagement_rate, reverse=True)

    return render_template(
        "dashboard.html",
        page=page,
        posts=posts,
        by_revenue=by_revenue[:10],
        by_engagement=by_engagement[:10],
        rpm=rpm,
        demo=app.config["DEMO_MODE"],
        totals={
            "impressions": total_impressions,
            "reach": total_reach,
            "engaged": total_engaged,
            "revenue": total_revenue,
            "avg_eng_rate": avg_eng_rate,
            "post_count": len(posts),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--demo", action="store_true", help="run with synthetic data")
    args = parser.parse_args()

    app.config["DEMO_MODE"] = args.demo
    print(f"Starting dashboard on http://{args.host}:{args.port}  (demo={args.demo})")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
