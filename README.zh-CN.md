# 片匣 / CineCase

**一个本地优先、带点胶片档案气质的私人媒体库。**

把它指向你想整理的目录，它就会建立封面、六格接触印样、时长与编码信息、
重复检测、搜索和浏览器内播放。所有数据都在本机，服务只监听 `127.0.0.1`。
**首次部署会自动巡检一次，之后只在点「手动巡检」时扫描。**

[English](README.md) | **中文**

## 功能

- **首次自动、之后手动**：首次部署自动跑一遍；之后只有点「手动巡检」才会扫描，
  没有后台定时巡检。
- **本地网页**：`http://127.0.0.1:8765`。
- **可选桌面窗口**：用 pywebview / WebView2 把同一套界面装进原生窗口，见
  [桌面应用](#桌面应用windows)。
- **中英文界面**：默认英文，右上角一键切换中文；选择会记住。
- **ffprobe 元数据**：时长、分辨率、帧率、视频/音频编码、码率。
- **封面与接触印样**：每个视频生成 640px 封面和 3×2 六格印样；音频生成波形封面。
- **重复检测**：同尺寸文件抽样哈希，重复项默认隐藏，可手动显示。
- **搜索 / 筛选 / 排序**：标题、文件名、B站简介；按类型、系列筛选；按最近入档、
  名称、片长或体积排序。
- **浏览器播放**：支持 Range 拖动进度；浏览器解不开的封装可交给本地播放器。
- **继续观看**：播放进度存在浏览器里。
- **删除需二次确认**：永久删除源文件、数据库记录、封面和接触印样。
- **B站旁车信息**：下载目录里带 `*-元数据.json` 时，自动读取标题和简介。

## 环境要求

- Windows 10/11（附带 `start.ps1` / `stop.ps1`）。
- Python **3.10+**（只用标准库，无需 pip 安装）。
- `ffmpeg` 和 `ffprobe` 在 `PATH` 中，或在 `config.json` 里写绝对路径。
- 现代浏览器。

Python 核心也能在 macOS/Linux 上手动运行；打开文件时会使用 `open` / `xdg-open`。
桌面版仅支持 Windows。网页版本身没有 pip 依赖；桌面构建使用 `pywebview` 和
`pyinstaller`。

## 桌面应用（Windows）

同一套后端和界面可以装进 WebView2 原生窗口：

```powershell
.\build-desktop.ps1
.\dist\CineCase\CineCase.exe
```

构建需要 Python 3.10+ 和 WebView2 Runtime（Windows 11 自带；Windows 10 可能需要
安装 Evergreen WebView2 Runtime）。脚本会创建 `.venv`、安装桌面构建依赖，并在
`dist\CineCase` 生成便携版（约 30 MB）。

便携版默认把 `config.json`、`data/`、`thumbs/`、`strips/` 和 WebView 配置放在
`CineCase.exe` 同目录；如果目录不可写，会退回 `%LOCALAPPDATA%\CineCase`。

想让桌面版和网页版共用同一个库，在 `CineCase.exe` 旁创建 `cinehome.txt`，
里面写库目录的绝对路径即可。同一端口同时只能跑一个服务；如果已有服务在运行，
桌面窗口会直接复用它。

## 快速开始

```powershell
git clone https://github.com/Dabendi/cinecase.git
cd cinecase
.\start.ps1
```

`start.ps1` 会启动服务和索引器，然后打开 `http://127.0.0.1:8765`。
首次部署时索引器会自动巡检一次，之后进入待命。

首次运行会自动从 `config.example.json` 生成 `config.json`，第一次自动巡检
使用的就是示例里的目录。若希望首次巡检就使用自己的目录，可以在启动前先把
`config.example.json` 复制为 `config.json` 并改好 `roots`。之后修改
`config.json`，保存并点页面上的 **手动巡检**。停止：

```powershell
.\stop.ps1
```

macOS / Linux：

```bash
python3 server.py
python3 scan.py --watch
```

然后打开 `http://127.0.0.1:8765`。首次启动自动巡检一次，之后点
**手动巡检** 刷新。

## 配置

`config.json` 已被 gitignore，不会被提交。最小示例：

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

- `roots`：要收录的目录；请保持 `label` 唯一，`path` 支持 `~` 和环境变量。
- `min_size_mb`：每个根目录的最小文件大小，小于阈值的文件会被忽略。
- `exclude_names`：扫描时跳过的目录名（`node_modules`、`.git`、`.venv` 等）。
- `ffmpeg` / `ffprobe`：可执行文件名或绝对路径。
- `port`：本地端口，默认 `8765`。修改端口后需要重启服务（`stop.ps1` /
  `start.ps1`）；其他设置会在下一次手动巡检时重新读取。

首次部署会自动扫描一次。之后增删目录后保存，再点 **手动巡检**；新文件也只会
在下一次手动巡检时入档。没有定时器。

## 工作方式

启动时如果没有“已完成巡检”的记录，索引器会自动跑一遍完整流程；之后的启动
直接待命，直到点 **手动巡检**。

1. **清点**：遍历配置目录，跳过排除项，记录超过大小阈值的媒体。
2. **比对重复**：按大小分组，对候选文件抽样哈希并标记重复。
3. **识别**：用 `ffprobe` 读取时长、画幅、编码、码率、帧率。
4. **封面**：优先使用同名图片 / `poster.jpg`，否则抽帧；音频回退到波形图。
5. **接触印样**：在视频里采 6 帧拼成一张图。
6. **服务**：`server.py` 提供 JSON API 和支持 Range 的媒体流，只绑定
   `127.0.0.1`。

生成文件：

- `data/library.db`：SQLite 索引
- `thumbs/`：封面
- `strips/`：接触印样
- `data/status.json`：首页实时状态
- `data/control.json`：暂停 / 继续 / 手动巡检请求

删除 `data/library.db`、`thumbs/`、`strips/` 即可重置索引；源文件不受影响。

## 删除行为

详情页有 **删除文件** 按钮，二次确认后永久删除源文件，并清除数据库记录、
封面和接触印样。不会进回收站，无法恢复。如果文件正被其他播放器占用，
接口会返回 `in_use`，页面会提示先关闭播放器。

## 隐私

- 应用不发起任何外部网络请求。
- `config.json`、`data/`、`thumbs/`、`strips/`、`screenshots/` 均被 gitignore。
- 服务只绑定 `127.0.0.1`。
- 唯一的破坏性操作是需要确认的删除。

## 限制

- 浏览器能否直接播放取决于编解码器；MKV/FLV/AVI/H.265 可能需要用本地播放器打开。
- 首次部署会自动巡检一次，之后扫描是手动的；没有定时巡检。
- PowerShell 脚本只适用于 Windows；Python 核心可移植。

## 文件结构

```
scan.py                  后台索引器（扫描、ffprobe、封面、印样、重复检测）
server.py                本地 Web 服务（UI、JSON API、Range 播放、删除）
desktop.py               可选桌面启动器（pywebview / WebView2）
web/index.html           页面结构
web/app.js               前端逻辑 + 中英文 i18n
web/style.css            胶片档案风格的样式
assets/cinecase.ico      桌面图标
config.example.json      配置模板
build-desktop.ps1        PyInstaller 桌面构建
requirements-desktop.txt 桌面构建依赖
start.ps1 / stop.ps1     Windows 网页服务启停脚本
```

## License

[MIT](LICENSE)
