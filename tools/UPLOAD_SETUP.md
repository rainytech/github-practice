# YouTube upload script: one-time setup

The script is `tools/upload_youtube.py`. Run it on your own PC (Windows is fine). It is free: the YouTube Data API v3 gives 10,000 units a day, and since November 2026 each call costs 1 unit (Google's reply of 23 Nov 2026), so the free quota is far more than enough.

## 1. Install Python and the libraries
1. Install Python 3 from python.org (tick "Add Python to PATH").
2. In a terminal opened in the repository folder:

```bash
pip install google-api-python-client google-auth-oauthlib
```

## 2. Create the Google Cloud project
1. Open https://console.cloud.google.com/ and sign in with the channel's Google account.
2. Click the project picker at the top, then **New project**, and name it "Goodwill YouTube Upload".
3. Go to **APIs & Services → Library**, search for **YouTube Data API v3**, and click **Enable**.

## 3. Create the OAuth login file
1. Go to **APIs & Services → OAuth consent screen**: choose **External**, fill in the app name and your email, and save. Under **Test users** (or **Audience**), add the channel's Gmail.
2. Go to **APIs & Services → Credentials → Create credentials → OAuth client ID**, then choose **Desktop app**.
3. Download the JSON file, rename it `client_secret.json`, and put it in the `tools/` folder. It is git-ignored, so it is never committed.

## 4. First run
Check the files first; nothing is uploaded:

```bash
python tools/upload_youtube.py videos/mgu-cost-q13 --dry-run
```

Then upload for real:

```bash
python tools/upload_youtube.py videos/<project>
```

The first time, the browser opens: choose the channel account and allow access. The login is then saved in `~/.goodwill_youtube_token.json`.

## 5. No audit needed
Google confirmed on 23 Nov 2026 that videos uploaded through the API are no longer locked as private, so Public uploads work straight away. (We submitted the audit form on 22 Nov; Google closed it as not needed.)

## Per-project settings (optional)
`videos/<project>/upload/settings.json`:

```json
{ "playlist": "MGU B.Com Hons Sem 6 · Cost Accounting", "privacy": "public" }
```

## Still manual in Studio
The Education fields (Type, Level, Exam) and the pinned comment.
