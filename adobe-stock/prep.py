"""Batch metadata generator for Adobe Stock contributor uploads.

Walks a folder of images / videos and writes ``adobe_stock.csv`` matching
the format Adobe Stock's Contributor Portal accepts for SFTP+CSV uploads.

CSV columns (per Adobe Stock spec):

    Filename, Title, Keywords, Category, Releases

Categories: 1 = animals, 2 = buildings, 3 = business, 4 = drinks, 5 = environment,
6 = arts, 7 = food, 8 = graphic resources, 9 = hobbies & leisure, 10 = industry,
11 = landscapes, 12 = lifestyle, 13 = people, 14 = plants & flowers, 15 = culture,
16 = science, 17 = social issues, 18 = sports, 19 = technology, 20 = transport,
21 = travel.

Usage examples::

    python3 adobe-stock/prep.py ./assets/finance --niche finance --out adobe_stock.csv
    python3 adobe-stock/prep.py ./assets/ai --niche ai-tech --use-vision
    python3 adobe-stock/prep.py ./photos --niche custom --keywords "yoga,wellness,studio,mat,mindfulness"

Vision mode is optional: only used when ``--use-vision`` is passed AND
``OPENAI_API_KEY`` is set. Otherwise titles are templated from the niche
and the filename.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow running as a script from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from keywords import KEYWORD_LIBRARIES, get_keywords, keywords_from_filename  # noqa: E402


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mxf", ".avi", ".mkv"}

# Niche → default Adobe Stock category code.
CATEGORY_FOR_NICHE: dict[str, int] = {
    "finance": 3,        # business
    "business": 3,
    "ai-tech": 19,       # technology
    "lifestyle": 12,
    "custom": 8,         # graphic resources (most flexible)
}


@dataclass
class Asset:
    path: Path
    filename: str
    is_video: bool
    title: str
    keywords: list[str]
    category: int
    releases: str = ""


def _gather_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
            out.append(p)
    return out


def _make_title(filename: str, niche: str) -> str:
    """Template a human-readable title from a filename + niche."""
    # Strip extension, replace separators, title-case it.
    base = os.path.splitext(os.path.basename(filename))[0]
    pretty = base.replace("-", " ").replace("_", " ").strip()
    # Drop trailing digits / "img" / "shot".
    parts = [p for p in pretty.split() if not p.isdigit() and p.lower() not in {"img", "image", "shot", "clip"}]
    pretty = " ".join(parts).capitalize()

    niche_suffix = {
        "finance": " — personal finance and investing concept",
        "business": " — corporate business workplace concept",
        "ai-tech": " — artificial intelligence and technology concept",
        "lifestyle": " — modern lifestyle concept",
    }.get(niche, "")

    title = (pretty or niche.title()) + niche_suffix
    # Adobe Stock title limit is 200 chars; ours is fine.
    return title[:200]


def _build_keywords(filename: str, niche: str, extra: list[str]) -> list[str]:
    """Merge filename-derived keywords with the niche library, dedup, cap at 49."""
    out: list[str] = []
    seen: set[str] = set()

    def add(words: list[str]) -> None:
        for w in words:
            w = w.strip().lower()
            if not w or w in seen:
                continue
            seen.add(w)
            out.append(w)
            if len(out) >= 49:
                return

    add(keywords_from_filename(filename))
    add(extra)
    add(get_keywords(niche))
    return out[:49]


def _maybe_enrich_with_vision(asset: Asset, openai_client) -> None:
    """If an OpenAI client is provided, ask gpt-4o-mini for a better title + keywords."""
    if openai_client is None or asset.is_video:
        return
    try:
        # Encode the image once.
        import base64

        with asset.path.open("rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        ext = asset.path.suffix.lower().lstrip(".")
        if ext == "jpg":
            ext = "jpeg"
        data_url = f"data:image/{ext};base64,{b64}"

        prompt = (
            "You are tagging a stock photo for Adobe Stock. Reply in EXACTLY "
            "this format and nothing else:\n"
            "TITLE: <one descriptive sentence, max 180 chars>\n"
            "KEYWORDS: kw1, kw2, kw3, ... (max 30 single-word or two-word keywords)\n"
            "Do not mention copyright, do not mention 'image of', "
            "do not include people's real names. Be specific about subject, action, "
            "mood and color where visible."
        )
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=400,
            temperature=0.4,
        )
        body = resp.choices[0].message.content or ""
        title_line = next((ln for ln in body.splitlines() if ln.upper().startswith("TITLE:")), "")
        kw_line = next((ln for ln in body.splitlines() if ln.upper().startswith("KEYWORDS:")), "")
        if title_line:
            asset.title = title_line.split(":", 1)[1].strip()[:200]
        if kw_line:
            extra = [k.strip().lower() for k in kw_line.split(":", 1)[1].split(",") if k.strip()]
            # Re-merge with niche keywords.
            merged: list[str] = []
            seen: set[str] = set()
            for w in extra + asset.keywords:
                if w not in seen:
                    seen.add(w)
                    merged.append(w)
            asset.keywords = merged[:49]
    except Exception as exc:  # noqa: BLE001 — degrade gracefully on any API failure
        print(f"  vision enrichment failed for {asset.filename}: {exc}", file=sys.stderr)


def build_assets(
    root: Path,
    niche: str,
    extra_keywords: list[str],
    use_vision: bool,
) -> list[Asset]:
    files = _gather_files(root)
    if not files:
        raise SystemExit(f"no image/video files found under {root}")

    category = CATEGORY_FOR_NICHE.get(niche, CATEGORY_FOR_NICHE["custom"])

    client = None
    if use_vision and os.environ.get("OPENAI_API_KEY"):
        try:
            from openai import OpenAI  # type: ignore

            client = OpenAI()
        except ImportError:
            print("--use-vision requested but `openai` is not installed; falling back to template mode", file=sys.stderr)

    assets: list[Asset] = []
    for path in files:
        ext = path.suffix.lower()
        is_video = ext in VIDEO_EXTS
        title = _make_title(path.name, niche)
        keywords = _build_keywords(path.name, niche, extra_keywords)
        asset = Asset(
            path=path,
            filename=path.name,
            is_video=is_video,
            title=title,
            keywords=keywords,
            category=category,
        )
        if client is not None:
            _maybe_enrich_with_vision(asset, client)
        assets.append(asset)

    return assets


def write_csv(assets: list[Asset], out_path: Path) -> Path:
    """Write the CSV in Adobe Stock's contributor-portal format."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        # Adobe Stock spec uses semicolons by default in the EU sample but
        # accepts commas globally — we use commas for maximum compatibility.
        writer = csv.writer(f)
        writer.writerow(["Filename", "Title", "Keywords", "Category", "Releases"])
        for a in assets:
            writer.writerow(
                [
                    a.filename,
                    a.title,
                    ", ".join(a.keywords),
                    str(a.category),
                    a.releases,
                ]
            )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="Folder or single file to process")
    parser.add_argument(
        "--niche",
        choices=sorted(set(list(KEYWORD_LIBRARIES.keys()) + ["custom"])),
        default="business",
        help="Niche keyword library to use (default: business)",
    )
    parser.add_argument(
        "--keywords",
        default="",
        help="Comma-separated extra keywords to prepend (e.g. for --niche custom)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("adobe_stock.csv"),
        help="Output CSV path (default: ./adobe_stock.csv)",
    )
    parser.add_argument(
        "--use-vision",
        action="store_true",
        help="Use OpenAI gpt-4o-mini to enrich titles/keywords (needs OPENAI_API_KEY)",
    )
    args = parser.parse_args()

    extra = [k.strip() for k in args.keywords.split(",") if k.strip()]
    assets = build_assets(args.path, args.niche, extra, args.use_vision)
    out = write_csv(assets, args.out)
    print(f"wrote {len(assets)} rows to {out}")
    print("upload your assets via Adobe Stock SFTP, then import this CSV in the Contributor Portal.")


if __name__ == "__main__":
    main()
