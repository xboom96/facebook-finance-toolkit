"""Single CLI entry point for publishing a generated Short to Facebook.

Reads from a ``shorts/output/<date>/<slug>/`` folder by default — the same
layout that ``shorts/pipeline.py`` produces — but accepts any directory or
direct MP4 path. Description / hashtags come from ``metadata.json`` if it
exists; ``--description`` overrides.

Examples::

    # Dry-run (no Meta calls, just shows what would be uploaded)
    python3 -m publish.cli --short shorts/output/2026-05-27/5-subscriptions-to-cancel-today --dry-run

    # Real Reels upload (requires META_PAGE_ID + META_PAGE_TOKEN env vars)
    python3 -m publish.cli --short shorts/output/2026-05-27/5-subscriptions-to-cancel-today

    # Direct MP4 path
    python3 -m publish.cli --mp4 /path/to/short.mp4 --description "..." --as video

    # Override description and tag mode
    python3 -m publish.cli --short shorts/output/today --as reels --description "Custom caption #money #finance"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as a script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from publish.fb_reels import FBReelsClient, credentials_from_env as reels_creds  # noqa: E402
from publish.fb_video import FBVideoClient, credentials_from_env as video_creds  # noqa: E402


def _resolve_short_dir(arg_short: Path | None, arg_mp4: Path | None) -> tuple[Path, Path | None]:
    """Resolve the input into (mp4_path, optional metadata.json path)."""
    if arg_mp4:
        mp4 = Path(arg_mp4).resolve()
        if not mp4.exists():
            sys.exit(f"--mp4 path does not exist: {mp4}")
        # Look for a sibling metadata.json
        sibling_meta = mp4.parent / "metadata.json"
        return mp4, sibling_meta if sibling_meta.exists() else None

    if arg_short:
        short_dir = Path(arg_short).resolve()
        if short_dir.is_file():
            # User pointed --short directly at the mp4
            return short_dir, (short_dir.parent / "metadata.json" if (short_dir.parent / "metadata.json").exists() else None)
        mp4 = short_dir / "short.mp4"
        if not mp4.exists():
            sys.exit(f"no short.mp4 in {short_dir} — did the pipeline finish?")
        meta = short_dir / "metadata.json"
        return mp4, meta if meta.exists() else None

    sys.exit("must specify --short <dir> or --mp4 <file>")


def _build_description(metadata_path: Path | None, override: str | None) -> str:
    if override:
        return override
    if metadata_path and metadata_path.exists():
        try:
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"warn: could not parse {metadata_path}: {exc}", file=sys.stderr)
            return ""
        # Best-effort: prefer the description field, fall back to title + hashtags.
        desc = (meta.get("description") or "").strip()
        hashtags = meta.get("hashtags") or []
        if isinstance(hashtags, list):
            tag_line = " ".join(t if t.startswith("#") else f"#{t}" for t in hashtags)
        else:
            tag_line = str(hashtags)
        title = (meta.get("title") or "").strip()
        if desc:
            # The script generator already embeds hashtags inside `description`,
            # so only append the tag_line if it's missing — avoids the
            # "#tag #tag #tag" doubling that happens when both are present.
            if tag_line and tag_line not in desc:
                return f"{desc}\n\n{tag_line}".strip()
            return desc
        if title:
            return f"{title}\n\n{tag_line}".strip() if tag_line else title
        return tag_line.strip()
    return ""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=False)
    src.add_argument("--short", type=Path, help="Path to a shorts/output/<date>/<slug>/ folder")
    src.add_argument("--mp4", type=Path, help="Direct path to a .mp4 file")
    p.add_argument(
        "--as",
        dest="upload_kind",
        choices=["reels", "video"],
        default="reels",
        help="Which Facebook API to use (default: reels)",
    )
    p.add_argument(
        "--description",
        default=None,
        help="Override the caption/description. Defaults to metadata.json title+description+hashtags.",
    )
    p.add_argument(
        "--title",
        default=None,
        help="Optional video title (classic Videos API only). Reels API does not use a separate title.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not call Meta. Print the exact request that would be made.",
    )
    p.add_argument(
        "--unpublished",
        action="store_true",
        help="(video mode only) Upload but do not publish — leaves the video as draft.",
    )
    p.add_argument(
        "--wait",
        action="store_true",
        help="(reels mode only) Poll the video status until Meta reports `ready`.",
    )
    args = p.parse_args()

    mp4, meta_path = _resolve_short_dir(args.short, args.mp4)
    description = _build_description(meta_path, args.description)

    if args.upload_kind == "reels":
        if args.dry_run:
            creds = {"page_id": "DRY_RUN_PAGE", "page_token": "DRY_RUN_TOKEN", "graph_version": "v19.0"}
        else:
            creds = reels_creds()
        client = FBReelsClient(
            page_id=creds["page_id"],
            page_token=creds["page_token"],
            graph_version=creds["graph_version"],
            dry_run=args.dry_run,
        )
        result = client.publish(mp4, description=description, wait_for_processing=args.wait)
        print()
        print("=== reels upload result ===")
        print(f"  dry_run:         {result.dry_run}")
        print(f"  video_id:        {result.video_id}")
        print(f"  bytes_uploaded:  {result.bytes_uploaded:,}")
        if result.permalink:
            print(f"  permalink:       {result.permalink}")
        print(f"  description ({len(result.description)} chars):")
        for line in (result.description or "").splitlines()[:20]:
            print(f"      {line}")
    else:
        if args.dry_run:
            creds = {"page_id": "DRY_RUN_PAGE", "page_token": "DRY_RUN_TOKEN", "graph_version": "v19.0"}
        else:
            creds = video_creds()
        client = FBVideoClient(
            page_id=creds["page_id"],
            page_token=creds["page_token"],
            graph_version=creds["graph_version"],
            dry_run=args.dry_run,
        )
        result = client.publish(
            mp4,
            description=description,
            title=args.title,
            published=not args.unpublished,
        )
        print()
        print("=== video upload result ===")
        print(f"  dry_run:         {result.dry_run}")
        print(f"  video_id:        {result.video_id}")
        print(f"  post_id:         {result.post_id}")
        print(f"  bytes_uploaded:  {result.bytes_uploaded:,}")
        if result.permalink:
            print(f"  permalink:       {result.permalink}")
        print(f"  description ({len(result.description)} chars):")
        for line in (result.description or "").splitlines()[:20]:
            print(f"      {line}")


if __name__ == "__main__":
    main()
