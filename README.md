# 片匣 / CineCase

**A local-first media library with a film-archive soul.**

Point it at the folders you care about, press **Scan now**, and it builds a
private library with cover thumbnails, six-frame contact sheets, duration and
codec metadata, duplicate detection, search, and in-browser playback.

Everything runs on your machine. The app binds to `127.0.0.1` only. A fresh
install performs one automatic scan; after that, scanning is manual only.

**English** | [中文](README.zh-CN.md)

## Features

- **Automatic first scan, then manual only** — a fresh install runs one scan;
  every later refresh comes from the **Scan now** button. No background patrol.
- **Local web UI** — `http://127.0.0.1:8765`.
- **Bilingual interface** — English by default, one-click Chinese toggle; the
  choice is remembered in the browser.
- **Metadata via ffprobe** — duration, resolution, frame rate, video/audio
  codecs, bitrate.
- **Covers & contact sheets** — a 640 px cover plus a 3×2 contact sheet for
  every video; audio gets a waveform cover.
- **Duplicate detection** — same-size candidates are sampled and hashed;
  duplicates are hidden by default and can be revealed.
- **Search, filter, sort** — search titles, filenames, and Bilibili
  descriptions; filter by media type, collection, and sort by recency, name,
  duration, or size.
- **Playback with Range requests** — seek in the browser; formats the browser
  cannot decode can be handed to your local player.
- **Continue watching** — playback position is stored in the browser.
- **Delete with confirmation** — permanently removes the media file, catalog
  row, cover, and contact sheet. A second confirmation is required.
- **Bilibili sidecar support** — if a download includes `*-元数据.json`, its
  title and description are used.

## Requirements

- Windows 10/11 for the provided `start.ps1` / `stop.ps1` scripts.
- Python **3.10+** (standard library only — no pip dependencies).
- `ffmpeg` and `ffprobe` available on `PATH`, or absolute paths in
  `config.json`.
- A modern browser.

The Python server and scanner also run on macOS/Linux if you start them
manually. The browser-open action uses `open` / `xdg-open` there.

## Quick start

```powershell
git clone https://github.com/Dabendi/cinecase.git
cd cinecase
.\start.ps1
```

`start.ps1` starts the web server and the indexer, then opens
`http://127.0.0.1:8765`. On a fresh install the indexer performs one automatic
scan and then waits for manual scans.

On first run, `config.json` is created from `config.example.json` if it does
not exist, and the automatic first scan uses those example roots. To have the
first scan use your own folders, copy `config.example.json` to `config.json`
and edit `roots` before starting. After that, edit `config.json`, save, and
press **Scan now** in the UI. Stop everything with:

```powershell
.\stop.ps1
```

macOS / Linux:

```bash
python3 server.py
python3 scan.py --watch
```

Then open `http://127.0.0.1:8765`. The first start auto-scans once; press
**Scan now** for later refreshes.

## Configuration

`config.json` is gitignored. A minimal example:

```json
{
  "port": 8765,
  "default_min_size_mb": 1,
  "ffmpeg": "ffmpeg",
  "ffprobe": "ffprobe",
  "roots": [
    { "label": "Videos", "path": "~/Videos", "min_size_mb": 0 },
    { "label": "Downloads", "path": "~/Downloads", "min_size_mb": 1 }
  ]
}
```

- `roots`: folders to index. Keep `label` values unique; `path` supports `~`
  and environment variables.
- `min_size_mb`: per-root minimum file size; smaller files are ignored.
- `exclude_names`: directory names skipped during the walk (defaults to
  `node_modules`, `.git`, `.venv`, etc.).
- `ffmpeg` / `ffprobe`: executable names or absolute paths.
- `port`: local port, default `8765`. Changing it requires restarting the
  server (`stop.ps1` / `start.ps1`); other settings are re-read on the next
  manual scan.

A fresh install performs one automatic scan. After that, add or change
directories, save, and press **Scan now**; new files are picked up on the next
manual scan. There is no timer.

## How it works

On startup, if no completed scan is recorded yet, the indexer runs the
pipeline once automatically. Later startups stay idle until **Scan now** is
pressed.

1. **Scan** — walk the configured roots, ignore excluded folders, and record
   media files above each root's size threshold.
2. **Dedupe** — group files by size, sample-hash candidates, and mark
   duplicates.
3. **Probe** — read duration, dimensions, codecs, bitrate, and frame rate with
   `ffprobe`.
4. **Cover** — prefer an adjacent image / `poster.jpg`; otherwise extract a
   frame; audio falls back to a waveform.
5. **Contact sheet** — sample six frames across the video into one image.
6. **Serve** — `server.py` exposes a JSON API and a Range-capable media
   stream, bound to `127.0.0.1`.

Generated files live in:

- `data/library.db` — SQLite catalog
- `thumbs/` — cover images
- `strips/` — contact sheets
- `data/status.json` — live progress for the UI
- `data/control.json` — pause / resume / scan requests

Delete `data/library.db`, `thumbs/`, and `strips/` to reset the library; source
media is untouched.

## Delete behavior

The detail panel has a **Delete file** button. It asks for confirmation, then
permanently removes the source file and its generated artifacts. Deletion does
not use the Recycle Bin and cannot be undone. If another player is holding the
file open, the API returns `in_use` and the UI asks you to close it first.

## Privacy

- The app makes no outbound network requests.
- `config.json`, `data/`, `thumbs/`, `strips/`, and `screenshots/` are
  gitignored.
- The server binds only to `127.0.0.1`.
- The only destructive operation is the confirmed delete.

## Limitations

- Browser playback depends on the browser's codec support. MKV/FLV/AVI/H.265
  files may open via the local player instead.
- Scanning is manual after the one automatic first-run pass; there is no
  scheduled patrol.
- The PowerShell scripts are Windows-only. The Python core is portable.

## Project layout

```
scan.py              background indexer (scan, ffprobe, covers, strips, dedupe)
server.py            local web server (UI, JSON API, Range streaming, delete)
web/index.html       UI shell
web/app.js           UI logic + EN/ZH i18n
web/style.css        archival cinema theme
config.example.json  template
start.ps1 / stop.ps1 Windows helper scripts
```

## License

[MIT](LICENSE)
