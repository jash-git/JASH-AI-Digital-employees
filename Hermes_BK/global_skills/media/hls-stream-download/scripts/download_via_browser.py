#!/usr/bin/env python3
"""Download HLS segments from a Cloudflare-protected video page (e.g. missav/surrit/fourhoi)
and merge to MP4. Uses a real headless Chromium (Playwright Async API) to solve the CDN's
JS challenge, then fetches each segment via the browser context and saves it as .ts.

Usage:
    python3 download_via_browser.py [--quality 720p] [--url MISSAV_URL] [--out ~/movie.mp4] [--daemon]

Progress is always written to /tmp/hls_dl_progress.log so a cron job or polling loop can read it.
Run with --daemon to double-fork (survives the terminal tool's ~420s foreground timeout).
"""
import os, sys, time, re, argparse, asyncio, base64, subprocess
from playwright.async_api import async_playwright

# ---- Configurable targets -------------------------------------------------
MISSAV_URL = "https://missav.ws/dsjh-017-uncensored-leak"   # page with the <video.player>
QUALITY    = "720p"                                         # 360p / 480p / 720p (highest first)
OUT_DIR    = "/tmp/hls_segs"
MP4        = os.path.expanduser("~/movie.mp4")
LOG        = "/tmp/hls_dl_progress.log"
CONCURRENCY = 10                                            # parallel fetch() per segment
MAX_RETRIES = 5

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

async def grab(page, idx):
    """Fetch one segment through the browser's fetch() (CF cookies already valid) and save .ts.
    Returns True on success."""
    b64 = await page.evaluate(f"""async()=>{{
        const resp = await fetch('{BASE}/{QUALITY}/video{idx}.jpeg');
        if(!resp.ok) return {{ok:false, status:resp.status}};
        const buf = await resp.arrayBuffer();
        const bytes = new Uint8Array(buf);
        let bin=''; for(let k=0;k<bytes.length;k++) bin+=String.fromCharCode(bytes[k]);
        return {{ok:true, b64: btoa(bin)}};
    }}""")
    if not b64 or not b64.get('ok'):
        return False
    with open(os.path.join(OUT_DIR, f"video{idx}.ts"), "wb") as f:
        f.write(base64.b64decode(b64['b64']))
    return True

async def main():
    global BASE
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.startswith("video"):
            os.remove(os.path.join(OUT_DIR, f))
    log(f"Started. Quality={QUALITY}, OUT_DIR={OUT_DIR}")

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            viewport={"width":1280,"height":900})
        page = await ctx.new_page()

        # 1) Load the missav page -> browser solves CF challenge, then fetches surrit CDN assets.
        log("Navigating to source page (establish CF context)...")
        await page.goto(MISSAV_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        # 2) Derive the surrit base + playlist from the network responses / master manifest.
        #    (Adapt BASE/PLAYLIST_URL to whatever CDN this site uses.)
        BASE = "https://surrit.com/02a9c462-cd17-4a58-b1bc-504fe5ccfa8a"  # <-- set per video
        PLAYLIST_URL = f"{BASE}/{QUALITY}/video.m3u8"

        seg_list = await page.evaluate(f"""async()=>{{
            const resp = await fetch('{PLAYLIST_URL}');
            const text = await resp.text();
            const durs = [...text.matchAll(/#EXTINF:([\\d.]+)/g)].map(m=>parseFloat(m[1]));
            const files = text.split('\\n').filter(l=>l && !l.startsWith('#'));
            return {{count: files.length, totalDur: durs.reduce((a,c)=>a+c,0)}};
        }}""")
        n = seg_list['count']
        log(f"Segment list: {n} segments, total ~{seg_list['totalDur']:.0f}s ({seg_list['totalDur']/60:.1f} min)")

        # 3) Download all segments in parallel batches.
        done = 0; failed = []; start = time.time()
        async def dl(idx):
            nonlocal done
            path = os.path.join(OUT_DIR, f"video{idx}.ts")
            if os.path.exists(path) and os.path.getsize(path) > 1000:
                return True
            for attempt in range(MAX_RETRIES):
                ok = await grab(page, idx)
                if ok and os.path.getsize(path) > 1000:
                    break
                await asyncio.sleep(2 + attempt)
            else:
                failed.append(idx); return False
            done += 1
            if done % 50 == 0 or done == n:
                el = time.time() - start; rate = done/el if el else 0
                log(f"Progress: {done}/{n} ({100*done/n:.1f}%) | {el/60:.1f}m elapsed | ~{(n-done)/rate:.0f}m left")
            return True

        sem = asyncio.Semaphore(CONCURRENCY)
        async def wrap(idx):
            async with sem: await dl(idx)
        await asyncio.gather(*[wrap(i) for i in range(n)])
        log(f"Download complete: {done} ok, {len(failed)} failed")
        if failed: log(f"Failed indices (first 30): {failed[:30]}")
        await b.close()

    # 4) Merge with ffmpeg (segments are MPEG-TS despite any .jpeg extension).
    log("Merging segments with ffmpeg...")
    list_file = os.path.join(OUT_DIR, "filelist.txt")
    ts_files = sorted([f for f in os.listdir(OUT_DIR) if f.endswith('.ts')],
                      key=lambda x: int(re.search(r'video(\d+)', x).group(1)))
    with open(list_file, 'w') as f:
        for tf in ts_files:
            f.write(f"file '{os.path.join(OUT_DIR, tf)}'\n")
    cmd = ["ffmpeg","-y","-f","concat","-safe","0","-i",list_file,
           "-c","copy","-movflags","+faststart", MP4]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        log(f"[OK] Merged MP4: {MP4} ({os.path.getsize(MP4)/(1024*1024):.0f} MB)")
    else:
        log(f"[FFMPEG ERROR]\n{r.stderr[-800:]}")

def daemonize():
    if os.fork() > 0: os._exit(0)
    os.setsid()
    if os.fork() > 0: os._exit(0)
    devnull = os.open(os.devnull, os.O_RDWR); os.dup2(devnull, 0)
    logfd = os.open(LOG, os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o644); os.dup2(logfd, 1); os.dup2(logfd, 2)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=MISSAV_URL); ap.add_argument("--quality", default=QUALITY)
    ap.add_argument("--out", default=MP4); ap.add_argument("--daemon", action="store_true")
    args = ap.parse_args()
    MISSAV_URL, QUALITY, MP4 = args.url, args.quality, args.out
    if args.daemon:
        daemonize(); log("Daemonized (detached). Starting download...")
    asyncio.run(main())
