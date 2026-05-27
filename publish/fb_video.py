"""Facebook **classic Videos API** uploader.

Use this when you want to post the MP4 as a regular Page video rather than
explicitly as a Reel. Facebook's algorithm will still index vertical 9:16
videos posted via this endpoint into the Reels tab on most surfaces, but
this gives you a single-request upload (no resumable session) which is
simpler when reliability matters more than Reels-only placement.

API endpoint::

    POST https://graph-video.facebook.com/{api}/{page-id}/videos
    multipart/form-data: source=<file>, description=<text>, access_token=<token>

Docs: https://developers.facebook.com/docs/graph-api/reference/video

This module uses ``urllib`` + a tiny hand-rolled multipart encoder so there
is no ``requests`` dependency — same approach as ``dashboard/app.py``.
"""
from __future__ import annotations

import json
import mimetypes
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Classic uploads use the dedicated graph-video subdomain for large files.
GRAPH_VIDEO_BASE = "https://graph-video.facebook.com"
DEFAULT_GRAPH_VERSION = "v19.0"
DEFAULT_TIMEOUT = 300  # large uploads take time

MAX_DESCRIPTION_CHARS = 5000


@dataclass
class VideoUploadResult:
    video_id: str
    post_id: str | None
    permalink: str | None
    description: str
    bytes_uploaded: int
    dry_run: bool
    debug: dict[str, Any] = field(default_factory=dict)


class FBVideoAPIError(RuntimeError):
    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload or {}


class FBVideoClient:
    """Uploads videos via the classic Page Videos API."""

    def __init__(
        self,
        page_id: str,
        page_token: str,
        *,
        graph_version: str = DEFAULT_GRAPH_VERSION,
        dry_run: bool = False,
        verbose: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.page_id = page_id
        self.page_token = page_token
        self.graph_version = graph_version
        self.dry_run = dry_run
        self.verbose = verbose
        self.timeout = timeout

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [video] {msg}", flush=True)

    def publish(
        self,
        mp4_path: Path,
        *,
        description: str = "",
        title: str | None = None,
        published: bool = True,
    ) -> VideoUploadResult:
        """Upload ``mp4_path`` as a regular Page video.

        :param published: if False, the video is uploaded but kept as
            unpublished — useful for staging content for later review or
            cross-posting via Meta Business Suite.
        """
        mp4_path = Path(mp4_path).resolve()
        if not mp4_path.exists():
            raise FileNotFoundError(f"no such file: {mp4_path}")

        size = mp4_path.stat().st_size
        clean_desc = self._sanitize_description(description)

        if self.dry_run:
            self._log("DRY RUN — no Meta calls will be made")
            self._log(f"would upload: {mp4_path}")
            self._log(f"size:         {size:,} bytes")
            self._log(f"description:  {clean_desc[:160]}{'…' if len(clean_desc) > 160 else ''}")
            self._log(f"title:        {title or '(none)'}")
            self._log(f"page id:      {self.page_id}")
            self._log(f"published:    {published}")
            return VideoUploadResult(
                video_id="DRY_RUN_VIDEO_ID",
                post_id="DRY_RUN_POST_ID",
                permalink=None,
                description=clean_desc,
                bytes_uploaded=size,
                dry_run=True,
                debug={"endpoint": "POST /{page}/videos"},
            )

        # Build the multipart request.
        boundary = f"----devin-fft-{uuid.uuid4().hex}"
        fields = {
            "description": clean_desc,
            "access_token": self.page_token,
            "published": "true" if published else "false",
        }
        if title:
            fields["title"] = title

        body, content_type = _encode_multipart(
            boundary=boundary,
            text_fields=fields,
            file_field=("source", mp4_path),
        )

        url = (
            f"{GRAPH_VIDEO_BASE}/{self.graph_version}/{self.page_id}/videos"
        )
        self._log(f"POST {url}")
        self._log(f"uploading {size:,} bytes as multipart …")

        req = Request(url, data=body, method="POST", headers={"Content-Type": content_type})
        with urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise FBVideoAPIError(f"non-JSON response: {raw[:200]!r}")
        if "error" in data:
            raise FBVideoAPIError(
                f"Meta API error: {data['error'].get('message') or data['error']}",
                payload=data,
            )

        video_id = data.get("id") or data.get("video_id") or ""
        post_id = data.get("post_id")
        permalink = self._resolve_permalink(video_id) if video_id else None

        return VideoUploadResult(
            video_id=video_id,
            post_id=post_id,
            permalink=permalink,
            description=clean_desc,
            bytes_uploaded=size,
            dry_run=False,
            debug={"response": data},
        )

    def _resolve_permalink(self, video_id: str) -> str | None:
        try:
            qs = urlencode({"fields": "permalink_url", "access_token": self.page_token})
            url = f"https://graph.facebook.com/{self.graph_version}/{video_id}?{qs}"
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            link = data.get("permalink_url")
            if link and link.startswith("/"):
                return f"https://www.facebook.com{link}"
            return link
        except Exception:
            return None

    @staticmethod
    def _sanitize_description(text: str) -> str:
        text = (text or "").strip()
        if len(text) > MAX_DESCRIPTION_CHARS:
            return text[: MAX_DESCRIPTION_CHARS - 1].rstrip() + "…"
        return text


def _encode_multipart(
    *,
    boundary: str,
    text_fields: dict[str, str],
    file_field: tuple[str, Path],
) -> tuple[bytes, str]:
    """Tiny hand-rolled multipart/form-data encoder.

    Why not use ``requests``? Sticking to stdlib keeps the publish module
    in line with ``dashboard/app.py`` and avoids adding a new dependency.

    Returns ``(body_bytes, content_type)``.
    """
    crlf = b"\r\n"
    parts: list[bytes] = []
    boundary_bytes = boundary.encode("ascii")

    for name, value in text_fields.items():
        parts.append(b"--" + boundary_bytes + crlf)
        parts.append(
            f'Content-Disposition: form-data; name="{name}"'.encode("utf-8") + crlf + crlf
        )
        parts.append(str(value).encode("utf-8") + crlf)

    field_name, path = file_field
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    parts.append(b"--" + boundary_bytes + crlf)
    parts.append(
        (
            f'Content-Disposition: form-data; name="{field_name}"; filename="{path.name}"'
        ).encode("utf-8")
        + crlf
    )
    parts.append(f"Content-Type: {mime}".encode("utf-8") + crlf + crlf)
    parts.append(path.read_bytes())
    parts.append(crlf)
    parts.append(b"--" + boundary_bytes + b"--" + crlf)

    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def credentials_from_env() -> dict[str, str]:
    """Read Page ID / token / version from the conventional env vars."""
    page_id = os.environ.get("META_PAGE_ID", "").strip()
    token = os.environ.get("META_PAGE_TOKEN", "").strip()
    version = os.environ.get("META_GRAPH_VERSION", DEFAULT_GRAPH_VERSION).strip() or DEFAULT_GRAPH_VERSION
    missing = [k for k, v in {"META_PAGE_ID": page_id, "META_PAGE_TOKEN": token}.items() if not v]
    if missing:
        sys.exit(
            "missing required env var(s): "
            + ", ".join(missing)
            + " (see publish/README.md for how to mint a long-lived Page token)"
        )
    return {"page_id": page_id, "page_token": token, "graph_version": version}
