"""
CineMon Download Server — Local PC Edition
==========================================
Run start.bat to launch.
Access on this PC:    http://localhost:8080
Access on phone/TV:   http://YOUR-LOCAL-IP:8080
"""

import os, sys, subprocess, shutil, urllib.parse, json
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))

# ── Check tools ───────────────────────────────────────────────────────────────
def check_tools():
    ok = True
    if not shutil.which("yt-dlp"):
        print("[setup] yt-dlp not found — installing via pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yt-dlp"])
    if not shutil.which("ffmpeg"):
        print("[warn] ffmpeg not found in PATH.")
        print("       HLS streams won't merge properly without it.")
        print("       Download: https://www.gyan.dev/ffmpeg/builds/")
        print("       Place ffmpeg.exe in C:\\tools\\ and add C:\\tools to PATH")
    print(f"[ok] yt-dlp : {shutil.which('yt-dlp') or 'NOT FOUND'}")
    print(f"[ok] ffmpeg : {shutil.which('ffmpeg') or 'NOT FOUND (HLS merge disabled)'}")
    return ok

check_tools()

# ── Embed URL builders ────────────────────────────────────────────────────────
def build_embed_urls(tmdb_id, ctype, season=1, episode=1):
    s, e = season, episode
    if ctype == "movie":
        return [
            f"https://vidsrc.cc/v2/embed/movie/{tmdb_id}",
            f"https://vidlink.pro/movie/{tmdb_id}",
            f"https://vidsrc.to/embed/movie/{tmdb_id}",
            f"https://embed.su/embed/movie/{tmdb_id}",
            f"https://autoembed.cc/movie/tmdb/{tmdb_id}",
            f"https://www.2embed.cc/embed/{tmdb_id}",
        ]
    else:
        return [
            f"https://vidsrc.cc/v2/embed/tv/{tmdb_id}/{s}/{e}",
            f"https://vidlink.pro/tv/{tmdb_id}/{s}/{e}",
            f"https://vidsrc.to/embed/tv/{tmdb_id}/{s}/{e}",
            f"https://embed.su/embed/tv/{tmdb_id}/{s}/{e}",
            f"https://autoembed.cc/tv/tmdb/{tmdb_id}-{s}-{e}",
        ]

# ── yt-dlp extraction ─────────────────────────────────────────────────────────
def ytdlp_extract(page_url, quality="1080"):
    fmt = (
        f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]"
        f"/bestvideo[height<={quality}]+bestaudio"
        f"/best[height<={quality}]/best"
    )
    cmd = [
        "yt-dlp",
        "--get-url",
        "--no-warnings",
        "--no-playlist",
        "--format", fmt,
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "--add-header", "Referer:https://vidsrc.to/",
        "--socket-timeout", "20",
        page_url,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        lines = [l.strip() for l in r.stdout.strip().splitlines() if l.strip().startswith("http")]
        if not lines:
            return None
        return {"video": lines[0], "audio": lines[1] if len(lines) >= 2 else None}
    except Exception as ex:
        print(f"[yt-dlp] {ex}")
        return None

# ── seapi.link fallback ───────────────────────────────────────────────────────
def seapi_extract(tmdb_id, ctype, season, episode, quality):
    import urllib.request
    if ctype == "movie":
        url = f"https://seapi.link/?type=tmdb&id={tmdb_id}&max_results=10"
    else:
        url = f"https://seapi.link/?type=tmdb&id={tmdb_id}&season={season}&episode={episode}&max_results=10"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        streams = data.get("streams") or data.get("results") or (data if isinstance(data, list) else [])
        target = int(quality)
        def qnum(s):
            q = s.get("quality") or s.get("resolution") or "0"
            return int("".join(c for c in q if c.isdigit()) or "0")
        mp4s = [s for s in streams if ".m3u8" not in (s.get("stream") or s.get("url") or "")]
        pool = mp4s or streams
        best = min(pool, key=lambda s: abs(target - qnum(s)), default=None)
        if not best:
            return None
        u = best.get("stream") or best.get("url") or best.get("link")
        return {"video": u, "audio": None} if u else None
    except Exception as ex:
        print(f"[seapi] {ex}")
        return None

# ── ffmpeg pipe ───────────────────────────────────────────────────────────────
def ffmpeg_pipe(wfile, video_url, audio_url=None):
    has_ffmpeg = bool(shutil.which("ffmpeg"))

    if not has_ffmpeg:
        # No ffmpeg — pipe the video URL directly (works for direct MP4s)
        import urllib.request
        req = urllib.request.Request(video_url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://vidsrc.to/"
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            while True:
                chunk = r.read(131072)
                if not chunk:
                    break
                wfile.write(chunk)
        return

    if audio_url:
        cmd = ["ffmpeg", "-i", video_url, "-i", audio_url,
               "-c:v", "copy", "-c:a", "aac",
               "-movflags", "frag_keyframe+empty_moov+faststart",
               "-f", "mp4", "pipe:1"]
    else:
        cmd = ["ffmpeg", "-i", video_url,
               "-c", "copy",
               "-movflags", "frag_keyframe+empty_moov+faststart",
               "-f", "mp4", "pipe:1"]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        while True:
            chunk = proc.stdout.read(131072)
            if not chunk:
                break
            wfile.write(chunk)
    finally:
        proc.kill()

# ── HTTP Request Handler ──────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {args[0]} → {args[1]}")

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # ── Serve index.html ──────────────────────────────────────────────────
        if parsed.path in ("/", "/index.html"):
            here = os.path.dirname(os.path.abspath(__file__))
            fpath = os.path.join(here, "index.html")
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"index.html not found next to server.py")
            return

        # ── Health check ──────────────────────────────────────────────────────
        if parsed.path == "/health":
            body = json.dumps({
                "status": "ok",
                "yt-dlp": bool(shutil.which("yt-dlp")),
                "ffmpeg": bool(shutil.which("ffmpeg")),
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors()
            self.end_headers()
            self.wfile.write(body)
            return

        # ── Download endpoint ─────────────────────────────────────────────────
        if parsed.path != "/download":
            self.send_response(404)
            self.end_headers()
            return

        p        = urllib.parse.parse_qs(parsed.query)
        get      = lambda k, d="": p.get(k, [d])[0].strip()
        embed_url = get("embed_url")
        tmdb_id   = get("id")
        ctype     = get("type", "movie")
        quality   = "720" if get("quality") == "720p" else "1080"
        season    = int(get("season", "1") or "1")
        episode   = int(get("episode", "1") or "1")
        raw_title = get("title", "video")
        safe      = "".join(c if c.isalnum() or c in "_-" else "_" for c in raw_title)
        fname     = f"{safe}_{quality}p.mp4"

        if not embed_url and not tmdb_id:
            self._err(400, "Provide embed_url or id")
            return

        result = None

        # Strategy 1 — yt-dlp on the live embed URL playing right now
        if embed_url:
            print(f"[dl] yt-dlp → live iframe: {embed_url}")
            result = ytdlp_extract(embed_url, quality)

        # Strategy 2 — yt-dlp on all known embed URLs for this content
        if not result and tmdb_id:
            for url in build_embed_urls(tmdb_id, ctype, season, episode):
                print(f"[dl] yt-dlp → {url}")
                result = ytdlp_extract(url, quality)
                if result:
                    break

        # Strategy 3 — seapi.link
        if not result and tmdb_id:
            print(f"[dl] seapi.link fallback")
            result = seapi_extract(tmdb_id, ctype, season, episode, quality)

        if not result:
            self._err(404, "Could not extract stream from any source. Try a different video source in CineMon.")
            return

        print(f"[dl] Got stream → sending {fname}")
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_cors()
        self.end_headers()

        try:
            ffmpeg_pipe(self.wfile, result["video"], result.get("audio"))
        except (BrokenPipeError, ConnectionResetError):
            print("[dl] Client disconnected early.")
        except Exception as ex:
            print(f"[dl] Stream error: {ex}")

    def _err(self, code, msg):
        body = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

# ── Start ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import socket
    # Print all local IPs
    hostname = socket.gethostname()
    try:
        ips = socket.getaddrinfo(hostname, None)
        local_ips = list(set(i[4][0] for i in ips if not i[4][0].startswith("127") and ":" not in i[4][0]))
    except:
        local_ips = []

    print()
    print("=" * 50)
    print("  CineMon Download Server — LOCAL MODE")
    print("=" * 50)
    print(f"  This PC  : http://localhost:{PORT}")
    for ip in local_ips:
        print(f"  Network  : http://{ip}:{PORT}  ← open on phone/tablet")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    print()

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Stopped.")
