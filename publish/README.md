# `publish/` — auto-publish generated Shorts to your Facebook Page

This module closes the loop:

```
shorts/ → MP4 → publish/ → Facebook Page → dashboard/ measures earnings
```

Two upload paths are supported:

| File | API | When to use |
| --- | --- | --- |
| `publish/fb_reels.py` | `/{page-id}/video_reels` (3-phase resumable) | The default. Posts as a native Reel so it shows in the Reels tab and is eligible for the Reels Play bonus where available. |
| `publish/fb_video.py` | `/{page-id}/videos` (multipart) | Simpler one-shot upload. Vertical 9:16 video posted this way is also indexed into Reels by Meta on most surfaces. |

Both clients use only the Python standard library — no `requests`, no SDK, same approach as `dashboard/app.py`.

---

## Quick start

```bash
# 1. Render a Short (or use one you already generated):
python3 shorts/pipeline.py --topic "5 subscriptions to cancel today" --seed 42

# 2. Dry-run the upload — no Meta calls, just prints the request that WOULD be made:
python3 -m publish.cli \
    --short shorts/output/2026-05-27/5-subscriptions-to-cancel-today \
    --as reels --dry-run

# 3. Set up credentials (see "Token setup" below), then upload for real:
export META_PAGE_ID=123456789012345
export META_PAGE_TOKEN=EAAG...
python3 -m publish.cli \
    --short shorts/output/2026-05-27/5-subscriptions-to-cancel-today \
    --as reels
```

Or chain it straight onto the shorts pipeline:

```bash
python3 shorts/pipeline.py --topic "..." --publish-fb reels
python3 shorts/pipeline.py --from-scraper --limit 5 --publish-fb reels  # batch!
python3 shorts/pipeline.py --topic "..." --publish-fb reels --publish-dry-run  # safe test
```

---

## Token setup (one-time, ~10 minutes)

You need a **long-lived Page access token** with these scopes:

- `pages_manage_posts`
- `pages_read_engagement`
- `pages_show_list`
- `publish_video`

The fastest, no-dev-app route:

1. Open the [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/).
2. Top-right → "User or Page" → **Get Page Access Token** → pick your CM-tools-enabled Page.
3. Click "Add permissions" and tick the four scopes above.
4. Click **Generate Access Token**. This is a *short-lived* (1-hour) token.
5. Exchange it for a *long-lived* (60-day) Page token:

   ```bash
   APP_ID=…   # from your Meta app dashboard
   APP_SECRET=…
   SHORT_TOKEN=…  # the one you just generated

   # Step A: short user token  ->  long user token
   curl -sG "https://graph.facebook.com/v19.0/oauth/access_token" \
       --data-urlencode "grant_type=fb_exchange_token" \
       --data-urlencode "client_id=$APP_ID" \
       --data-urlencode "client_secret=$APP_SECRET" \
       --data-urlencode "fb_exchange_token=$SHORT_TOKEN"
   # -> {"access_token":"<LONG_USER_TOKEN>", ...}

   # Step B: long user token  ->  Page token (no expiry as long as user token is valid)
   curl -sG "https://graph.facebook.com/v19.0/me/accounts" \
       --data-urlencode "access_token=<LONG_USER_TOKEN>"
   # -> { "data": [ { "id": "<PAGE_ID>", "access_token": "<LONG_PAGE_TOKEN>", ... } ] }
   ```

6. Copy `<PAGE_ID>` into `META_PAGE_ID` and `<LONG_PAGE_TOKEN>` into `META_PAGE_TOKEN`. Add them to your shell profile or a `.env` file (do **not** commit them):

   ```bash
   # ~/.bashrc
   export META_PAGE_ID=123456789012345
   export META_PAGE_TOKEN=EAAG...
   export META_GRAPH_VERSION=v19.0   # optional
   ```

7. Verify with a dry-run first:

   ```bash
   python3 -m publish.cli --short shorts/output/<date>/<slug> --as reels --dry-run
   ```

8. Then do a real test post on a draft / test Page before pointing it at your main Page.

> **Tip:** the same `META_PAGE_ID` + `META_PAGE_TOKEN` are used by `dashboard/app.py`, so you only set them up once.

---

## What gets posted

By default the caption is taken from the `metadata.json` produced by `shorts/pipeline.py`:

- **Title line** — the script's hook (first sentence)
- **Disclaimer** — "Not financial advice. Educational only."
- **Hashtags** — the niche-specific tags from `script_gen.HASHTAG_BANK`

You can override with `--description "..."` if you want a custom caption per post.

---

## Failure modes worth knowing

- **`(#100) Tried accessing nonexisting field …`** — the token does not have the right Page scope. Re-mint with `publish_video` ticked.
- **`(#10) Application does not have permission for this action`** — your Meta app is in *Development* mode. Submit it for App Review or just use the system-user-token route for personal Page automation. For a personal Page that you admin, the long-lived Page token route above works without App Review.
- **`Upload error: invalid offset 0`** — the rupload endpoint received a 2nd retry. Re-run; the resumable session is idempotent within ~24h but the simplest fix is just to retry.
- **Reels under 3 seconds / over 90 seconds** — Reels API enforces a 3–90 s duration window. The `shorts/` pipeline produces 60–80 s by design so you should be fine.
- **Aspect ratio not 9:16** — Reels API rejects non-vertical content. `shorts/` always renders at 1080×1920.

---

## Files in this module

```
publish/
├── __init__.py
├── README.md            ← you are here
├── requirements.txt     ← intentionally empty (stdlib only)
├── fb_reels.py          ← FBReelsClient (resumable Reels upload)
├── fb_video.py          ← FBVideoClient (multipart classic Video upload)
└── cli.py               ← unified CLI (python -m publish.cli ...)
```
