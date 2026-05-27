"""Auto-publish helpers for Facebook Page Reels and Videos.

This module closes the loop between the `shorts/` pipeline (which produces
ready-to-upload MP4s) and the Facebook Page where you actually monetize.

Sub-modules:

* :mod:`publish.fb_reels` — uploads via the **Reels API** (resumable upload
  to Meta's rupload endpoint). This is the API to use for short-form
  vertical content that should appear in the dedicated Reels feed and be
  eligible for the Reels Play bonus where available.
* :mod:`publish.fb_video` — uploads via the **classic Videos API**
  (multipart upload to ``/{page-id}/videos``). Use this for content that
  should appear as a regular Page video (also gets indexed into Reels if
  the aspect ratio is vertical).
* :mod:`publish.cli` — single command-line entry point that picks the
  right API based on flags and your folder layout.

All modules use ``urllib`` from the standard library (no ``requests``
dependency) so the publish module installs zero extra packages — same
approach as ``dashboard/app.py``.

Required token scopes (see ``publish/README.md``):

* ``pages_manage_posts``
* ``pages_read_engagement``
* ``pages_show_list``
* ``publish_video``
"""

from publish.fb_reels import FBReelsClient, ReelsUploadResult  # noqa: F401
from publish.fb_video import FBVideoClient, VideoUploadResult  # noqa: F401
