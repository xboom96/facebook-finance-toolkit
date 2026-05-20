# How to get a Facebook Page Access Token

The dashboard needs a **Page Access Token** with `read_insights` + `pages_read_engagement` permissions. Here's the fastest path.

## 1. Create a Meta Developer App (one-time)

1. Go to <https://developers.facebook.com/apps/>.
2. Click **Create App** → choose **Business** → click **Next**.
3. App name: `MoneyDashboard` (any name works) → **Create app**.
4. You'll land on the app dashboard. Note the **App ID** at the top — you'll see it as `App ID: 123456789012345`.

## 2. Get a User Access Token via the Graph API Explorer

1. Open <https://developers.facebook.com/tools/explorer/>.
2. In the top-right, select your app from the **Meta App** dropdown.
3. Click **User or Page** → **Get User Access Token**.
4. In the permissions popup, add these scopes (use the search box):
   - `pages_show_list`
   - `pages_read_engagement`
   - `read_insights`
5. Click **Generate Access Token** → log in with the Facebook account that **admins your page**.
6. After approval, the **Access Token** field is populated. This is a *short-lived user token* — we'll convert it next.

## 3. Convert to a long-lived Page Access Token

A user token expires in ~1 hour. A page token derived from it never expires (as long as the user doesn't revoke).

In the Graph API Explorer, run these GET calls (just paste them in the URL bar of the explorer and hit Submit):

**Step 3a — Get long-lived USER token** (in your terminal, not the explorer):

```bash
APP_ID="YOUR_APP_ID"
APP_SECRET="YOUR_APP_SECRET"   # find in App Dashboard → Settings → Basic
SHORT_USER_TOKEN="paste_from_step_2"

curl -G "https://graph.facebook.com/v19.0/oauth/access_token" \
  --data-urlencode "grant_type=fb_exchange_token" \
  --data-urlencode "client_id=$APP_ID" \
  --data-urlencode "client_secret=$APP_SECRET" \
  --data-urlencode "fb_exchange_token=$SHORT_USER_TOKEN"
```

You get back `{"access_token":"...","expires_in":5183999}` — that's ~60 days.

**Step 3b — Exchange for a permanent PAGE token:**

```bash
LONG_USER_TOKEN="paste_from_step_3a"

curl -G "https://graph.facebook.com/v19.0/me/accounts" \
  --data-urlencode "access_token=$LONG_USER_TOKEN"
```

Response:

```json
{
  "data": [
    {
      "access_token": "EAAB...verylongstring...",
      "name": "Your Page Name",
      "id": "123456789012345",
      "category": "Personal Blog"
    }
  ]
}
```

The `access_token` here is the **Page Access Token** and it does **not expire** (as long as your password isn't changed and permissions aren't revoked). The `id` is your **Page ID**.

## 4. (Alternative, easier) Use the System User token in Business Manager

If you have Meta Business Manager:

1. <https://business.facebook.com/> → **Business Settings** → **Users** → **System Users**.
2. **Add** → name it `MoneyDashboard SU` → role `Admin`.
3. Open the system user → **Add Assets** → select your Page → permission `Manage Page`.
4. Click **Generate New Token** → app: your dev app → permissions: `pages_read_engagement`, `read_insights`, `pages_show_list` → **Generate Token**.

This token also doesn't expire. Paste it into the dashboard's setup screen along with your Page ID.

## 5. Validate the token

```bash
PAGE_ID="123456789012345"
PAGE_TOKEN="EAAB..."

curl -G "https://graph.facebook.com/v19.0/$PAGE_ID" \
  --data-urlencode "fields=name,fan_count,followers_count" \
  --data-urlencode "access_token=$PAGE_TOKEN"
```

If you see your page's name and follower count, you're done.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `(#100) Tried accessing nonexisting field "insights"` | Token is missing `read_insights`. Re-grant the scope. |
| `(#10) (#10) Application does not have permission for this action` | Your app is in Development mode. Move to **Live mode** in App Dashboard (no review needed for read-only insights on your own page). |
| `(#190) Error validating access token` | Token expired or was generated for a different page. Regenerate via step 3b. |
| `Session has expired` after a day | You used a short-lived user token instead of a page token. Repeat step 3. |

## Where to plug the token into the dashboard

Either:

- **Web form** — visit `http://127.0.0.1:5000/setup` and paste it in (recommended for local use), or
- **Env vars** — `export META_PAGE_ID=...` and `export META_PAGE_TOKEN=...` and modify `dashboard/app.py` to pull from env (already supported as defaults).

Your token is stored only in the Flask session cookie on your own machine. Never commit it to git.
