片匣 / CineCase — macOS 便携版 / Portable macOS build
========================================================

中文
----
1. 解压后打开 CineCase.app。可以拖进“应用程序”再打开。
2. 首次打开如果被 macOS 拦截（未识别开发者 / 已损坏）：
   - 在 Finder 里右键 CineCase.app → 打开 → 再点“打开”；或
   - 在终端执行一次：
     xattr -dr com.apple.quarantine /Applications/CineCase.app
     （如果 App 不在“应用程序”，换成实际路径）
   这个包是 ad-hoc 签名、没有 Apple Developer 公证，所以第一次需要这一步。
3. macOS 使用系统 WebKit，不需要 WebView2。
4. 数据在 ~/Library/Application Support/CineCase：
   config.json、data/、thumbs/、strips/、webview/。
   首次启动会自动巡检一次，默认扫描 ~/Videos、~/Movies、~/Downloads；
   之后只有点“手动巡检 / Scan now”才扫描。
   想在首次扫描前选目录，先把 config.example.json 复制为
   ~/Library/Application Support/CineCase/config.json 并改 roots。
5. ffmpeg / ffprobe 已内置（ffmpeg-static，见 THIRD_PARTY_NOTICES.md）。
6. 关闭窗口即停止本地服务和索引器。

English
-------
1. Unzip and open CineCase.app (you can move it to Applications first).
2. If macOS blocks the first launch (unidentified developer / damaged):
   - Right-click CineCase.app -> Open -> Open; or
   - Run once in Terminal:
     xattr -dr com.apple.quarantine /Applications/CineCase.app
     (use the real path if the app is elsewhere)
   This build is ad-hoc signed, not notarized, so the first launch needs this.
3. macOS uses the system WebKit; WebView2 is not needed.
4. Data lives in ~/Library/Application Support/CineCase:
   config.json, data/, thumbs/, strips/, webview/.
   The first launch auto-scans ~/Videos, ~/Movies, ~/Downloads once; after
   that, scanning is manual with "Scan now". To choose folders before the
   first scan, copy config.example.json to
   ~/Library/Application Support/CineCase/config.json and edit roots.
5. ffmpeg/ffprobe are bundled (ffmpeg-static; see THIRD_PARTY_NOTICES.md).
6. Close the window to stop the local server and indexer.
