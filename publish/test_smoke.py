"""Tiny smoke test for the publish module.

Runs a fully *offline* end-to-end exercise of both client classes by
monkey-patching ``urllib.request.urlopen`` to return canned Meta-style
responses. Validates that:

* The 3-phase Reels flow makes exactly 3 (or 4 incl. permalink) HTTP calls
  in the right order with the right query params.
* The classic Videos flow builds a well-formed multipart body.
* Dry-run mode short-circuits and makes zero network calls.

Run::

    python3 publish/test_smoke.py
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

# Allow `python publish/test_smoke.py` (without -m) from the repo root.
THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publish.fb_reels import FBReelsClient  # noqa: E402
from publish.fb_video import FBVideoClient, _encode_multipart  # noqa: E402


def _fake_response(payload: dict) -> mock.MagicMock:
    """Return a context-manager-shaped mock that mimics ``urlopen()``."""
    body = json.dumps(payload).encode("utf-8")
    resp = mock.MagicMock()
    resp.read.return_value = body
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def _make_dummy_mp4() -> Path:
    """Create a tiny placeholder .mp4 so size + path logic exercises."""
    tmp = Path(tempfile.mkstemp(suffix=".mp4")[1])
    tmp.write_bytes(b"\x00" * 1024)
    return tmp


class ReelsClientTest(unittest.TestCase):
    def test_dry_run_makes_no_network_calls(self):
        mp4 = _make_dummy_mp4()
        try:
            client = FBReelsClient(
                page_id="123",
                page_token="token-abc",
                dry_run=True,
                verbose=False,
            )
            with mock.patch("publish.fb_reels.urlopen") as opener:
                result = client.publish(mp4, description="hello world")
            self.assertEqual(opener.call_count, 0)
            self.assertTrue(result.dry_run)
            self.assertEqual(result.video_id, "DRY_RUN_VIDEO_ID")
            self.assertEqual(result.description, "hello world")
        finally:
            mp4.unlink(missing_ok=True)

    def test_three_phase_upload(self):
        mp4 = _make_dummy_mp4()
        try:
            client = FBReelsClient(
                page_id="42",
                page_token="tok",
                dry_run=False,
                verbose=False,
            )

            responses = iter([
                _fake_response({"video_id": "VID_99", "upload_url": "https://rupload.facebook.com/abc"}),
                _fake_response({"success": True}),  # binary upload reply
                _fake_response({"success": True}),  # finish
                _fake_response({"permalink_url": "/MoneyHabits/videos/VID_99/"}),  # permalink resolve
            ])
            called_urls: list[str] = []

            def fake_open(req, timeout=None):  # noqa: ARG001
                called_urls.append(req.get_full_url() if hasattr(req, "get_full_url") else str(req))
                return next(responses)

            with mock.patch("publish.fb_reels.urlopen", side_effect=fake_open):
                result = client.publish(mp4, description="hi #money")

            self.assertEqual(len(called_urls), 4)
            self.assertIn("upload_phase=start", called_urls[0])
            self.assertEqual(called_urls[1], "https://rupload.facebook.com/abc")
            self.assertIn("upload_phase=finish", called_urls[2])
            self.assertIn("video_state=PUBLISHED", called_urls[2])
            self.assertEqual(result.video_id, "VID_99")
            self.assertEqual(result.permalink, "https://www.facebook.com/MoneyHabits/videos/VID_99/")
        finally:
            mp4.unlink(missing_ok=True)

    def test_description_truncated(self):
        mp4 = _make_dummy_mp4()
        try:
            client = FBReelsClient(
                page_id="1",
                page_token="t",
                dry_run=True,
                verbose=False,
            )
            big = "x" * 5000
            result = client.publish(mp4, description=big)
            self.assertLess(len(result.description), 2200)
            self.assertTrue(result.description.endswith("\u2026"))
        finally:
            mp4.unlink(missing_ok=True)


class VideoClientTest(unittest.TestCase):
    def test_multipart_encoder_round_trip(self):
        mp4 = _make_dummy_mp4()
        try:
            body, content_type = _encode_multipart(
                boundary="testbnd",
                text_fields={"description": "hello", "access_token": "tok"},
                file_field=("source", mp4),
            )
            self.assertIn(b"name=\"description\"", body)
            self.assertIn(b"name=\"access_token\"", body)
            self.assertIn(b"name=\"source\"", body)
            self.assertTrue(content_type.startswith("multipart/form-data;"))
            self.assertIn("boundary=testbnd", content_type)
            # The file payload must be included.
            self.assertIn(mp4.read_bytes(), body)
        finally:
            mp4.unlink(missing_ok=True)

    def test_dry_run(self):
        mp4 = _make_dummy_mp4()
        try:
            client = FBVideoClient(
                page_id="9",
                page_token="t",
                dry_run=True,
                verbose=False,
            )
            with mock.patch("publish.fb_video.urlopen") as opener:
                result = client.publish(mp4, description="caption", title="Title")
            self.assertEqual(opener.call_count, 0)
            self.assertTrue(result.dry_run)
        finally:
            mp4.unlink(missing_ok=True)

    def test_real_upload_path(self):
        mp4 = _make_dummy_mp4()
        try:
            client = FBVideoClient(
                page_id="9",
                page_token="t",
                dry_run=False,
                verbose=False,
            )
            responses = iter([
                _fake_response({"id": "V_1", "post_id": "9_777"}),
                _fake_response({"permalink_url": "/page/videos/V_1/"}),
            ])

            def fake_open(req, timeout=None):  # noqa: ARG001
                return next(responses)

            with mock.patch("publish.fb_video.urlopen", side_effect=fake_open):
                result = client.publish(mp4, description="hi")

            self.assertEqual(result.video_id, "V_1")
            self.assertEqual(result.post_id, "9_777")
            self.assertEqual(result.permalink, "https://www.facebook.com/page/videos/V_1/")
        finally:
            mp4.unlink(missing_ok=True)


def main() -> None:
    # Use a stdout-friendly test runner so failures are easy to spot.
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
