---
name: hls-stream-download
description: 從網頁播放器抓取 m3u8 串流、下載所有片段並合併成 MP4 的完整流程
---

# HLS Stream Download

從網頁播放器抓取 m3u8 串流、驗證時長、下載所有片段並合併成 MP4。

## 觸發條件
- 用戶要求從網頁下載影片/戲劇
- 需要抓取 m3u8 串流並轉存為 MP4
- 需要處理斷點續傳和重試

## 步驟

### 1. 瀏覽網頁並切換片源
1. 使用 `browser_navigate` 打開目標網址
2. 使用 `browser_snapshot` 取得頁面快照
3. 找到片源切換按鈕（通常標示為「片源1」、「片源2」等）
4. 逐一點擊每個片源（`browser_click`）

### 2. 檢查每個片源的影片時長
1. 點擊片源後，使用 `browser_console` 執行：
   ```javascript
   document.querySelector('video')?.duration || 'no video yet'
   ```
2. 若時長大於 1800 秒（30分鐘），則該片源符合條件
3. 若不符合，繼續點擊下一個片源

### 3. 取得 m3u8 URL
1. 對符合條件的片源，使用 `browser_console` 執行：
   ```javascript
   const video = document.querySelector('video');
   video ? JSON.stringify({src: video.src, currentSrc: video.currentSrc}) : 'no video tag'
   ```
2. 從結果中取得 m3u8 URL

### 3b. 進階：Cloudflare 防護的串流站（如 missav / surrit.com）
> 常見陷阱：`curl`、`yt-dlp --impersonate` 直連會被 Cloudflare JS challenge 擋成 403 HTML。
> 有些站是**雙層 CF**：主頁 + 影片 CDN 各擋一次。此時必須用真實瀏覽器過關，再從頁面 JS 變數解出 m3u8。

**偵測方法：**
```bash
curl -sL --max-time 30 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36" "<m3u8_url>" | head -c 300
# 若回傳 <!DOCTYPE html>...Cloudflare 而非 #EXTM3U → 需瀏覽器過關
curl -sL --max-time 30 ... "<master_m3u8>" | grep -q '#EXT-X-STREAM-INF' && echo OK || echo NEED_BROWSER
```

**missav 特有解碼（obfuscated eval packer）：**
頁面用 base-15 `eval()` 隱藏 CDN URL，長這樣：
```javascript
eval(function(p,a,c,k,e,d){...}('e=\'8://7.6/5-4-3-2-1/d.0\';c=\'8://7.6/5-4-3-2-1/a/9.0\';b=\'8://7.6/5-4-3-2-1/a/9.0\';',15,15,'m3u8|<hash>|b1bc|4a58|cd17|<md5>|com|surrit|https|video|720p|source1280|source842|playlist|source'.split('|'),0,{}))
```
解碼後得到（`hash`=02a9c462...）：
- master: `https://surrit.com/<md5>-cd17-4a58-b1bc-<hash>/playlist.m3u8`
- 720p:   `https://surrit.com/.../720p/video.m3u8`（另有 360p / 480p）
> 手動解碼太累：直接用下方 Playwright 腳本，它會自己 navigate → 過關 → 從 `fetch()` 抓 master + 各品質 playlist。

**⚠️ `.jpeg` 檔名陷阱：** missav 的片段檔名是 `videoN.jpeg`，但內容其實是 **MPEG-TS**（magic byte `0x47`），不是 JPEG。別用 JPEG 解碼或信任副檔名，合併時照原檔名存成 `.ts`。

### 4. 分析 m3u8 串流
1. 使用 `curl` 下載 m3u8 主清單：
   ```bash
   curl -s -o /tmp/m3u8_master.m3u8 "<master_url>"
   ```
2. 檢查是否為多質量選擇（指向另一個 m3u8），若是則跟進
3. 下載實際片段清單：
   ```bash
   curl -s -o /tmp/m3u8_segments.m3u8 "<segment_url>"
   ```
4. 統計片段數和總時長：
   ```bash
   grep -c '^#EXTINF:' /tmp/m3u8_segments.m3u8
   grep '^#EXTINF:' /tmp/m3u8_segments.m3u8 | awk -F: '{sum += $2} END {print "Total segments: " NR ", Total duration: " sum " seconds (" sum/60 " minutes)"}'
   ```

### 5. 下載並合併
1. 建立下載腳本 `/tmp/download_hls.py`（參考以下模板）
2. 執行下載：
   ```bash
   python3 /tmp/download_hls.py 2>&1
   ```
3. 使用 `terminal(background=true, notify_on_complete=true)` 執行
4. 使用 `process(action='wait')` 等待完成

### 6. 驗證 MP4 檔案
1. 使用 `ffprobe` 驗證：
   ```bash
   ffprobe -v error -show_entries format=duration,size -show_entries format=format_name -of default=noprint_wrappers=1 "<output_file>"
   ```
2. 確認時長和格式正確

### 7. 清理暫存
1. 詢問用戶是否清理暫存資料
2. 若同意，執行：
   ```bash
   rm -rf /tmp/hls_segments /tmp/m3u8_playlist.m3u8 /tmp/m3u8_master.m3u8 /tmp/m3u8_segments.m3u8 /tmp/download_hls.py
   ```

## 下載腳本模板（一）：一般站 — curl + ffmpeg

```python
#!/usr/bin/env python3
"""HLS downloader with resume and retry."""
import os, sys, time, subprocess, re
from urllib.parse import urljoin

M3U8_URL = "<m3u8_url>"
BASE_URL = "<base_url>"
OUTPUT_DIR = "/tmp/hls_segments"
OUTPUT_FILE = os.path.expanduser("~/drama_episode1.mp4")
MAX_RETRIES = 10
RETRY_DELAY = 5

def parse_m3u8(url):
    result = subprocess.run(["curl", "-s", "--max-time", "30", "-o", "-", url],
                          capture_output=True, text=True)
    if result.returncode != 0:
        return None
    content = result.stdout
    if "#EXTM3U" not in content:
        if content.strip().endswith(".m3u8") or "/hls/" in content.strip():
            new_url = urljoin(url, content.strip())
            return parse_m3u8(new_url)
        return None
    segments = []
    current_duration = None
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('#EXTINF:'):
            match = re.search(r'#EXTINF:(\d+\.?\d*)', line)
            if match:
                current_duration = float(match.group(1))
        elif line.startswith('#') or line == '':
            continue
        else:
            segments.append((line, current_duration))
            current_duration = None
    return segments

def download_segment(url, output_path, max_retries=MAX_RETRIES):
    for attempt in range(1, max_retries + 1):
        result = subprocess.run(
            ["curl", "-s", "--max-time", "60", "--retry", "3", "--retry-delay", "2",
             "-o", output_path, url],
            capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        if attempt < max_retries:
            time.sleep(RETRY_DELAY)
    return False

def verify_segment(path):
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'rb') as f:
            return f.read(1) == b'\x47'
    except:
        return False

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    segments = parse_m3u8(M3U8_URL)
    if not segments:
        sys.exit(1)
    
    downloaded = []
    for i, (filename, duration) in enumerate(segments):
        local_name = filename.split('?')[0] if '?' in filename else filename
        local_path = os.path.join(OUTPUT_DIR, local_name)
        
        if os.path.exists(local_path) and verify_segment(local_path):
            downloaded.append(local_path)
            continue
        
        print(f"[{i+1}/{len(segments)}] Downloading: {filename[:60]}...")
        if download_segment(urljoin(BASE_URL, filename), local_path):
            if verify_segment(local_path):
                downloaded.append(local_path)
                print(f"  [✓] ({os.path.getsize(local_path)} bytes)")
            else:
                print(f"  [✗] Invalid segment")
        else:
            print(f"  [✗] Failed")
    
    # Merge with ffmpeg
    list_file = os.path.join(OUTPUT_DIR, "filelist.txt")
    with open(list_file, 'w') as f:
        for seg in downloaded:
            f.write(f"file '{seg}'\n")
    
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
           "-c", "copy", "-movflags", "+faststart", OUTPUT_FILE]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    
    if result.returncode == 0:
        print(f"[✓] Done: {OUTPUT_FILE} ({os.path.getsize(OUTPUT_FILE)/(1024*1024):.1f} MB)")
    else:
        print(f"[!] FFmpeg error: {result.stderr[-500:]}")

if __name__ == "__main__":
    main()
```

## 下載腳本模板（二）：Cloudflare 防護站 — Playwright 無頭瀏覽器過關
> 當 curl/yt-dlp 直連被 CF 擋成 403 HTML 時用這個。原理：用 Playwright 開無頭 Chrome，
> navigate 到主頁讓它跑完 JS challenge、建立 session，再用 `page.evaluate(fetch())` 抓每個片段。
> **關鍵**：`main()` 是 async，必須用 `asyncio.run(main())`；且要在 async context 裡用
> `async_playwright()`（不是 sync_playwright），否則會報 "Sync API inside the asyncio loop"。

```python
#!/usr/bin/env python3
"""Playwright-based HLS downloader for Cloudflare-protected CDNs (e.g. missav/surrit)."""
import os, time, re, subprocess, asyncio, base64
from playwright.async_api import async_playwright

BASE = "https://surrit.com/<md5>-cd17-4a58-b1bc-<hash>"   # 從解碼或瀏覽器 network 取得
QUALITY = "720p"
PLAYLIST_URL = f"{BASE}/{QUALITY}/video.m3u8"
OUT_DIR = "/tmp/hls_segs"
MP4 = os.path.expanduser("~/movie_720p.mp4")
LOG = "/tmp/download_progress.log"
CONCURRENCY = 10
MAX_RETRIES = 5

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")

async def grab(page, idx):
    # fetch 片段 → base64 → 寫成 .ts（注意：副檔名可能是 .jpeg，內容是 TS）
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
    open(os.path.join(OUT_DIR, f"video{idx}.ts"), "wb").write(base64.b64decode(b64['b64']))
    return True

async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        if f.startswith("video"):
            os.remove(os.path.join(OUT_DIR, f))   # 斷點續傳：先清舊的
    log(f"Started. Quality={QUALITY}")
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            viewport={"width":1280,"height":900})
        page = await ctx.new_page()
        log("Navigating to missav (establish CF context)...")
        await page.goto("https://missav.ws/<dvd_id>", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)   # 讓 player eval + challenge 跑完
        log("Fetching segment list...")
        seg_list = await page.evaluate(f"""async()=>{{
            const resp = await fetch('{PLAYLIST_URL}');
            const text = await resp.text();
            const durs = [...text.matchAll(/#EXTINF:([\\d.]+)/g)].map(m=>parseFloat(m[1]));
            const files = text.split('\\n').filter(l=>l && !l.startsWith('#'));
            return {{count: files.length, totalDur: durs.reduce((a,c)=>a+c,0)}};
        }}""")
        n = seg_list['count']
        log(f"{n} segments, ~{seg_list['totalDur']/60:.0f} min")
        done, failed, start = 0, [], time.time()
        async def dl(idx):
            nonlocal done
            path = os.path.join(OUT_DIR, f"video{idx}.ts")
            if os.path.exists(path) and os.path.getsize(path) > 1000:
                return True
            for a in range(MAX_RETRIES):
                if await grab(page, idx) and os.path.getsize(path) > 1000:
                    break
                await asyncio.sleep(2 + a)
            else:
                failed.append(idx); return False
            done += 1
            if done % 50 == 0 or done == n:
                el = time.time() - start; rate = done/el if el else 0
                log(f"Progress: {done}/{n} ({100*done/n:.1f}%) | {el/60:.1f}m | ~{(n-done)/rate:.0f}m left")
            return True
        sem = asyncio.Semaphore(CONCURRENCY)
        async def wrap(i):
            async with sem:
                await dl(i)
        await asyncio.gather(*[wrap(i) for i in range(n)])
        log(f"Download complete: {done} ok, {len(failed)} failed")
        await b.close()
    # 合併（先確認片段是 TS：magic byte 0x47；若實際是 fmp4 則改用 -c copy）
    files = sorted([f for f in os.listdir(OUT_DIR) if f.endswith('.ts')],
                   key=lambda x: int(re.search(r'video(\d+)', x).group(1)))
    open(os.path.join(OUT_DIR, "filelist.txt"), "w").write(
        "".join(f"file '{os.path.join(OUT_DIR,f)}'\n" for f in files))
    r = subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",
            os.path.join(OUT_DIR,"filelist.txt"),"-c","copy","-movflags","+faststart",MP4],
            capture_output=True, text=True)
    log(f"[OK] {MP4} ({os.path.getsize(MP4)/1048576:.0f} MB)" if r.returncode==0
        else f"[FFMPEG ERROR]\n{r.stderr[-800:]}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 注意事項
- **雙層 Cloudflare**：主頁 + 影片 CDN 各擋一次，curl/yt-dlp 直連都會 403；用 Playwright 模板二。
- **`.jpeg` 檔名陷阱**：片段檔名可能叫 `.jpeg` 但內容是 MPEG-TS（magic byte `0x47`），別當 JPEG 處理。
- **async 陷阱**：Playwright 模板的 `main()` 是 coroutine，必須 `asyncio.run(main())`；context 用 `async_playwright()`。
- **某些串流有 hash 驗證**，必須保留完整 URL（包含 ?hash=...）
- **合併前驗證片段格式**：TS 看 magic byte `0x47`；若解碼後是 fmp4/ISO 則改用 `-c copy` 或 `-f mp4 concat`。
- **下載過程可能很長**（1800 段 × 4s ≈ 120min 影片，實際下載約 15-25min），用 background 模式。
- **斷點續傳**：已下載且 >1KB 的 `.ts` 會跳過；重跑前可先清 `OUT_DIR` 內舊檔。
- **每個片段最多重試 MAX_RETRIES 次**，每次間隔遞增（2+a 秒）。
- **合併後用 ffprobe 驗證**：duration、codec、size 都對才算成功。
