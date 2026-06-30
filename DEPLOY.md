# CineMon Download Server — Deploy Guide

## What this is

A Python server that runs yt-dlp + ffmpeg.
Deploy it once on Railway (free) → paste the URL into index.html → done.
Download button works for everyone, forever, on any device, no setup needed.

---

## Step 1 — Deploy to Railway (5 minutes, free)

1. Go to https://railway.app and sign up (free)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
   - OR click **"New Project"** → **"Empty Project"** → **"Add Service"** → **"GitHub Repo"**
3. Push the `cinemon-server` folder to a GitHub repo
   (or use Railway's drag-and-drop deploy — see Step 1b below)
4. Railway auto-detects Python + installs ffmpeg + yt-dlp from `nixpacks.toml`
5. Click **"Deploy"** — wait ~2 minutes
6. Go to **Settings → Networking → Generate Domain**
7. Copy your URL, e.g. `https://cinemon-abc123.up.railway.app`

### Step 1b — Deploy without GitHub (drag & drop)

1. Go to https://railway.app → New Project → Deploy from local directory
2. Drag the entire `cinemon-server` folder into the upload area
3. Railway builds and deploys automatically

---

## Step 2 — Update index.html

Open `index.html` and find this line near the top of the `<script>`:

```javascript
const DL_PROXY = 'https://YOUR-APP.up.railway.app/download';
```

Replace `YOUR-APP` with your actual Railway subdomain. Save the file.

---

## Step 3 — Done

Open CineMon, play any video, press **1080p** or **720p**.
The server extracts the real stream using yt-dlp and pipes the MP4 to your browser.

---

## Keep yt-dlp updated on Railway

yt-dlp needs updates when sites change their encryption (roughly monthly).
Railway redeploys automatically when you push to GitHub — just run:

```
yt-dlp -U   ← updates requirements.txt automatically
git add . && git commit -m "update yt-dlp" && git push
```

Or on Railway dashboard: **Deployments → Redeploy** (fetches latest yt-dlp).

---

## File structure

```
cinemon-server/
├── server.py         ← Python download server (the main file)
├── index.html        ← CineMon app (edit DL_PROXY here)
├── requirements.txt  ← Python deps (yt-dlp)
├── nixpacks.toml     ← Railway build config (installs ffmpeg + yt-dlp)
├── railway.json      ← Railway deployment config
└── DEPLOY.md         ← This file
```

---

## Test the server

After deploy, open this in your browser:

```
https://YOUR-APP.up.railway.app/health
```

Should show: `{"status":"ok","service":"CineMon Download Server"}`

Test a download directly:
```
https://YOUR-APP.up.railway.app/download?id=27205&type=movie&quality=1080p&title=Inception
```

Should start downloading a file.

---

## Troubleshooting

**Download fails with "Could not extract stream"**
→ yt-dlp may be outdated — redeploy on Railway to get latest version
→ Try switching video source in CineMon (VidSrc.cc works best)

**Server not responding**
→ Check Railway dashboard → Logs for errors
→ Free tier sleeps after inactivity — first request takes ~5 seconds to wake up

**Download starts but file is broken**
→ ffmpeg may have failed to mux — check Railway logs
→ Try 720p instead of 1080p (smaller, more reliable)

---

## Railway free tier limits

- 500 hours/month compute (enough for personal use)
- $5 free credit monthly
- No credit card needed to start
- Server sleeps after 30min inactivity (wakes in ~5s on next request)
