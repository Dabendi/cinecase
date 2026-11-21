#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""片匣 · 本地媒体库：后台索引器

只读扫描配置中的媒体目录，把元数据、封面缩略图、重复标记写进
data/library.db，并持续输出 data/status.json 供看板实时展示。
不会修改、移动或删除任何媒体文件。
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
THUMBS = BASE / "thumbs"
STRIPS = BASE / "strips"
LOGS = DATA / "logs"
CFG_PATH = BASE / "config.json"
DB_PATH = DATA / "library.db"
STATUS_PATH = DATA / "status.json"
CONTROL_PATH = DATA / "control.json"
PID_PATH = DATA / "scanner.pid"

VIDEO_EXT = {
    ".mp4", ".mkv", ".avi", ".flv", ".mov", ".wmv", ".webm", ".m4v",
    ".ts", ".mpg", ".mpeg", ".rmvb", ".rm", ".3gp", ".vob", ".ogv", ".mts",
}
AUDIO_EXT = {
    ".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".opus", ".wma",
    ".ape", ".alac", ".aiff", ".m4b",
}
MEDIA_EXT = VIDEO_EXT | AUDIO_EXT

TRAILING_DATE = re.compile(
    r"\s*[\(\[（【]?\d{4}[-_.年]\d{1,2}[-_.月]\d{1,2}日?[\)\]）】]?\s*$"
)

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
BELOW_NORMAL = 0x00004000 if os.name == "nt" else 0

PHASE_LABELS = {
    "boot": "启动中",
    "scan": "正在清点文件",
    "dedupe": "正在比对重复",
    "probe": "正在识别媒体",
    "thumb": "正在冲印封面",
    "strip": "正在冲印接触印样",
    "paused": "已暂停",
    "idle": "已就绪，等待手动巡检",
    "error": "索引器出错",
}


def now() -> float:
    return time.time()


def iso(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or now()).strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{iso()}] {msg}", flush=True)


def write_json_atomic(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(obj, ensure_ascii=False, indent=1)
    for attempt in range(5):
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)
            return
        except OSError:
            if attempt == 4:
                raise
            time.sleep(0.05 * (attempt + 1))


def load_config() -> dict:
    if not CFG_PATH.exists():
        example = BASE / "config.example.json"
        if not example.exists():
            raise FileNotFoundError(
                "config.json is missing and config.example.json was not found"
            )
        CFG_PATH.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    with CFG_PATH.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("ffmpeg", "ffmpeg")
    cfg.setdefault("ffprobe", "ffprobe")
    cfg.setdefault("default_min_size_mb", 1)
    roots = []
    for root in cfg.get("roots", []):
        if not isinstance(root, dict) or not isinstance(root.get("path"), str):
            continue
        root["path"] = os.path.normpath(
            os.path.expanduser(os.path.expandvars(root["path"]))
        )
        root.setdefault("label", os.path.basename(root["path"]) or "Media")
        root.setdefault("min_size_mb", cfg["default_min_size_mb"])
        roots.append(root)
    cfg["roots"] = roots
    labels = [r.get("label") for r in roots]
    if len(labels) != len(set(labels)):
        log("警告: roots 中存在重复的 label，建议保持 label 唯一")
    return cfg


def load_last_scan(conn: sqlite3.Connection) -> float | None:
    try:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'last_scan_at'"
        ).fetchone()
        if row and row[0]:
            return float(row[0])
    except (sqlite3.Error, ValueError):
        pass
    try:
        row = conn.execute("SELECT MAX(probed_at) FROM media").fetchone()
        if row and row[0]:
            return float(row[0])
    except sqlite3.Error:
        pass
    return None


def has_completed_scan(conn: sqlite3.Connection) -> bool:
    try:
        row = conn.execute(
            """SELECT 1 FROM meta
               WHERE key = 'last_scan_at'
                 AND value IS NOT NULL AND value != ''"""
        ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False


def save_last_scan(conn: sqlite3.Connection, ts: float) -> None:
    conn.execute(
        """INSERT INTO meta(key, value) VALUES('last_scan_at', ?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
        (str(ts),),
    )
    conn.commit()


def lower_priority() -> None:
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), BELOW_NORMAL)
    except Exception:
        pass


def open_db() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)
    STRIPS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS media (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            path         TEXT UNIQUE NOT NULL,
            root         TEXT NOT NULL,
            collection   TEXT,
            rel_dir      TEXT,
            name         TEXT NOT NULL,
            title        TEXT,
            name_key     TEXT,
            kind         TEXT,
            ext          TEXT,
            size         INTEGER,
            mtime        REAL,
            duration     REAL,
            width        INTEGER,
            height       INTEGER,
            vcodec       TEXT,
            acodec       TEXT,
            bitrate      INTEGER,
            fps          REAL,
            thumb        TEXT,
            cover_src    TEXT,
            sig          TEXT,
            dup_of       INTEGER,
            status       TEXT NOT NULL DEFAULT 'new',
            error        TEXT,
            thumb_error  TEXT,
            bvid         TEXT,
            pubdate      INTEGER,
            description  TEXT,
            added_at     REAL,
            probed_at    REAL
        );
        CREATE INDEX IF NOT EXISTS idx_media_status ON media(status);
        CREATE INDEX IF NOT EXISTS idx_media_kind ON media(kind);
        CREATE INDEX IF NOT EXISTS idx_media_root ON media(root);
        CREATE INDEX IF NOT EXISTS idx_media_size ON media(size);
        CREATE INDEX IF NOT EXISTS idx_media_dup ON media(dup_of);
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(media)").fetchall()}
    for col in ("strip", "strip_error"):
        if col not in cols:
            conn.execute(f"ALTER TABLE media ADD COLUMN {col} TEXT")
    conn.commit()
    return conn


def read_control() -> dict:
    try:
        return json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_control(obj: dict) -> None:
    write_json_atomic(CONTROL_PATH, obj)


class State:
    def __init__(self) -> None:
        self.phase = "boot"
        self.phase_done = 0
        self.phase_total = 0
        self.current = ""
        self.files_seen = 0
        self.bytes_seen = 0
        self.started = now()
        self.last_scan_at: float | None = None
        self.paused = False
        self.pause_phase: str | None = None
        self.last_publish = 0.0

    def publish(self, conn: sqlite3.Connection, force: bool = False) -> None:
        t = now()
        if not force and t - self.last_publish < 0.8:
            return
        self.last_publish = t
        try:
            stats = db_stats(conn)
            recent = [
                dict(r)
                for r in conn.execute(
                    """SELECT id, title, kind, thumb, duration, collection
                       FROM media
                       WHERE status IN ('ready', 'error')
                       ORDER BY COALESCE(probed_at, added_at) DESC, id DESC
                       LIMIT 5"""
                ).fetchall()
            ]
            errors = [
                dict(r)
                for r in conn.execute(
                    """SELECT id, title, error, thumb_error, strip_error
                       FROM media
                       WHERE status = 'error' OR thumb_error IS NOT NULL
                             OR strip_error IS NOT NULL
                       ORDER BY id DESC LIMIT 5"""
                ).fetchall()
            ]
        except sqlite3.Error:
            stats, recent, errors = {}, [], []
        progress = None
        if self.phase_total > 0:
            progress = round(min(1.0, self.phase_done / self.phase_total), 4)
        payload = {
            "name": "片匣",
            "pid": os.getpid(),
            "phase": self.phase,
            "phase_label": PHASE_LABELS.get(self.phase, self.phase),
            "running": True,
            "paused": self.paused,
            "started_at": self.started,
            "started_at_text": iso(self.started),
            "updated_at": t,
            "updated_at_text": iso(t),
            "current": self.current,
            "progress": progress,
            "phase_done": self.phase_done,
            "phase_total": self.phase_total,
            "files_seen": self.files_seen,
            "bytes_seen": self.bytes_seen,
            "last_scan_at": self.last_scan_at,
            "last_scan_at_text": iso(self.last_scan_at) if self.last_scan_at else None,
            "stats": stats,
            "recent": recent,
            "errors": errors,
        }
        try:
            write_json_atomic(STATUS_PATH, payload)
        except OSError:
            pass


_STATS_SQL = """
SELECT
  COUNT(*) AS rows_all,
  SUM(CASE WHEN status = 'missing' THEN 1 ELSE 0 END) AS missing,
  SUM(CASE WHEN status != 'missing' AND kind = 'video' THEN 1 ELSE 0 END) AS videos,
  SUM(CASE WHEN status != 'missing' AND kind = 'audio' THEN 1 ELSE 0 END) AS audio,
  SUM(CASE WHEN status != 'missing' THEN size ELSE 0 END) AS total_size,
  SUM(CASE WHEN status != 'missing' THEN COALESCE(duration, 0) ELSE 0 END) AS total_duration,
  SUM(CASE WHEN status != 'missing' AND dup_of IS NOT NULL THEN 1 ELSE 0 END) AS duplicates,
  SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) AS pending_probe,
  SUM(CASE WHEN status = 'probed' THEN 1 ELSE 0 END) AS pending_thumb,
  SUM(CASE WHEN status = 'ready' THEN 1 ELSE 0 END) AS ready,
  SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS errored,
  SUM(CASE WHEN status != 'missing' AND strip IS NOT NULL THEN 1 ELSE 0 END) AS strips,
  SUM(CASE WHEN status = 'ready' AND kind = 'video' AND strip IS NULL
                AND strip_error IS NULL THEN 1 ELSE 0 END) AS pending_strip
FROM media
"""


def db_stats(conn: sqlite3.Connection) -> dict:
    r = conn.execute(_STATS_SQL).fetchone()
    d = dict(r) if r else {}
    missing = d.get("missing") or 0
    d = {k: (v or 0) for k, v in d.items()}
    d["total"] = d.pop("rows_all", 0) - missing
    return d


def rel_dir_of(dirpath: str, base: str) -> str:
    try:
        rel = os.path.relpath(dirpath, base)
    except ValueError:
        return ""
    return "" if rel == "." else rel


def collection_for(root: dict, rel_dir: str) -> str:
    label = root["label"]
    if not rel_dir:
        return label
    parts = [p for p in rel_dir.split(os.sep) if p]
    if not parts:
        return label
    if label == "学习盘":
        return parts[0]
    if label == "B站收藏":
        return parts[-1]
    return label


def clean_stem(stem: str) -> str:
    s = stem.replace("_", " ")
    s = TRAILING_DATE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or stem


def natural_key(text: str) -> str:
    return re.sub(r"\d+", lambda m: m.group(0).zfill(6), text.lower())


def read_bilibili_meta(path: str) -> dict:
    p = Path(path)
    cand = p.with_name(p.stem + "-元数据.json")
    if not cand.exists():
        return {}
    try:
        raw = json.loads(cand.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        "title": (raw.get("title") or "").strip(),
        "description": raw.get("desc") or "",
        "bvid": raw.get("bvid") or "",
        "pubdate": raw.get("pubdate") or 0,
    }


def kind_by_ext(ext: str) -> str:
    return "video" if ext in VIDEO_EXT else "audio"


def upsert_media(
    conn: sqlite3.Connection,
    root: dict,
    path: str,
    rel_dir: str,
    size: int,
    mtime: float,
) -> None:
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path)
    stem = Path(path).stem
    meta = read_bilibili_meta(path)
    title = meta.get("title") or clean_stem(stem)
    collection = collection_for(root, rel_dir)
    nkey = natural_key(title)
    kind = kind_by_ext(ext)

    row = conn.execute(
        "SELECT id, size, mtime, status, thumb, duration FROM media WHERE path = ?",
        (path,),
    ).fetchone()

    if row is None:
        conn.execute(
            """INSERT INTO media
               (path, root, collection, rel_dir, name, title, name_key, kind, ext,
                size, mtime, status, added_at, bvid, pubdate, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?)""",
            (
                path, root["label"], collection, rel_dir, name, title, nkey, kind,
                ext, size, mtime, now(), meta.get("bvid") or None,
                meta.get("pubdate") or None, meta.get("description") or None,
            ),
        )
        return

    if row["size"] == size and abs((row["mtime"] or 0) - mtime) < 0.001:
        if row["status"] == "missing":
            restored = "ready" if row["thumb"] else (
                "probed" if row["duration"] else "new"
            )
            conn.execute(
                "UPDATE media SET status = ? WHERE id = ?", (restored, row["id"])
            )
        elif meta.get("title") and meta.get("title") != title:
            conn.execute(
                "UPDATE media SET title = ?, name_key = ? WHERE id = ?",
                (title, nkey, row["id"]),
            )
        return

    conn.execute(
        """UPDATE media SET
             root = ?, size = ?, mtime = ?, name = ?, title = ?, name_key = ?,
             collection = ?, rel_dir = ?, kind = ?, ext = ?,
             status = 'new', thumb = NULL, cover_src = NULL, sig = NULL,
             duration = NULL, width = NULL, height = NULL, vcodec = NULL,
             acodec = NULL, bitrate = NULL, fps = NULL,
             error = NULL, thumb_error = NULL, strip = NULL, strip_error = NULL,
             probed_at = NULL,
             bvid = ?, pubdate = ?, description = ?
           WHERE id = ?""",
        (
            root["label"], size, mtime, name, title, nkey, collection, rel_dir,
            kind, ext, meta.get("bvid") or None, meta.get("pubdate") or None,
            meta.get("description") or None, row["id"],
        ),
    )


def walk_media(conn: sqlite3.Connection, cfg: dict, root: dict, st: State):
    base = root["path"]
    min_size = int(
        root.get("min_size_mb", cfg.get("default_min_size_mb", 1)) * 1024 * 1024
    )
    excludes = {n.lower() for n in cfg.get("exclude_names", [])}
    stack = [base]
    while stack:
        dirpath = stack.pop()
        try:
            with os.scandir(dirpath) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name.lower() in excludes:
                                continue
                            if entry.is_symlink():
                                continue
                            is_junction = getattr(entry, "is_junction", None)
                            if is_junction and is_junction():
                                continue
                            if os.name == "nt":
                                try:
                                    attrs = entry.stat(
                                        follow_symlinks=False
                                    ).st_file_attributes
                                    if attrs & 0x400:  # reparse point
                                        continue
                                except OSError:
                                    continue
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            st.files_seen += 1
                            st.current = entry.path
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in MEDIA_EXT:
                                s = entry.stat(follow_symlinks=False)
                                st.bytes_seen += s.st_size
                                if s.st_size >= min_size:
                                    yield (
                                        entry.path,
                                        rel_dir_of(dirpath, base),
                                        s.st_size,
                                        s.st_mtime,
                                    )
                    except OSError:
                        continue
                    if time.time() - st.last_publish > 0.7:
                        st.publish(conn, force=True)
        except OSError:
            continue
    st.current = ""


def scan_roots(
    conn: sqlite3.Connection, cfg: dict, st: State, only_root: str | None = None
) -> None:
    st.phase = "scan"
    st.phase_done = 0
    st.phase_total = 0
    st.files_seen = 0
    st.bytes_seen = 0
    st.current = ""
    st.publish(conn, force=True)
    for root in cfg["roots"]:
        if only_root and root["label"] != only_root:
            continue
        base = root["path"]
        if not os.path.isdir(base):
            log(f"跳过不存在的目录: {base}")
            continue
        log(f"清点: {base}")
        seen = set()
        for path, rel_dir, size, mtime in walk_media(conn, cfg, root, st):
            seen.add(path)
            upsert_media(conn, root, path, rel_dir, size, mtime)
        conn.commit()
        rows = conn.execute(
            "SELECT id, path FROM media WHERE root = ? AND status != 'missing'",
            (root["label"],),
        ).fetchall()
        missing = [r["id"] for r in rows if r["path"] not in seen]
        if missing:
            conn.executemany(
                "UPDATE media SET status = 'missing' WHERE id = ?",
                [(i,) for i in missing],
            )
            conn.commit()
        log(f"  {root['label']}: 命中 {len(seen)} 个媒体，标记消失 {len(missing)} 个")

    if not only_root:
        labels = [r["label"] for r in cfg.get("roots", [])]
        if labels:
            marks = ",".join("?" for _ in labels)
            conn.execute(
                f"""UPDATE media SET status = 'missing'
                    WHERE status != 'missing' AND root NOT IN ({marks})""",
                labels,
            )
        else:
            conn.execute(
                "UPDATE media SET status = 'missing' WHERE status != 'missing'"
            )
        conn.commit()
    st.current = ""
    st.publish(conn, force=True)


def quick_sig(path: str, size: int) -> str | None:
    h = hashlib.blake2b(digest_size=16)
    h.update(str(size).encode("ascii"))
    chunk = 1024 * 1024
    try:
        with open(path, "rb") as f:
            if size <= 3 * chunk:
                while True:
                    b = f.read(chunk)
                    if not b:
                        break
                    h.update(b)
            else:
                h.update(f.read(chunk))
                f.seek(size // 2)
                h.update(f.read(64 * 1024))
                f.seek(size - chunk)
                h.update(f.read(chunk))
    except OSError:
        return None
    return h.hexdigest()


def dedupe(conn: sqlite3.Connection, st: State) -> None:
    st.phase = "dedupe"
    st.phase_done = 0
    st.phase_total = 0
    st.publish(conn, force=True)
    rows = conn.execute(
        "SELECT id, path, size, sig FROM media WHERE status != 'missing'"
    ).fetchall()
    by_size = defaultdict(list)
    for r in rows:
        by_size[r["size"]].append(r)
    candidates = [r for group in by_size.values() if len(group) > 1 for r in group]
    st.phase_total = len(candidates)
    for r in candidates:
        if not r["sig"]:
            sig = quick_sig(r["path"], r["size"])
            if sig:
                conn.execute("UPDATE media SET sig = ? WHERE id = ?", (sig, r["id"]))
        st.phase_done += 1
        st.publish(conn)
    conn.commit()

    conn.execute("UPDATE media SET dup_of = NULL")
    groups = defaultdict(list)
    for r in conn.execute(
        "SELECT id, path, size, sig FROM media WHERE status != 'missing' AND sig IS NOT NULL"
    ).fetchall():
        groups[(r["size"], r["sig"])].append(r)
    dup_count = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        canonical = min(group, key=lambda r: (len(r["path"]), r["id"]))
        for r in group:
            if r["id"] != canonical["id"]:
                conn.execute(
                    "UPDATE media SET dup_of = ? WHERE id = ?",
                    (canonical["id"], r["id"]),
                )
                dup_count += 1
    conn.commit()
    log(f"重复检查完成：{dup_count} 个重复项")
    st.phase_done = st.phase_total
    st.publish(conn, force=True)


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        timeout=timeout,
        creationflags=(NO_WINDOW | BELOW_NORMAL) if os.name == "nt" else 0,
    )


def _fnum(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fps(value) -> float | None:
    if not value or "/" not in str(value):
        v = _fnum(value)
        return v or None
    a, b = str(value).split("/", 1)
    a, b = _fnum(a), _fnum(b)
    return round(a / b, 3) if b else None


def probe_one(conn: sqlite3.Connection, cfg: dict, row: sqlite3.Row) -> None:
    cmd = [
        cfg["ffprobe"], "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", row["path"],
    ]
    try:
        p = _run(cmd, 45)
        if p.returncode != 0:
            raise RuntimeError((p.stderr or b"").decode("utf-8", "replace").strip())
        data = json.loads((p.stdout or b"{}").decode("utf-8", "replace"))
    except Exception as exc:
        msg = str(exc).strip().replace("\n", " ")[:500] or "ffprobe 失败"
        conn.execute(
            "UPDATE media SET status = 'error', error = ? WHERE id = ?",
            (msg, row["id"]),
        )
        return

    fmt = data.get("format") or {}
    streams = data.get("streams") or []
    vid = next(
        (
            s for s in streams
            if s.get("codec_type") == "video"
            and not (s.get("disposition") or {}).get("attached_pic")
        ),
        None,
    )
    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = _fnum(fmt.get("duration"))
    if not duration:
        duration = max(
            [_fnum(s.get("duration")) for s in streams] + [0.0]
        )
    kind = "video" if vid else ("audio" if aud else row["kind"])
    bitrate = int(
        _fnum(fmt.get("bit_rate")) or _fnum((vid or aud or {}).get("bit_rate"))
    )
    conn.execute(
        """UPDATE media SET
             duration = ?, width = ?, height = ?, vcodec = ?, acodec = ?,
             bitrate = ?, fps = ?, kind = ?, status = 'probed',
             probed_at = ?, error = NULL
           WHERE id = ?""",
        (
            round(duration, 3) if duration else None,
            int(_fnum(vid.get("width"))) if vid else None,
            int(_fnum(vid.get("height"))) if vid else None,
            vid.get("codec_name") if vid else None,
            aud.get("codec_name") if aud else None,
            bitrate or None,
            _fps(vid.get("avg_frame_rate")) if vid else None,
            kind,
            now(),
            row["id"],
        ),
    )


def find_cover(path: str) -> Path | None:
    p = Path(path)
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        cand = p.with_suffix(ext)
        if cand.is_file():
            return cand
    for name in ("poster.jpg", "cover.jpg", "folder.jpg"):
        cand = p.parent / name
        if cand.is_file():
            return cand
    return None


def _ffmpeg_ok(cmd: list[str], out: Path, timeout: int = 75) -> bool:
    try:
        p = _run(cmd, timeout)
    except Exception:
        return False
    if p.returncode != 0:
        if out.exists():
            try:
                out.unlink()
            except OSError:
                pass
        return False
    return out.exists() and out.stat().st_size > 100


def make_thumb(conn: sqlite3.Connection, cfg: dict, row: sqlite3.Row) -> None:
    ffmpeg = cfg["ffmpeg"]
    out = THUMBS / f"{row['id']}.jpg"
    cover = find_cover(row["path"])
    used_cover = str(cover) if cover else None
    ok = False

    base = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]

    if cover:
        ok = _ffmpeg_ok(
            base + ["-i", str(cover), "-frames:v", "1",
                    "-vf", "scale=640:-2", "-q:v", "3", str(out)],
            out,
        )

    if not ok and row["kind"] == "video":
        duration = row["duration"] or 0
        t = 1.0 if duration <= 3 else min(max(duration * 0.15, 1.0), 120.0)
        for ts in (t, 1.0, 3.0):
            ok = _ffmpeg_ok(
                base + ["-ss", f"{ts:.2f}", "-i", row["path"], "-frames:v", "1",
                        "-vf", "scale=640:-2", "-q:v", "4", str(out)],
                out,
            )
            if ok:
                break

    if not ok and row["kind"] == "audio":
        ok = _ffmpeg_ok(
            base + ["-i", row["path"], "-an", "-frames:v", "1",
                    "-vf", "scale=640:-2", "-q:v", "3", str(out)],
            out,
        )
        if not ok:
            ok = _ffmpeg_ok(
                base + ["-i", row["path"],
                        "-filter_complex", "showwavespic=s=640x360:colors=0xC9A227",
                        "-frames:v", "1", "-q:v", "3", str(out)],
                out,
            )

    if ok:
        conn.execute(
            """UPDATE media SET thumb = ?, cover_src = ?, status = 'ready',
                               thumb_error = NULL WHERE id = ?""",
            (f"{row['id']}.jpg", used_cover, row["id"]),
        )
    else:
        conn.execute(
            """UPDATE media SET status = 'ready', thumb = NULL,
                               thumb_error = ? WHERE id = ?""",
            ("封面生成失败", row["id"]),
        )


def make_strip(conn: sqlite3.Connection, cfg: dict, row: sqlite3.Row) -> None:
    """把 6 帧采样拼成一张 3×2 的接触印样。"""
    ffmpeg = cfg["ffmpeg"]
    out = STRIPS / f"{row['id']}.jpg"
    duration = row["duration"] or 0
    if duration > 2:
        cap = max(0.5, duration - 0.5)
        times = [
            min(max(duration * f, 0.5), cap)
            for f in (0.08, 0.24, 0.40, 0.56, 0.72, 0.88)
        ]
    else:
        times = [0.5] * 6

    args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for t in times:
        args += ["-ss", f"{t:.3f}", "-i", row["path"]]
    filters = [
        f"[{i}:v]scale=320:180:force_original_aspect_ratio=increase,"
        f"crop=320:180,setsar=1[v{i}]"
        for i in range(6)
    ]
    graph = ";".join(filters)
    graph += (
        ";[v0][v1][v2]hstack=inputs=3[top]"
        ";[v3][v4][v5]hstack=inputs=3[bottom]"
        ";[top][bottom]vstack=inputs=2[out]"
    )
    args += [
        "-filter_complex", graph, "-map", "[out]",
        "-frames:v", "1", "-q:v", "4", str(out),
    ]
    ok = _ffmpeg_ok(args, out, timeout=150)
    if ok:
        conn.execute(
            "UPDATE media SET strip = ?, strip_error = NULL WHERE id = ?",
            (f"{row['id']}.jpg", row["id"]),
        )
    else:
        conn.execute(
            "UPDATE media SET strip_error = ? WHERE id = ?",
            ("接触印样生成失败", row["id"]),
        )


def ensure_running(conn: sqlite3.Connection, st: State) -> bool:
    """返回 False 表示外部要求停止/出错；暂停时阻塞直到恢复。"""
    while True:
        ctrl = read_control()
        if not ctrl.get("paused"):
            if st.paused:
                st.paused = False
                if st.pause_phase:
                    st.phase = st.pause_phase
                st.publish(conn, force=True)
            return True
        if st.phase != "paused":
            st.pause_phase = st.phase
        st.paused = True
        st.phase = "paused"
        st.publish(conn, force=True)
        time.sleep(1.0)


def process_pending(
    conn: sqlite3.Connection,
    cfg: dict,
    st: State,
    only_root: str | None = None,
    limit: int | None = None,
) -> None:
    where = "status = 'new'" + (" AND root = ?" if only_root else "")
    params = (only_root,) if only_root else ()
    rows = conn.execute(
        f"SELECT id, path, kind, duration FROM media WHERE {where} ORDER BY id",
        params,
    ).fetchall()
    if limit:
        rows = rows[:limit]

    st.phase = "probe"
    st.phase_done = 0
    st.phase_total = len(rows)
    st.publish(conn, force=True)
    for row in rows:
        if not ensure_running(conn, st):
            return
        st.current = row["path"]
        st.publish(conn, force=True)
        probe_one(conn, cfg, row)
        conn.commit()
        st.phase_done += 1
        st.publish(conn, force=True)
        if st.phase_done % 10 == 0:
            log(f"识别 {st.phase_done}/{st.phase_total}")

    where = "status = 'probed'" + (" AND root = ?" if only_root else "")
    rows = conn.execute(
        f"SELECT id, path, kind, duration FROM media WHERE {where} ORDER BY id",
        params,
    ).fetchall()
    if limit:
        rows = rows[:limit]

    st.phase = "thumb"
    st.phase_done = 0
    st.phase_total = len(rows)
    st.publish(conn, force=True)
    for row in rows:
        if not ensure_running(conn, st):
            return
        st.current = row["path"]
        st.publish(conn, force=True)
        make_thumb(conn, cfg, row)
        conn.commit()
        st.phase_done += 1
        st.publish(conn, force=True)
        if st.phase_done % 10 == 0:
            log(f"封面 {st.phase_done}/{st.phase_total}")

    strip_where = (
        "status = 'ready' AND kind = 'video' AND strip IS NULL "
        "AND strip_error IS NULL"
    )
    if only_root:
        strip_where += " AND root = ?"
    rows = conn.execute(
        f"SELECT id, path, kind, duration FROM media WHERE {strip_where} ORDER BY id",
        params,
    ).fetchall()
    if limit:
        rows = rows[:limit]

    st.phase = "strip"
    st.phase_done = 0
    st.phase_total = len(rows)
    st.publish(conn, force=True)
    for row in rows:
        if not ensure_running(conn, st):
            return
        st.current = row["path"]
        st.publish(conn, force=True)
        make_strip(conn, cfg, row)
        conn.commit()
        st.phase_done += 1
        st.publish(conn, force=True)
        if st.phase_done % 10 == 0:
            log(f"接触印样 {st.phase_done}/{st.phase_total}")
    st.current = ""


def full_pass(
    conn: sqlite3.Connection,
    cfg: dict,
    st: State,
    only_root: str | None = None,
    limit: int | None = None,
) -> None:
    scan_roots(conn, cfg, st, only_root)
    if only_root:
        return
    dedupe(conn, st)
    process_pending(conn, cfg, st, None, limit)
    st.last_scan_at = now()
    save_last_scan(conn, st.last_scan_at)


def take_rescan() -> bool:
    ctrl = read_control()
    if ctrl.get("rescan"):
        ctrl["rescan"] = False
        write_control(ctrl)
        return True
    return False


def watch_loop(
    conn: sqlite3.Connection,
    cfg: dict,
    st: State,
    only_root: str | None = None,
    limit: int | None = None,
) -> None:
    """常驻待命，只在收到手动巡检请求时扫描。"""
    st.phase = "idle"
    st.publish(conn, force=True)
    last_tick = 0.0
    while True:
        time.sleep(1.5)
        ctrl = read_control()
        if ctrl.get("paused"):
            if st.phase != "paused":
                st.pause_phase = st.phase
            st.paused = True
            st.phase = "paused"
            st.current = ""
            st.publish(conn, force=True)
            continue
        if st.paused:
            st.paused = False
            if st.pause_phase:
                st.phase = st.pause_phase
        if ctrl.get("rescan"):
            take_rescan()
            try:
                cfg = load_config()
            except Exception as exc:
                log(f"配置读取失败: {exc}")
                st.phase = "error"
                st.current = str(exc)[:300]
                st.publish(conn, force=True)
                continue
            log("手动巡检开始")
            full_pass(conn, cfg, st, only_root, limit)
            st.phase = "idle"
            st.current = ""
            st.publish(conn, force=True)
            last_tick = 0.0
            continue
        st.phase = "idle"
        if time.time() - last_tick > 3.0:
            last_tick = time.time()
            st.publish(conn, force=True)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="片匣后台索引器")
    ap.add_argument(
        "--watch", action="store_true",
        help="常驻；首次部署自动巡检一次，之后等待手动巡检",
    )
    ap.add_argument("--once", action="store_true", help="只跑一轮")
    ap.add_argument(
        "--no-initial", action="store_true",
        help="即使首次部署也不做启动扫描",
    )
    ap.add_argument("--only-root", help="只处理指定根目录标签（调试用）")
    ap.add_argument("--limit", type=int, help="每个阶段最多处理 N 项（调试用）")
    args = ap.parse_args()
    if not args.watch:
        args.once = True

    lower_priority()
    cfg = load_config()
    conn = open_db()
    PID_PATH.write_text(str(os.getpid()), encoding="ascii")
    st = State()
    st.last_scan_at = load_last_scan(conn)
    first_run = not has_completed_scan(conn)

    try:
        if args.only_root:
            scan_roots(conn, cfg, st, args.only_root)
            process_pending(conn, cfg, st, args.only_root, args.limit)
        elif args.no_initial:
            log("跳过启动扫描，等待手动巡检")
        elif args.once:
            full_pass(conn, cfg, st, None, args.limit)
        elif first_run:
            log("首次部署：自动执行一次巡检")
            full_pass(conn, cfg, st, None, args.limit)
        else:
            log("已有索引，跳过启动扫描，等待手动巡检")
        if args.watch:
            watch_loop(conn, cfg, st, args.only_root, args.limit)
        else:
            st.phase = "idle"
            st.phase_done = st.phase_total
            st.publish(conn, force=True)
    except KeyboardInterrupt:
        st.phase = "idle"
        st.publish(conn, force=True)
        log("收到退出信号")
    except Exception as exc:
        st.phase = "error"
        st.current = str(exc)[:300]
        st.publish(conn, force=True)
        log(f"索引器异常: {exc!r}")
        raise
    finally:
        conn.close()
        try:
            if PID_PATH.read_text(encoding="ascii").strip() == str(os.getpid()):
                PID_PATH.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
