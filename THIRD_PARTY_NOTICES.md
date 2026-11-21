# Third-party notices

## CineCase

MIT License. See `LICENSE`.

## FFmpeg / FFprobe

FFmpeg is used locally for probing and frame extraction only. No network
services are involved.

### Windows build

The Windows build bundles FFmpeg and FFprobe from the
[BtbN FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) project
(`ffmpeg-master-latest-win64-lgpl-shared`).

- FFmpeg is licensed under the **GNU Lesser General Public License v3**.
- The license text is included at `_internal/ffmpeg/LICENSE.txt`.
- FFmpeg source: https://github.com/FFmpeg/FFmpeg
- Build scripts and patches: https://github.com/BtbN/FFmpeg-Builds

### macOS build

The macOS builds bundle the `ffmpeg` and `ffprobe` binaries from
[ffmpeg-static](https://github.com/eugeneware/ffmpeg-static) release `b6.1.1`.

- The license text shipped with the binaries is included at
  `_internal/ffmpeg/LICENSE.txt`.
- FFmpeg source: https://github.com/FFmpeg/FFmpeg
- Binary distribution: https://github.com/eugeneware/ffmpeg-static

## Microsoft Edge WebView2 (Windows only)

The Windows build bundles the Microsoft Edge WebView2 Evergreen Bootstrapper so
that a machine without the WebView2 Runtime can install it. The bootstrapper is
signed by Microsoft Corporation.

WebView2 is subject to Microsoft's terms and privacy statements:
https://developer.microsoft.com/microsoft-edge/webview2/

## Python

The desktop executable is built with PyInstaller and bundles the CPython
runtime and standard library under the Python Software Foundation License.
