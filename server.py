#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""片匣 · 本地媒体库：Web 服务

只绑定 127.0.0.1。提供页面、查询 API、缩略图、Range 视频流，
以及“用本地播放器打开”“暂停/继续索引”等本机操作。
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
WEB = BASE / "web"
THUMBS = BASE / "thumbs"
STRIPS = BASE / "strips"
DB_PATH = DATA / "library.db"
STATUS_PATH = DATA / "status.json"
CONTROL_PATH = DATA / "control.json"
PID_PATH = DATA / "server.pid"
CFG_PATH = BASE / "config.json"

def load_config() -> dict:
    if not CFG_PATH.exists():
        example = BASE / "config.example.json"
        if not example.exists():
            raise FileNotFoundError(
                "config.json is missing and config.example.json was not found"
            )
        CFG_PATH.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
    roots = []
    for root in cfg.get("roots", []):
        if not isinstance(root, dict) or not isinstance(root.get("path"), str):
            continue
        root["path"] = os.path.normpath(
            os.path.expanduser(os.path.expandvars(root["path"]))
        )
        roots.append(root)
    cfg["roots"] = roots
    cfg.setdefault("ffmpeg", "ffmpeg")
    cfg.setdefault("ffprobe", "ffprobe")
    return cfg


CFG = load_config()
PORT = int(CFG.get("port", 8765))

MEDIA_MIME = {
    ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm",
    ".ogv": "video/ogg", ".mkv": "video/x-matroska", ".avi": "video/x-msvideo",
    ".mov": "video/quicktime", ".flv": "video/x-flv", ".wmv": "video/x-ms-wmv",
    ".ts": "video/mp2t", ".mpg": "video/mpeg", ".mpeg": "video/mpeg",
    ".3gp": "video/3gpp", ".rmvb": "application/vnd.rn-realmedia-vbr",
    ".rm": "application/vnd.rn-realmedia", ".vob": "video/dvd", ".mts": "video/mp2t",
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".wav": "audio/wav", ".flac": "audio/flac", ".ogg": "audio/ogg",
    ".opus": "audio/ogg", ".wma": "audio/x-ms-wma", ".ape": "audio/x-ape",
    ".aiff": "audio/aiff", ".alac": "audio/mp4", ".m4b": "audio/mp4",
}

STATIC_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}

SORTS = {
    "recent": "m.added_at DESC, m.id DESC",
    "name": "m.name_key ASC, m.id ASC",
    "duration": "m.duration DESC, m.id DESC",
    "size": "m.size DESC, m.id DESC",
}


def now() -> float:
    return time.time()


def write_json_atomic(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


_roots_cache = {"mtime": None, "roots": []}


def current_roots() -> list:
    try:
        mtime = CFG_PATH.stat().st_mtime
        if _roots_cache["mtime"] != mtime:
            _roots_cache["roots"] = load_config().get("roots", [])
            _roots_cache["mtime"] = mtime
        return _roots_cache["roots"]
    except Exception:
        return CFG.get("roots", [])


def under_roots(path: str) -> bool:
    p = os.path.normcase(os.path.abspath(path))
    for root in current_roots():
        base = os.path.normcase(os.path.abspath(root["path"]))
        if p == base or p.startswith(base + os.sep):
            return True
    return False


def open_path(target: str) -> None:
    if os.name == "nt":
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class Handler(BaseHTTPRequestHandler):
    server_version = "CineShelf/1.0"

    # ---------- 基础响应 ----------

    def log_message(self, fmt, *args):
        pass

    def send_json(self, obj, status: int = 200, head: bool = False) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def send_error_json(self, status: int, message: str, head: bool = False) -> None:
        self.send_json({"ok": False, "error": message}, status, head)

    def send_bytes(self, path: Path, ctype: str, head: bool = False, cache: str = "no-cache") -> None:
        if not path.is_file():
            self.send_error_json(404, "not found", head)
            return
        size = path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if head:
            return
        try:
            with path.open("rb") as f:
                while True:
                    chunk = f.read(256 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    # ---------- 路由 ----------

    def do_GET(self):
        self.route(False)

    def do_HEAD(self):
        self.route(True)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 65536:
                self.send_error_json(413, "body too large")
                return
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(body, dict):
                body = {}
        except Exception:
            self.send_error_json(400, "invalid json")
            return
        if self.headers.get("X-Cine") != "1":
            self.send_error_json(403, "forbidden")
            return
        origin = self.headers.get("Origin")
        if origin and not (
            origin.startswith(f"http://127.0.0.1:{PORT}")
            or origin.startswith(f"http://localhost:{PORT}")
        ):
            self.send_error_json(403, "forbidden origin")
            return
        try:
            if path == "/api/open":
                self.api_open(body)
            elif path == "/api/control":
                self.api_control(body)
            elif path == "/api/delete":
                self.api_delete(body)
            else:
                self.send_error_json(404, "not found")
        except Exception as exc:
            self.send_error_json(500, str(exc))

    def route(self, head: bool) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if path.startswith("/api/"):
                self.api_get(path, query, head)
            elif path in ("/", "/index.html"):
                self.send_bytes(WEB / "index.html", STATIC_MIME[".html"], head)
            elif path.startswith("/static/"):
                name = path[len("/static/"):]
                if not name or "/" in name or "\\" in name or name.startswith("."):
                    self.send_error_json(404, "not found", head)
                    return
                ctype = STATIC_MIME.get(Path(name).suffix.lower(), "application/octet-stream")
                self.send_bytes(WEB / name, ctype, head)
            elif path == "/favicon.ico":
                self.serve_favicon(head)
            else:
                self.send_error_json(404, "not found", head)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return
        except Exception as exc:
            try:
                self.send_error_json(500, str(exc), head)
            except Exception:
                pass

    def serve_favicon(self, head: bool) -> None:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="10" fill="#120f0c"/>'
            '<rect x="10" y="12" width="44" height="40" rx="4" fill="none" '
            'stroke="#c8402e" stroke-width="3"/>'
            '<circle cx="25" cy="26" r="4" fill="#c9a227"/>'
            '<circle cx="39" cy="26" r="4" fill="#c9a227"/>'
            '<circle cx="25" cy="40" r="4" fill="#c9a227"/>'
            '<circle cx="39" cy="40" r="4" fill="#c9a227"/></svg>'
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(svg)))
        self.send_header("Cache-Control", "max-age=86400")
        self.end_headers()
        if not head:
            self.wfile.write(svg)

    # ---------- API ----------

    def api_get(self, path: str, query: dict, head: bool) -> None:
        if path == "/api/health":
            self.send_json({"ok": True, "name": "片匣", "time": now()}, 200, head)
        elif path == "/api/status":
            self.api_status(head)
        elif path == "/api/facets":
            self.api_facets(head)
        elif path == "/api/items":
            self.api_items(query, head)
        elif path.startswith("/api/item/"):
            self.api_item(path, head)
        elif path.startswith("/api/thumb/"):
            self.api_thumb(path, head)
        elif path.startswith("/api/strip/"):
            self.api_strip(path, head)
        elif path.startswith("/api/stream/"):
            self.api_stream(path, head)
        else:
            self.send_error_json(404, "not found", head)

    def api_status(self, head: bool) -> None:
        status = read_json(STATUS_PATH) or {}
        age = None
        if status.get("updated_at"):
            age = round(now() - status["updated_at"], 1)
        payload = dict(status) if status else {}
        payload["running"] = bool(status) and age is not None and age < 180
        payload["status_age_sec"] = age
        payload["server_time"] = now()
        if not payload.get("stats"):
            conn = db()
            try:
                row = conn.execute(
                    """SELECT COUNT(*) AS total,
                              SUM(CASE WHEN kind='video' THEN 1 ELSE 0 END) AS videos,
                              SUM(CASE WHEN kind='audio' THEN 1 ELSE 0 END) AS audio,
                              SUM(COALESCE(size,0)) AS total_size,
                              SUM(COALESCE(duration,0)) AS total_duration,
                              SUM(CASE WHEN dup_of IS NOT NULL THEN 1 ELSE 0 END) AS duplicates
                       FROM media WHERE status != 'missing'"""
                ).fetchone()
                payload["stats"] = {k: (v or 0) for k, v in dict(row).items()}
            except sqlite3.Error:
                payload["stats"] = {}
            finally:
                conn.close()
        self.send_json(payload, 200, head)

    def api_facets(self, head: bool) -> None:
        conn = db()
        try:
            collections = [
                dict(r) for r in conn.execute(
                    """SELECT collection AS name, COUNT(*) AS count
                       FROM media
                       WHERE status != 'missing' AND dup_of IS NULL
                       GROUP BY collection ORDER BY count DESC, name ASC"""
                ).fetchall()
            ]
            roots = [
                dict(r) for r in conn.execute(
                    """SELECT root AS name, COUNT(*) AS count
                       FROM media
                       WHERE status != 'missing' AND dup_of IS NULL
                       GROUP BY root ORDER BY count DESC, name ASC"""
                ).fetchall()
            ]
        except sqlite3.Error:
            collections, roots = [], []
        finally:
            conn.close()
        self.send_json({"collections": collections, "roots": roots}, 200, head)

    def api_items(self, query: dict, head: bool) -> None:
        def q1(name: str, default: str = "") -> str:
            return (query.get(name) or [default])[0]

        search = q1("q").strip()
        kind = q1("kind")
        collection = q1("collection")
        sort = q1("sort", "recent")
        include_dups = q1("dup") == "1"
        try:
            offset = max(0, int(q1("offset", "0")))
            limit = min(96, max(1, int(q1("limit", "48"))))
        except ValueError:
            offset, limit = 0, 48
        order = SORTS.get(sort, SORTS["recent"])

        where = ["m.status != 'missing'"]
        params: list = []
        if not include_dups:
            where.append("m.dup_of IS NULL")
        if kind in ("video", "audio"):
            where.append("m.kind = ?")
            params.append(kind)
        if collection:
            where.append("m.collection = ?")
            params.append(collection)
        if search:
            like = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            where.append(
                "(m.title LIKE ? ESCAPE '\\' OR m.name LIKE ? ESCAPE '\\' "
                "OR m.description LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like])
        clause = " AND ".join(where)

        conn = db()
        try:
            total = conn.execute(
                f"SELECT COUNT(*) FROM media m WHERE {clause}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"""SELECT m.id, m.title, m.name, m.kind, m.ext, m.size,
                           m.duration, m.width, m.height, m.collection, m.root,
                           m.rel_dir, m.thumb, m.strip, m.dup_of, m.status, m.added_at,
                           m.bvid,
                           (SELECT COUNT(*) FROM media d WHERE d.dup_of = m.id) AS dup_count
                    FROM media m
                    WHERE {clause}
                    ORDER BY {order}
                    LIMIT ? OFFSET ?""",
                params + [limit, offset],
            ).fetchall()
            items = [dict(r) for r in rows]
        except sqlite3.Error as exc:
            self.send_error_json(500, str(exc), head)
            return
        finally:
            conn.close()
        self.send_json(
            {"items": items, "total": total, "offset": offset, "limit": limit},
            200,
            head,
        )

    def api_item(self, path: str, head: bool) -> None:
        try:
            item_id = int(path.rsplit("/", 1)[1])
        except ValueError:
            self.send_error_json(400, "bad id", head)
            return
        conn = db()
        try:
            row = conn.execute(
                """SELECT id, path, root, collection, rel_dir, name, title, kind,
                          ext, size, mtime, duration, width, height, vcodec, acodec,
                          bitrate, fps, thumb, strip, status, error, thumb_error, bvid,
                          pubdate, description, added_at, probed_at, dup_of
                   FROM media WHERE id = ?""",
                (item_id,),
            ).fetchone()
        except sqlite3.Error as exc:
            self.send_error_json(500, str(exc), head)
            return
        finally:
            conn.close()
        if not row or row["status"] == "missing":
            self.send_error_json(404, "not found", head)
            return
        self.send_json(dict(row), 200, head)

    def api_thumb(self, path: str, head: bool) -> None:
        try:
            item_id = int(path.rsplit("/", 1)[1])
        except ValueError:
            self.send_error_json(400, "bad id", head)
            return
        conn = db()
        try:
            row = conn.execute(
                "SELECT thumb FROM media WHERE id = ?", (item_id,)
            ).fetchone()
        finally:
            conn.close()
        if not row or not row["thumb"]:
            self.send_error_json(404, "no thumb", head)
            return
        target = (THUMBS / row["thumb"]).resolve()
        if target.parent != THUMBS.resolve():
            self.send_error_json(404, "no thumb", head)
            return
        self.send_bytes(target, "image/jpeg", head, "public, max-age=86400")

    def api_strip(self, path: str, head: bool) -> None:
        try:
            item_id = int(path.rsplit("/", 1)[1])
        except ValueError:
            self.send_error_json(400, "bad id", head)
            return
        conn = db()
        try:
            row = conn.execute(
                "SELECT strip FROM media WHERE id = ?", (item_id,)
            ).fetchone()
        finally:
            conn.close()
        if not row or not row["strip"]:
            self.send_error_json(404, "no strip", head)
            return
        target = (STRIPS / row["strip"]).resolve()
        if target.parent != STRIPS.resolve():
            self.send_error_json(404, "no strip", head)
            return
        self.send_bytes(target, "image/jpeg", head, "public, max-age=86400")

    def api_stream(self, path: str, head: bool) -> None:
        try:
            item_id = int(path.rsplit("/", 1)[1])
        except ValueError:
            self.send_error_json(400, "bad id", head)
            return
        conn = db()
        try:
            row = conn.execute(
                "SELECT path, ext, status FROM media WHERE id = ?", (item_id,)
            ).fetchone()
        finally:
            conn.close()
        if not row or row["status"] == "missing":
            self.send_error_json(404, "not found", head)
            return
        file_path = row["path"]
        if not under_roots(file_path) or not os.path.isfile(file_path):
            self.send_error_json(404, "file missing", head)
            return
        ctype = MEDIA_MIME.get((row["ext"] or "").lower(), "application/octet-stream")
        self.stream_file(Path(file_path), ctype, head)

    def stream_file(self, path: Path, ctype: str, head: bool) -> None:
        size = path.stat().st_size
        range_header = self.headers.get("Range")
        start, end = 0, size - 1
        partial = False
        if range_header:
            m = re.match(r"bytes=(\d*)-(\d*)$", range_header.strip())
            if not m:
                self.send_error_json(416, "bad range", head)
                return
            a, b = m.group(1), m.group(2)
            if a == "" and b == "":
                self.send_error_json(416, "bad range", head)
                return
            if a == "":
                length = int(b)
                start = max(0, size - length)
                end = size - 1
            else:
                start = int(a)
                end = int(b) if b else size - 1
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            end = min(end, size - 1)
            partial = True
        length = end - start + 1
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if head:
            return
        try:
            with path.open("rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(256 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    # ---------- 本机操作 ----------

    def api_open(self, body: dict) -> None:
        try:
            item_id = int(body.get("id"))
        except (TypeError, ValueError):
            self.send_error_json(400, "bad id")
            return
        action = body.get("action") or "play"
        conn = db()
        try:
            row = conn.execute(
                "SELECT path, status FROM media WHERE id = ?", (item_id,)
            ).fetchone()
        finally:
            conn.close()
        if not row or row["status"] == "missing":
            self.send_error_json(404, "not found")
            return
        target = row["path"] if action == "play" else os.path.dirname(row["path"])
        if not os.path.exists(target):
            self.send_error_json(404, "missing on disk")
            return
        open_path(target)
        self.send_json({"ok": True})

    def api_control(self, body: dict) -> None:
        action = body.get("action")
        ctrl = read_json(CONTROL_PATH) or {}
        if action == "pause":
            ctrl["paused"] = True
        elif action == "resume":
            ctrl["paused"] = False
        elif action == "rescan":
            ctrl["paused"] = False
            ctrl["rescan"] = True
        else:
            self.send_error_json(400, "unknown action")
            return
        write_json_atomic(CONTROL_PATH, ctrl)
        self.send_json({"ok": True, "control": ctrl})

    def api_delete(self, body: dict) -> None:
        try:
            item_id = int(body.get("id"))
        except (TypeError, ValueError):
            self.send_error_json(400, "bad id")
            return

        conn = db()
        try:
            row = conn.execute(
                "SELECT path, thumb, strip, dup_of FROM media WHERE id = ?",
                (item_id,),
            ).fetchone()
            if not row:
                self.send_error_json(404, "not_found")
                return
            path = row["path"]
            if not under_roots(path):
                self.send_error_json(403, "outside_roots")
                return
            if os.path.isdir(path):
                self.send_error_json(400, "is_directory")
                return
            if os.path.exists(path):
                for attempt in range(3):
                    if not os.path.exists(path):
                        break
                    try:
                        os.remove(path)
                        break
                    except FileNotFoundError:
                        break
                    except PermissionError:
                        if attempt == 2:
                            self.send_error_json(409, "in_use")
                            return
                        time.sleep(0.35)
                    except OSError as exc:
                        self.send_error_json(500, f"delete_failed:{exc}")
                        return

            for base, name in ((THUMBS, row["thumb"]), (STRIPS, row["strip"])):
                if not name:
                    continue
                target = (base / name).resolve()
                if target.parent == base.resolve() and target.is_file():
                    try:
                        target.unlink()
                    except OSError:
                        pass

            # 如果删掉的是某个重复组的主项，把其中一个副本扶正
            dups = conn.execute(
                "SELECT id FROM media WHERE dup_of = ?", (item_id,)
            ).fetchall()
            if dups:
                new_canon = dups[0]["id"]
                conn.execute(
                    "UPDATE media SET dup_of = NULL WHERE id = ?", (new_canon,)
                )
                conn.execute(
                    "UPDATE media SET dup_of = ? WHERE dup_of = ? AND id != ?",
                    (new_canon, item_id, new_canon),
                )
            conn.execute("DELETE FROM media WHERE id = ?", (item_id,))
            conn.commit()
        except sqlite3.Error as exc:
            self.send_error_json(500, f"db_error:{exc}")
            return
        finally:
            conn.close()
        self.send_json({"ok": True, "deleted": True})


def main() -> int:
    global PORT
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="片匣 Web 服务")
    ap.add_argument("--port", type=int, default=None)
    args = ap.parse_args()
    if args.port:
        PORT = args.port
    DATA.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()), encoding="ascii")
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    httpd.daemon_threads = True
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 片匣服务已启动: http://127.0.0.1:{PORT}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        try:
            if PID_PATH.read_text(encoding="ascii").strip() == str(os.getpid()):
                PID_PATH.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
