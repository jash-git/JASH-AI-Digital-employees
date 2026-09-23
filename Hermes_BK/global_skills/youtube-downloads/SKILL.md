---
name: youtube-downloads
description: Download YouTube videos and playlists with yt-dlp.
---

# youtube-downloads

Use when downloading YouTube videos or playlists with yt-dlp, especially when dealing with playlists, 403 errors, or unusual title formats.

## Prerequisites

1. Ensure yt-dlp is up to date:
   ```
   pip install --upgrade yt-dlp
   ```

2. Install Deno (required for YouTube JS signature solving):
   ```
   curl -fsSL https://deno.land/install.sh | sh
   export PATH="$HOME/.deno/bin:$PATH"
   ```

3. Verify ffmpeg is available (for merging audio/video and embedding thumbnails).

## Standard Download Command

For playlist downloads with safe naming and metadata embedding:

```
yt-dlp \
  -o "%(playlist_index)02d - %(title)s.%(ext)s" \
  --merge-output-format mp4 \
  --embed-thumbnail \
  --embed-metadata \
  --restrict-filenames \
  --format "bestvideo[protocol^=m3u8]+bestaudio[protocol^=m3u8]/best[protocol^=m3u8]/best" \
  "https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID"
```

For single video downloads:
```
yt-dlp \
  -o "%(title)s.%(ext)s" \
  --merge-output-format mp4 \
  --embed-thumbnail \
  --embed-metadata \
  --restrict-filenames \
  --format "bestvideo+bestaudio/best" \
  "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Pitfalls & Fixes

### 403 Forbidden / Bandwidth Limits
- **Cause**: YouTube rate-limiting automated downloads.
- **Fix**: Use m3u8 protocol format (`bestvideo[protocol^=m3u8]+bestaudio[protocol^=m3u8]/best[protocol^=m3u8]/best`) instead of default format. Avoid forcing `--extractor-args "youtube:player_client=web"` or `ios` as these often trigger stricter blocks.
- **Fallback**: Try `--format "bestvideo+bestaudio/best"` as a last resort.

### Video Title Shows as "NA"
- **Cause**: yt-dlp fails to parse the title from YouTube's API response.
- **Fix**: After download, scan for `NA - *.mp4` files and rename them manually or with a script. Use `yt-dlp --flat-playlist --dump-json` to get correct titles and indices before downloading.

### Wrong Video ID
- **Cause**: Copying the wrong video ID from a playlist page or URL.
- **Fix**: Always verify video IDs with:
  ```
  yt-dlp --flat-playlist --dump-json "PLAYLIST_URL"
  ```
  This outputs one JSON object per video with `id`, `title`, and `playlist_index` fields. Compare against what you expect.

### Temp Files Left Behind
- **Cause**: Download interrupted or merge step failed.
- **Fix**: Clean up with a Python script:
  ```python
  import glob, os
  for f in glob.glob(os.path.join(workdir, "*")):
      name = os.path.basename(f)
      if ".part" in name or ".ytdl" in name or name.endswith(".webp") or name.endswith(".meta") or ".temp" in name:
          os.remove(f)
  ```

### Video Unavailable
- **Cause**: Video was deleted, set to private, or has region restrictions.
- **Fix**: Check with `yt-dlp --dump-json --no-download VIDEO_URL`. If all player clients fail (`web`, `mweb`, `android`, `ios`, `web_creator`), the video is genuinely unavailable. Inform the user rather than retrying.

## Workflow for Playlist Downloads

1. **Verify playlist contents**: Run `yt-dlp --flat-playlist --dump-json PLAYLIST_URL` to get all video IDs and titles.
2. **Download**: Run yt-dlp with the standard command above.
3. **Handle NA titles**: If any files have "NA" in the name, use the flat-playlist output to rename them correctly.
4. **Clean temp files**: Remove `.part`, `.ytdl`, `.meta`, `.webp`, and `.temp.*` files.
5. **Verify**: Count final MP4 files against the playlist index count.
