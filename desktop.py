#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""片匣 · CineCase 桌面启动器

用 pywebview / WebView2 把现有的本地 Web UI 装进一个原生窗口。
打包后它同时充当 server/scanner 的分发入口：

    CineCase.exe                 -> 桌面窗口
    CineCase.exe --server ...    -> 只跑 Web 服务（内部使用）
    CineCase.exe --scanner ...   -> 只跑索引器（内部使用）
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
SOURCE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", SOURCE_DIR))

NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def choose_home() -> Path:
    env = os.environ.get("CINE_HOME")
    if env:
        return Path(env).expanduser().resolve()
    if FROZEN and sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CineCase"
    exe_dir = Path(sys.executable).resolve().parent if FROZEN else SOURCE_DIR
    pointer = exe_dir / "cinehome.txt"
    if pointer.exists():
        try:
            target = Path(pointer.read_text(encoding="utf-8").strip()).expanduser()
            if target:
                return target.resolve()
        except OSError:
            pass
    if not FROZEN:
        return SOURCE_DIR
    try:
        probe = exe_dir / ".cinecase-write-test"
        probe.write_text("ok", encoding="ascii")
        probe.unlink()
        return exe_dir
    except OSError:
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CineCase"


HOME = choose_home()
HOME.mkdir(parents=True, exist_ok=True)
os.environ["CINE_HOME"] = str(HOME)


def message_box(text: str, title: str = "片匣 · CineCase") -> None:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            escaped = text.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.run(
                [
                    "osascript", "-e",
                    f'display dialog "{escaped}" buttons {{"OK"}} '
                    f'default button 1 with title "{title}"',
                ],
                check=False,
            )
        except Exception:
            print(f"{title}: {text}", file=sys.stderr)
    else:
        print(f"{title}: {text}", file=sys.stderr)


def load_port() -> int:
    cfg_path = HOME / "config.json"
    if not cfg_path.exists():
        example = RESOURCE_DIR / "config.example.json"
        if example.exists():
            shutil.copyfile(example, cfg_path)
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return int(cfg.get("port", 8765))
    except Exception:
        return 8765


def health(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/health", timeout=1
        ) as response:
            return response.status == 200
    except Exception:
        return False


def webview2_installed() -> bool:
    if os.name != "nt":
        return True
    try:
        import winreg
        guid = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
        paths = (
            rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{guid}",
            rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{guid}",
        )
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for path in paths:
                try:
                    with winreg.OpenKey(root, path) as key:
                        version, _ = winreg.QueryValueEx(key, "pv")
                        if version:
                            return True
                except OSError:
                    pass
    except Exception:
        return True
    return False


def spawn(role: str, port: int):
    log_dir = HOME / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"desktop-{role}.log"
    log = open(log_path, "ab")
    env = os.environ.copy()
    env["CINE_HOME"] = str(HOME)
    env["PYTHONIOENCODING"] = "utf-8"

    if FROZEN:
        args = [sys.executable, f"--{role}"]
    else:
        args = [sys.executable, "-X", "utf8", str(SOURCE_DIR / "desktop.py"), f"--{role}"]
    if role == "server":
        args += ["--port", str(port)]
    else:
        args += ["--watch"]

    proc = subprocess.Popen(
        args,
        cwd=str(HOME),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=NO_WINDOW,
    )
    return proc, log


def wait_health(port: int, timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if health(port):
            return True
        time.sleep(0.25)
    return False


def apply_dark_titlebar() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes
        hwnd = 0
        for _ in range(20):
            time.sleep(0.5)
            hwnd = ctypes.windll.user32.FindWindowW(None, "片匣 · CineCase")
            if hwnd:
                break
        if not hwnd:
            return
        value = ctypes.c_int(1)
        for attr in (20, 19):  # immersive dark mode (Win10/Win11)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)
            )
        color = ctypes.c_int(0x00090B0D)  # COLORREF for #0d0b09
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(color), ctypes.sizeof(color)
        )
    except Exception:
        pass


def stop_process(proc: subprocess.Popen) -> None:
    try:
        if proc.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                creationflags=NO_WINDOW,
            )
        else:
            proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_desktop() -> int:
    if not webview2_installed():
        installer = RESOURCE_DIR / "webview2" / "MicrosoftEdgeWebView2Setup.exe"
        if installer.exists():
            message_box(
                "片匣需要 Microsoft Edge WebView2 Runtime。\n\n"
                "将打开随附的安装程序；安装完成后请重新打开片匣。"
            )
            try:
                subprocess.run([str(installer)], check=False)
            except Exception:
                pass
        else:
            message_box(
                "片匣需要 Microsoft Edge WebView2 Runtime。\n\n"
                "请先安装：\n"
                "https://developer.microsoft.com/microsoft-edge/webview2/"
            )
        return 1

    try:
        import webview
    except Exception as exc:
        message_box(
            "缺少桌面窗口依赖 pywebview。\n\n"
            "请先运行 build-desktop.ps1，或安装 pywebview 后再启动。\n\n"
            f"{exc}"
        )
        return 1

    port = load_port()
    started: list[tuple[subprocess.Popen, object]] = []
    try:
        if not health(port):
            server_proc, server_log = spawn("server", port)
            started.append((server_proc, server_log))
            if not wait_health(port):
                message_box(
                    f"本地服务没有在端口 {port} 启动成功。\n"
                    "请检查 config.json 的端口是否被占用，或查看 "
                    f"{HOME / 'data' / 'logs' / 'desktop-server.log'}。"
                )
                return 1
            scanner_proc, scanner_log = spawn("scanner", port)
            started.append((scanner_proc, scanner_log))

        icon_path = RESOURCE_DIR / "assets" / "cinecase.ico"
        window_icon = str(icon_path) if os.name == "nt" and icon_path.exists() else None
        webview.create_window(
            "片匣 · CineCase",
            f"http://127.0.0.1:{port}/",
            width=1280,
            height=860,
            min_size=(900, 600),
            background_color="#0d0b09",
        )
        threading.Thread(target=apply_dark_titlebar, daemon=True).start()
        webview.start(
            private_mode=False,
            storage_path=str(HOME / "webview"),
            icon=window_icon,
        )
        return 0
    except Exception as exc:
        message_box(f"桌面窗口启动失败：\n\n{exc}")
        return 1
    finally:
        for proc, log in started:
            stop_process(proc)
            try:
                log.close()
            except Exception:
                pass
        for name, proc in (("server.pid", started[0][0] if started else None),
                           ("scanner.pid", started[1][0] if len(started) > 1 else None)):
            if proc is None:
                continue
            try:
                pid_file = HOME / "data" / name
                if pid_file.read_text(encoding="ascii").strip() == str(proc.pid):
                    pid_file.unlink()
            except OSError:
                pass


def dispatch():
    argv = sys.argv[1:]
    if "--server" in argv:
        argv = [a for a in argv if a != "--server"]
        sys.argv = [sys.argv[0], *argv]
        import server
        return server.main()
    if "--scanner" in argv:
        argv = [a for a in argv if a != "--scanner"]
        sys.argv = [sys.argv[0], *argv]
        import scan
        return scan.main()
    return None


def main() -> int:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "CineCase.LocalMediaLibrary"
            )
        except Exception:
            pass
    result = dispatch()
    if result is not None:
        return result
    return run_desktop()


if __name__ == "__main__":
    raise SystemExit(main())
