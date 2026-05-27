"""Facebook **Reels API** uploader for Page-owned vertical short videos.

This is the API to use for vertical short-form video that should show up
in the Reels tab of the Facebook app and be eligible for the Reels Play
bonus (where available in the creator's country).

Flow (see https://developers.facebook.com/docs/video-api/guides/reels-publishing):

1. **Start an upload session.**
   ``POST /{api}/{page-id}/video_reels?upload_phase=start&access_token=…``
   Returns ``{"video_id": "...", "upload_url": "https://rupload.facebook.com/..."}``.

2. **Upload the file binary.**
   ``POST <upload_url>``
   Headers: ``Authorization: OAuth <page-token>``,
            ``offset: 0``,
            ``file_size: <bytes>``.
   Body: the raw bytes of the .mp4 file.

3. **Finish the session and publish.**
   ``POST /{api}/{page-id}/video_reels?upload_phase=finish&video_id=…
       &video_state=PUBLISHED&description=…&access_token=…``

This module wraps all three steps in :class:`FBReelsClient.publish`.

A ``--dry-run`` mode is provided so the entire pipeline can be exercised
end-to-end without actually posting anything. Use it the first time you
hook a new token up.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_GRAPH_VERSION = "v19.0"
GRAPH_BASE = "https://graph.facebook.com"
DEFAULT_TIMEOUT = 60  # seconds — file upload may take a while

# Meta caps Reels descriptions at 2200 chars including hashtags. We leave a
# little headroom for trailing whitespace and our footer.
MAX_DESCRIPTION_CHARS = 2150


@dataclass
class ReelsUploadResult:
    video_id: str
    permalink: str | None
    description: str
    bytes_uploaded: int
    dry_run: bool
    debug: dict[str, Any] = field(default_factory=dict)


class FBReelsAPIError(RuntimeError):
    """Raised when Meta returns a non-success response."""

    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload or {}


class FBReelsClient:
    """Lightweight Reels uploader using only the Python standard library."""

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [reels] {msg}", flush=True)

    def _graph_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        qs = urlencode({k: v for k, v in (query or {}).items() if v is not None})
        url = f"{GRAPH_BASE}/{self.graph_version}/{path.lstrip('/')}"
        if qs:
            url = f"{url}?{qs}"
        return url

    def _post_form(self, url: str) -> dict[str, Any]:
        """POST with no body — used for the start/finish phases."""
        req = Request(url, data=b"", method="POST", headers={"Accept": "application/json"})
        with urlopen(req, timeout=self.timeout) as resp:
            body = resp.read().decode("utf-8")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            raise FBReelsAPIError(f"non-JSON response from Meta: {body[:200]!r}")
        if "error" in data:
            raise FBReelsAPIError(
                f"Meta API error: {data['error'].get('message') or data['error']}",
                payload=data,
            )
        return data

    def _upload_binary(self, upload_url: str, mp4_path: Path) -> dict[str, Any]:
        size = mp4_path.stat().st_size
        self._log(f"uploading {size:,} bytes to {upload_url.split('?', 1)[0]}")
        with mp4_path.open("rb") as f:
            data = f.read()
        req = Request(
            upload_url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"OAuth {self.page_token}",
                "offset": "0",
                "file_size": str(size),
                "Content-Type": "application/octet-stream",
            },
        )
        with urlopen(req, timeout=self.timeout * 5) as resp:
            body = resp.read().decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"raw": body[:200]}
        if isinstance(payload, dict) and "error" in payload:
            raise FBReelsAPIError(
                f"binary upload failed: {payload['error'].get('message') or payload['error']}",
                payload=payload,
            )
        return payload

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish(
        self,
        mp4_path: Path,
        *,
        description: str = "",
        thumbnail_offset_ms: int | None = None,
        wait_for_processing: bool = False,
        max_wait_seconds: int = 180,
    ) -> ReelsUploadResult:
        """Upload ``mp4_path`` and publish it as a Reel on the Page.

        :param description: caption + hashtags (truncated at ~2200 chars).
        :param thumbnail_offset_ms: seek-time used as the auto-thumbnail.
        :param wait_for_processing: poll ``/{video-id}?fields=status`` until
            Meta reports ``ready`` before returning. Useful when chaining
            multiple uploads.
        """
        mp4_path = Path(mp4_path).resolve()
        if not mp4_path.exists():
            raise FileNotFoundError(f"no such file: {mp4_path}")
        if mp4_path.suffix.lower() != ".mp4":
            raise ValueError(f"reels API requires .mp4, got {mp4_path.suffix}")

        size = mp4_path.stat().st_size
        clean_desc = self._sanitize_description(description)

        if self.dry_run:
            self._log("DRY RUN — no Meta calls will be made")
            self._log(f"would upload: {mp4_path}")
            self._log(f"size:         {size:,} bytes")
            self._log(f"description:  {clean_desc[:160]}{'…' if len(clean_desc) > 160 else ''}")
            self._log(f"page id:      {self.page_id}")
            self._log("phases:       start → rupload binary → finish (PUBLISHED)")
            return ReelsUploadResult(
                video_id="DRY_RUN_VIDEO_ID",
                permalink=None,
                description=clean_desc,
                bytes_uploaded=size,
                dry_run=True,
                debug={"phases": ["start", "rupload", "finish"]},
            )

        # ---- phase 1: start
        self._log("starting upload session …")
        start = self._post_form(
            self._graph_url(
                f"{self.page_id}/video_reels",
                {"upload_phase": "start", "access_token": self.page_token},
            )
        )
        video_id = start.get("video_id")
        upload_url = start.get("upload_url")
        if not video_id or not upload_url:
            raise FBReelsAPIError(
                "start phase did not return video_id/upload_url",
                payload=start,
            )
        self._log(f"got video_id={video_id}")

        # ---- phase 2: upload binary
        self._upload_binary(upload_url, mp4_path)

        # ---- phase 3: finish
        finish_q: dict[str, Any] = {
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": clean_desc,
            "access_token": self.page_token,
        }
        if thumbnail_offset_ms is not None:
            finish_q["thumb_offset"] = thumbnail_offset_ms
        self._log("finishing upload session and publishing …")
        finish = self._post_form(self._graph_url(f"{self.page_id}/video_reels", finish_q))
        if not finish.get("success", True):
            raise FBReelsAPIError("Meta returned success=false on finish phase", payload=finish)

        permalink = self._resolve_permalink(video_id)
        if wait_for_processing:
            self._wait_for_ready(video_id, max_wait_seconds=max_wait_seconds)

        return ReelsUploadResult(
            video_id=video_id,
            permalink=permalink,
            description=clean_desc,
            bytes_uploaded=size,
            dry_run=False,
            debug={"start": start, "finish": finish},
        )

    # ------------------------------------------------------------------
    # Helpers used after the upload
    # ------------------------------------------------------------------

    def _resolve_permalink(self, video_id: str) -> str | None:
        """Ask the Graph for the public permalink. Failure here is non-fatal."""
        try:
            url = self._graph_url(
                video_id,
                {"fields": "permalink_url", "access_token": self.page_token},
            )
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            link = data.get("permalink_url")
            if link and link.startswith("/"):
                return f"https://www.facebook.com{link}"
            return link
        except Exception:
            return None

    def _wait_for_ready(self, video_id: str, *, max_wait_seconds: int) -> None:
        deadline = time.monotonic() + max_wait_seconds
        while time.monotonic() < deadline:
            try:
                url = self._graph_url(
                    video_id,
                    {"fields": "status", "access_token": self.page_token},
                )
                req = Request(url, headers={"Accept": "application/json"})
                with urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                state = (data.get("status") or {}).get("video_status")
                self._log(f"processing state: {state}")
                if state == "ready":
                    return
            except Exception as exc:  # noqa: BLE001
                self._log(f"status check failed (will retry): {exc}")
            time.sleep(5)
        self._log("timed out waiting for processing — proceeding anyway")

    @staticmethod
    def _sanitize_description(text: str) -> str:
        text = (text or "").strip()
        if len(text) > MAX_DESCRIPTION_CHARS:
            return text[: MAX_DESCRIPTION_CHARS - 1].rstrip() + "…"
        return text


# ---------------------------------------------------------------------------
# Helpers for callers that want to load credentials from the standard places
# ---------------------------------------------------------------------------


def credentials_from_env() -> dict[str, str]:
    """Read Page ID / token / version from the conventional env vars.

    Same vars used by ``dashboard/app.py``. Raises ``SystemExit`` if the
    required ones are missing (so CLIs can call this directly).
    """
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
