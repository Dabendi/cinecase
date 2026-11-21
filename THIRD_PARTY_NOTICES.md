# Third-party notices

## CineCase

MIT License. See `LICENSE`.

## FFmpeg / FFprobe

The portable Windows build bundles FFmpeg and FFprobe from the
[BtbN FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) project
(`ffmpeg-master-latest-win64-lgpl-shared`).

- FFmpeg is licensed under the **GNU Lesser General Public License v3**.
- The full license text is included in the portable build at
  `_internal/ffmpeg/LICENSE.txt`.
- FFmpeg source: https://github.com/FFmpeg/FFmpeg
- Build scripts and patches: https://github.com/BtbN/FFmpeg-Builds

This application uses FFmpeg for local decoding/probing only. No network
services are involved.

## Microsoft Edge WebView2

The portable Windows build bundles the Microsoft Edge WebView2 Evergreen
Bootstrapper so that a machine without the WebView2 Runtime can install it.
The bootstrapper is signed by Microsoft Corporation.

WebView2 is subject to Microsoft's terms and privacy statements:
https://developer.microsoft.com/microsoft-edge/webview2/

## Python

The desktop executable is built with PyInstaller and bundles the CPython
runtime and standard library under the Python Software Foundation License.
