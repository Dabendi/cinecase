片匣 / CineCase — 便携版 / Portable Windows build
=====================================================

中文
----
1. 双击 CineCase.exe。
2. Windows 11 自带 WebView2 Runtime。Windows 10 如果提示缺少 WebView2，
   按提示运行随附的 Microsoft Edge WebView2 安装程序，装好后重新打开片匣。
3. 首次启动会自动巡检一次。默认扫描 ~/Videos 和 ~/Downloads；如果想在
   首次扫描前使用自己的目录，先把 config.example.json 复制为 config.json，
   修改 roots，再启动 CineCase.exe。
4. 之后只有点页面上的“手动巡检 / Scan now”才会重新扫描；不会自动巡检。
5. 数据都在本文件夹：config.json、data/、thumbs/、strips/、webview/。
   删除它们可以重置索引，不会删除你的媒体文件。
6. 关闭窗口即停止本地服务和索引器。

ffmpeg / ffprobe 已内置（LGPL shared build），见 THIRD_PARTY_NOTICES.md。
本应用使用 MIT License。

English
-------
1. Double-click CineCase.exe.
2. Windows 11 includes WebView2. On Windows 10, if prompted, run the bundled
   Microsoft Edge WebView2 installer once, then open CineCase again.
3. The first launch performs one automatic scan, using ~/Videos and
   ~/Downloads by default. To use your own folders before that first scan,
   copy config.example.json to config.json, edit roots, then launch.
4. After the first scan, press "Scan now" to refresh; there is no automatic
   patrol.
5. Data lives in this folder: config.json, data/, thumbs/, strips/, webview/.
   Delete them to reset the index; your media files are untouched.
6. Close the window to stop the local server and indexer.

FFmpeg/ffprobe are bundled (LGPL shared build). See THIRD_PARTY_NOTICES.md.
The app is MIT licensed.
