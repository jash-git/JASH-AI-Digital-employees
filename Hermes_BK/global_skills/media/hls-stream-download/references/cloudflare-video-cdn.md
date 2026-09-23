# References: Cloudflare-protected video CDNs (missav / surrit / fourhoi)

Session-specific detail for downloading HLS from sites whose CDN runs a **Cloudflare managed JS
challenge** that headless `curl` cannot solve. Captured while pulling DSJH-017 from missav.ws.

## The problem chain

```
missav.ws/<id>   (CF challenge, solved by browser)
      │  page embeds an obfuscated eval() that decodes to CDN URLs on surrit.com
      ▼
surrit.com/<hash>/playlist.m3u8        ← master (360p / 480p / 720p variants)
         ├── 360p/video.m3u8
         ├── 480p/video.m3u8
         └── 720p/video.m3u8            ← each lists ~1800 segments named videoN.jpeg
```

- `surrit.com` is the **video CDN** (family: `.fourhoi.com`, `.myavlive.com`). It has its OWN
  Cloudflare challenge. A plain `curl` to it returns a 4546-byte CF cookie-error HTML page, even
  with `_cfuvid` / `cf_clearance` cookies copied from missav — those cookies live on
  `.fourhoi.com` / `.missav.ws`, **not** on surrit.com.
- The browser's in-page `fetch()` works because the same Chromium context that solved missav's
  challenge also resolves surrit's when it fetches the CDN asset (the page does this itself).

## Decoding the obfuscated eval()

The page contains a JS packer:
```js
eval(function(p,a,c,k,e,d){...}('e=\'8://7.6/5-4-3-2-1/d.0\';c=\'8://7.6/5-4-3-2-1/a/9.0\';...',15,15,'m3u8|504fe5ccfa8a|b1bc|4a58|cd17|02a9c462|com|surrit|https|video|720p|source1280|source842|playlist|source'.split('|'),0,{}))
```
Tokens (index 0..14): `m3u8 | 504fe5ccfa8a | b1bc | 4a58 | cd17 | 02a9c462 | com | surrit | https | video | 720p | source1280 | source842 | playlist | source`

Decoded URLs:
- `e` = `https://surrit.com/02a9c462-cd17-4a58-b1bc-504fe5ccfa8a/d.m3u8`  (master)
- `c` = `.../a/video.m3u8` → actually resolves to `.../720p/video.m3u8` (source1280 / 720p)
- `b` = same path, fallback (source842)

The master manifest also carries `#EXT-X-TOKEN=...` and per-quality `#EXT-X-STREAM-INF`.

## Segment format gotcha: `.jpeg` extension ≠ JPEG

Segments are named `videoN.jpeg` but are actually **MPEG-TS** files. Verify the magic byte:
```
head -c 2 video0.jpeg   # => 47 40   (0x47 = TS sync byte)
```
The file also contains an "FFmpeg Service01" metadata atom. So merge with `ffmpeg -f concat`
(copy), NOT by treating them as images.

## Verified working method: Playwright Async API, fetch() per segment

Why this works and others don't (tested in-session):

| Method | Result | Why |
|--------|--------|-----|
| `curl_cffi` impersonate on missav + surrit | 403 CF challenge | headless can't run the JS puzzle |
| `yt-dlp --extractor-args generic:impersonate` | "Unsupported URL" (after passing CF) | no dedicated extractor |
| Playwright **Sync** API inside `asyncio.run()` | crashes: *"Sync API inside the asyncio loop"* | must use Async API in an event loop |
| `page.download()` / `ctx.download.create()` | AttributeError in this Playwright version | not available here |
| **Playwright Async + `page.evaluate(fetch())`** returning base64 → write `.ts` | ✅ 100% success, ~1.3 seg/s | browser context already CF-valid |

Speed: ~1.4 segments/sec with 10 parallel fetch() → ~22 min for 1800 segments + ffmpeg merge.

## Long-running downloads survive terminal timeouts only when detached

The terminal tool's foreground mode kills the process group at its timeout (~420s), which
aborts a download mid-flight (observed: frozen at 500/1800). Two fixes that worked:

1. **Double-fork daemon** (`daemonize()` in `scripts/download_via_browser.py`): parent exits,
   `os.setsid()`, second parent exits → the worker reparents to init and survives the terminal's
   timeout. Redirect std fds to the log file so progress persists across separate calls.
2. **Background mode** (`terminal(background=true)`) with a watcher pattern like `"Download complete"`.

Always write progress to a stable log (e.g. `/tmp/hls_dl_progress.log`) and poll it in separate
`terminal` calls rather than relying on one long foreground run.

## Quick verification recipe (after download)
```bash
# format + duration
ffprobe -v error -show_entries format=duration,size,format_name -of default=noprint_wrappers=1 movie.mp4
# per-stream codec / resolution / audio
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate -of default=noprint_wrappers=1 movie.mp4
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,bit_rate -of default=noprint_wrappers=1 movie.mp4
# decode-check middle + end (catches truncated/corrupt merges)
ffmpeg -v error -ss 3600 -i movie.mp4 -frames:v 1 -f null - && ffmpeg -v error -ss 7200 -i movie.mp4 -frames:v 1 -f null -
```

## Reference: DSJH-017 concrete values (from this session)
- Page: `https://missav.ws/dsjh-017-uncensored-leak`
- CDN base: `https://surrit.com/02a9c462-cd17-4a58-b1bc-504fe5ccfa8a`
- Master: `.../playlist.m3u8` → 360p / 480p / 720p (CODECS `avc1.64001e/mp4a.40.2`)
- Segments: 1800 × 4s = 7199.6s ≈ 120 min; merged MP4 came out **7324s (~122 min), 1.5 GB, H264 720p + AAC**
