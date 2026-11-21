(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const PKEY = "cine:progress:";
  const LANG_KEY = "cine:lang";

  const S = {
    q: "", kind: "", collection: "", sort: "recent", dups: false,
    items: [], total: 0, loading: false, done: false,
    status: null, fingerprint: "", pendingNew: 0,
    detailItem: null, lastSave: 0, refreshTimer: 0,
    sessionStart: Date.now() / 1000,
  };

  const els = {
    langToggle: $("#langToggle"), langLabel: $("#langLabel"),
    livePill: $("#livePill"), liveText: $("#liveText"),
    phaseTitle: $("#phaseTitle"), currentFile: $("#currentFile"),
    bar: $("#bar"), barFill: $("#barFill"),
    barCount: $("#barCount"), barHint: $("#barHint"),
    statTotal: $("#statTotal"), statDuration: $("#statDuration"),
    statSize: $("#statSize"), statDup: $("#statDup"),
    btnPause: $("#btnPause"), btnRescan: $("#btnRescan"),
    btnDelete: $("#btnDelete"),
    confirmDelete: $("#confirmDelete"), confirmName: $("#confirmName"),
    confirmPath: $("#confirmPath"), confirmError: $("#confirmError"),
    confirmDeleteBtn: $("#confirmDeleteBtn"), cancelDelete: $("#cancelDelete"),
    search: $("#search"), kindSeg: $("#kindSeg"),
    collectionFilter: $("#collectionFilter"), sort: $("#sort"),
    showDups: $("#showDups"),
    continueSection: $("#continueSection"), continueRow: $("#continueRow"),
    shelf: $("#shelf"), grid: $("#grid"), empty: $("#empty"),
    resultLine: $("#resultLine"), loadMoreWrap: $("#loadMoreWrap"),
    loadMore: $("#loadMore"),
    detail: $("#detail"), stage: $("#stage"), closeDetail: $("#closeDetail"),
    detailKicker: $("#detailKicker"), detailTitle: $("#detailTitle"),
    detailSub: $("#detailSub"), detailDesc: $("#detailDesc"),
    detailStrip: $("#detailStrip"), detailSpecs: $("#detailSpecs"),
    btnPlayLocal: $("#btnPlayLocal"), btnFolder: $("#btnFolder"),
    btnCopy: $("#btnCopy"),
    toast: $("#toast"), newPill: $("#newPill"),
  };

  const MESSAGES = {
    en: {
      "doc.title": "片匣 · Local Media Library",
      "brand.tagline": "PRIVATE SCREENING ARCHIVE · LOCAL CINEMA",
      "mast.issue": "VOL. 001 / LOCAL COLLECTION",
      "live.connecting": "Connecting…",
      "ledger.kicker": "INDEXING / ARCHIVE",
      "ledger.connecting": "Connecting to indexer…",
      "stat.titles": "Titles",
      "stat.runtime": "Runtime",
      "stat.size": "Size",
      "stat.duplicates": "Duplicates",
      "btn.pause": "Pause",
      "btn.resume": "Resume",
      "btn.scan": "Scan now",
      "btn.scanBusy": "Scanning…",
      "btn.scanTitle": "Rescan the configured folders. It never runs automatically.",
      "toolbar.search": "Search titles, filenames, or descriptions…",
      "filter.all": "All",
      "filter.video": "Video",
      "filter.audio": "Audio",
      "filter.collections": "All collections",
      "sort.recent": "Recently added",
      "sort.name": "Name",
      "sort.duration": "Duration",
      "sort.size": "Size",
      "toolbar.dups": "Show duplicates",
      "aria.kind": "Media type",
      "aria.collections": "Collection filter",
      "aria.sort": "Sort",
      "continue.title": "Continue watching",
      "continue.note": "Pick up where you left off",
      "shelf.title": "Library",
      "empty.title": "Nothing here yet",
      "empty.hint": "Try another search, or run a scan to bring films in.",
      "loadMore": "Load more",
      "footer.note": "片匣 · Indexing is read-only; deletion only after confirmation",
      "detail.close": "Close",
      "btn.openLocal": "Open in local player",
      "btn.folder": "Show folder",
      "btn.copy": "Copy path",
      "btn.delete": "Delete file",
      "desc.label": "SYNOPSIS",
      "strip.label": "CONTACT SHEET",
      "confirm.kicker": "DELETE",
      "confirm.title": "Delete this file?",
      "confirm.warning": "The file will be permanently deleted from disk. This cannot be undone; its cover and contact sheet will also be removed.",
      "confirm.cancel": "Cancel",
      "confirm.delete": "Delete permanently",
      "confirm.deleting": "Deleting…",
      "lang.toZh": "Switch to Chinese",
      "lang.toEn": "Switch to English",
      "status.offline": "Indexer offline",
      "status.offlineHint": "Run start.ps1 to start the indexer",
      "status.paused": "Paused",
      "status.error": "Indexer error",
      "status.working": "Working",
      "status.standby": "Standby",
      "status.shortWorking": "{short}…",
      "phase.scan.short": "Scanning",
      "phase.dedupe.short": "Comparing",
      "phase.probe.short": "Probing",
      "phase.thumb.short": "Covers",
      "phase.strip.short": "Sheets",
      "phase.scan.title": "Counting every frame",
      "phase.dedupe.title": "Comparing duplicates",
      "phase.probe.title": "Reading duration, size, and sound",
      "phase.thumb.title": "Printing covers",
      "phase.strip.title": "Printing contact sheets",
      "phase.paused.title": "Indexing paused",
      "phase.idle.title": "Library ready",
      "phase.error.title": "Indexer needs attention",
      "phase.working.title": "Working",
      "ledger.idleHint": "Press “Scan now” to rescan the folders",
      "ledger.filesSeen": "{n} files checked",
      "ledger.lastScan": "Last scan {time}",
      "ledger.noScan": "No scan yet",
      "ledger.manualMode": "Manual mode",
      "ledger.indexed": "{done} / {total} indexed",
      "ledger.pendingCount": "{n} pending",
      "ledger.fileCount": "{n} files",
      "result.loading": "Loading…",
      "result.noResults": "No results",
      "result.count": "{n} titles · {m} shown",
      "duration.hours": "{h} h {m} min",
      "duration.minutes": "{m} min {s} sec",
      "duration.seconds": "{s} sec",
      "toast.loadFail": "Couldn't load the list. The indexer may not be ready.",
      "toast.itemFail": "Couldn't load this item.",
      "toast.playerOpened": "Opened in the default player.",
      "toast.openFail": "Couldn't open: {err}",
      "toast.folderOpened": "Opened containing folder.",
      "toast.pathCopied": "Path copied.",
      "toast.copyFail": "Couldn't copy the path.",
      "toast.deleted": "Permanently deleted from disk.",
      "toast.deleteFail": "Delete failed: {err}",
      "toast.paused": "Indexing paused.",
      "toast.resumed": "Indexing resumed.",
      "toast.scanQueued": "Scan queued.",
      "toast.actionFail": "Action failed: {err}",
      "card.processing": "Processing",
      "card.kindVideo": "V",
      "card.kindAudio": "A",
      "card.new": "NEW",
      "card.dupMore": "{n} more copies",
      "card.dupMoreOne": "1 more copy",
      "kind.video": "video",
      "kind.audio": "audio",
      "card.aria": "{title}, {kind}, {duration}",
      "detail.kickerVideo": "FILM / VIDEO",
      "detail.kickerAudio": "AUDIO",
      "detail.added": "Added {date}",
      "detail.duration": "Duration",
      "detail.resolution": "Resolution",
      "detail.fps": "Frame rate",
      "detail.vcodec": "Video",
      "detail.acodec": "Audio",
      "detail.bitrate": "Bitrate",
      "detail.size": "Size",
      "detail.collection": "Collection",
      "detail.source": "Source",
      "detail.addedSpec": "Added",
      "detail.duplicate": "Duplicate",
      "detail.duplicateOf": "Same content as #{id}",
      "detail.path": "Path",
      "detail.bvid": "BVID",
      "detail.unsupportedVideo": "This container or codec can't play in the browser",
      "detail.unsupportedAudio": "This audio format can't play in the browser",
      "detail.unsupportedHint": "Hand it to the local player; picture and sound are unaffected.",
      "detail.unsupportedButton": "Open in local player",
      "confirm.errorInUse": "File is in use. Close the player and try again.",
      "confirm.errorGeneric": "Delete failed: {err}",
      "error.notFound": "Item not found.",
      "newPill": "New titles added — back to top",
      "newPillCount": "{n} new titles — back to top",
      "untitled": "(untitled)",
      "unknownCollection": "Uncategorised",
    },
    zh: {
      "doc.title": "片匣 · 本地媒体库",
      "brand.tagline": "私人放映档案 · LOCAL CINEMA ARCHIVE",
      "mast.issue": "VOL. 001 / 本机馆藏",
      "live.connecting": "连接中",
      "ledger.kicker": "INDEXING / 入档",
      "ledger.connecting": "正在连接索引器…",
      "stat.titles": "片目",
      "stat.runtime": "总时长",
      "stat.size": "容量",
      "stat.duplicates": "重复",
      "btn.pause": "暂停",
      "btn.resume": "继续",
      "btn.scan": "手动巡检",
      "btn.scanBusy": "巡检中…",
      "btn.scanTitle": "重新扫描配置目录；不会自动运行",
      "toolbar.search": "搜索标题、文件名或简介…",
      "filter.all": "全部",
      "filter.video": "影像",
      "filter.audio": "声音",
      "filter.collections": "全部系列",
      "sort.recent": "最近入档",
      "sort.name": "名称顺序",
      "sort.duration": "按片长",
      "sort.size": "按体积",
      "toolbar.dups": "含重复项",
      "aria.kind": "媒体类型",
      "aria.collections": "系列筛选",
      "aria.sort": "排序",
      "continue.title": "继续观看",
      "continue.note": "接着上次看到的位置",
      "shelf.title": "馆藏",
      "empty.title": "还没有找到媒体",
      "empty.hint": "换个关键词，或点一次手动巡检让索引器把片子送进来。",
      "loadMore": "加载更多",
      "footer.note": "片匣 · 只读索引；删除需二次确认",
      "detail.close": "关闭",
      "btn.openLocal": "用本地播放器打开",
      "btn.folder": "所在文件夹",
      "btn.copy": "复制路径",
      "btn.delete": "删除文件",
      "desc.label": "简介 / SYNOPSIS",
      "strip.label": "接触印样 / CONTACT SHEET",
      "confirm.kicker": "DELETE / 删除",
      "confirm.title": "确认删除这个文件？",
      "confirm.warning": "文件会从磁盘永久删除，无法恢复；封面和接触印样也会一起清除。",
      "confirm.cancel": "取消",
      "confirm.delete": "永久删除",
      "confirm.deleting": "删除中…",
      "lang.toZh": "切换到中文",
      "lang.toEn": "切换到英语",
      "status.offline": "索引器未运行",
      "status.offlineHint": "运行 start.ps1 启动后台索引",
      "status.paused": "已暂停",
      "status.error": "索引器出错",
      "status.working": "整理中",
      "status.standby": "待命",
      "status.shortWorking": "{short}中",
      "phase.scan.short": "清点",
      "phase.dedupe.short": "比对",
      "phase.probe.short": "识别",
      "phase.thumb.short": "冲印",
      "phase.strip.short": "印样",
      "phase.scan.title": "清点每一格胶片",
      "phase.dedupe.title": "校对人眼难辨的重复",
      "phase.probe.title": "读取片长、画幅与声音",
      "phase.thumb.title": "冲印封面",
      "phase.strip.title": "冲印接触印样",
      "phase.paused.title": "入档已暂停",
      "phase.idle.title": "馆藏已就绪",
      "phase.error.title": "索引器遇到问题",
      "phase.working.title": "正在整理",
      "ledger.idleHint": "点击「手动巡检」重新清点目录",
      "ledger.filesSeen": "已清点 {n} 个文件",
      "ledger.lastScan": "上次巡检 {time}",
      "ledger.noScan": "尚未手动巡检",
      "ledger.manualMode": "手动模式",
      "ledger.indexed": "{done} / {total} 已入档",
      "ledger.pendingCount": "{n} 个待处理",
      "ledger.fileCount": "{n} 个文件",
      "result.loading": "清点中…",
      "result.noResults": "暂无结果",
      "result.count": "共 {n} 部 · 已陈列 {m}",
      "duration.hours": "{h} 小时 {m} 分",
      "duration.minutes": "{m} 分 {s} 秒",
      "duration.seconds": "{s} 秒",
      "toast.loadFail": "列表加载失败，索引器可能尚未就绪",
      "toast.itemFail": "无法读取这一条目",
      "toast.playerOpened": "已交给系统默认播放器",
      "toast.openFail": "打开失败：{err}",
      "toast.folderOpened": "已打开所在文件夹",
      "toast.pathCopied": "路径已复制",
      "toast.copyFail": "复制失败",
      "toast.deleted": "已从磁盘永久删除",
      "toast.deleteFail": "删除失败：{err}",
      "toast.paused": "已暂停入档",
      "toast.resumed": "已继续入档",
      "toast.scanQueued": "已排入新一轮巡检",
      "toast.actionFail": "操作失败：{err}",
      "card.processing": "待冲印",
      "card.kindVideo": "影",
      "card.kindAudio": "声",
      "card.new": "新入档",
      "card.dupMore": "另有 {n} 份",
      "card.dupMoreOne": "另有 1 份",
      "kind.video": "影像",
      "kind.audio": "声音",
      "card.aria": "{title}，{kind}，{duration}",
      "detail.kickerVideo": "影像 / FILM",
      "detail.kickerAudio": "声音 / AUDIO",
      "detail.added": "收录 {date}",
      "detail.duration": "片长",
      "detail.resolution": "画幅",
      "detail.fps": "帧率",
      "detail.vcodec": "视频",
      "detail.acodec": "音频",
      "detail.bitrate": "码率",
      "detail.size": "体积",
      "detail.collection": "系列",
      "detail.source": "来源",
      "detail.addedSpec": "收录",
      "detail.duplicate": "重复",
      "detail.duplicateOf": "与馆藏 #{id} 内容相同",
      "detail.path": "路径",
      "detail.bvid": "BVID",
      "detail.unsupportedVideo": "这个封装或编码浏览器播不了",
      "detail.unsupportedAudio": "这个音频格式浏览器解不开",
      "detail.unsupportedHint": "可以把它交给本机播放器，画面和声音都不受影响。",
      "detail.unsupportedButton": "用本地播放器打开",
      "confirm.errorInUse": "文件正被占用，请先关闭播放器再删除",
      "confirm.errorGeneric": "删除失败：{err}",
      "error.notFound": "条目不存在",
      "newPill": "有新片入档，回顶部看看",
      "newPillCount": "有新片入档 ({n})，回顶部看看",
      "untitled": "(未命名)",
      "unknownCollection": "未分类",
    },
  };

  let LANG = "en";
  try {
    if (localStorage.getItem(LANG_KEY) === "zh") LANG = "zh";
  } catch (err) { /* ignore */ }

  let NUM = new Intl.NumberFormat(LANG === "zh" ? "zh-CN" : "en-US");
  const PHASE_KEYS = ["scan", "dedupe", "probe", "thumb", "strip"];

  function t(key, vars) {
    const table = MESSAGES[LANG] || MESSAGES.en;
    let text = table[key] != null ? table[key] : (MESSAGES.en[key] != null ? MESSAGES.en[key] : key);
    if (vars) {
      for (const [name, value] of Object.entries(vars)) {
        text = text.split(`{${name}}`).join(String(value));
      }
    }
    return text;
  }

  function phaseShortFor(phase) {
    return PHASE_KEYS.includes(phase) ? t(`phase.${phase}.short`) : t("status.working");
  }

  function phaseTitleFor(phase) {
    if (phase === "paused") return t("phase.paused.title");
    if (phase === "idle" || phase === "watch") return t("phase.idle.title");
    if (phase === "error") return t("phase.error.title");
    return PHASE_KEYS.includes(phase) ? t(`phase.${phase}.title`) : t("phase.working.title");
  }

  const pad = (n) => String(n).padStart(2, "0");

  function basename(p) {
    if (!p) return "";
    return p.split(/[\\/]/).pop() || p;
  }

  function fmtDuration(sec) {
    if (!sec || !isFinite(sec)) return "—";
    const s = Math.round(sec);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const ss = s % 60;
    return h > 0 ? `${h}:${pad(m)}:${pad(ss)}` : `${m}:${pad(ss)}`;
  }

  function fmtTotalDuration(sec) {
    if (!sec) return "—";
    const s = Math.round(sec);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return t("duration.hours", { h: NUM.format(h), m });
    if (m > 0) return t("duration.minutes", { m, s: s % 60 });
    return t("duration.seconds", { s });
  }

  function fmtSize(bytes) {
    if (!bytes) return "—";
    if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
    if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(bytes >= 10 * 1024 ** 2 ? 0 : 1)} MB`;
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }

  function fmtDate(ts) {
    if (!ts) return "—";
    const d = new Date(ts * 1000);
    return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`;
  }

  function toast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => els.toast.classList.remove("show"), 2600);
  }

  async function getJSON(url) {
    const r = await fetch(url, { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  async function postJSON(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Cine": "1" },
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
    return data;
  }

  /* ---------------- 状态台账 ---------------- */

  async function loadStatus() {
    try {
      const s = await getJSON("/api/status");
      S.status = s;
      renderStatus(s);
      maybeAutoRefresh(s);
    } catch (err) {
      renderOffline();
    }
  }

  function renderOffline() {
    els.livePill.className = "live-pill is-offline";
    els.liveText.textContent = t("status.offline");
    els.phaseTitle.textContent = t("status.offline");
    els.currentFile.textContent = t("status.offlineHint");
    els.bar.className = "bar";
    els.barFill.style.width = "0%";
    els.barCount.textContent = "—";
    els.barHint.textContent = "";
    els.btnPause.disabled = true;
    els.btnRescan.disabled = true;
    const rescanSpan = els.btnRescan.querySelector("span");
    if (rescanSpan) rescanSpan.textContent = t("btn.scan");
  }

  function renderStatus(s) {
    const stats = s.stats || {};
    const running = !!s.running;
    const paused = !!s.paused;
    const phase = s.phase || "";
    const indexing = PHASE_KEYS.includes(phase);
    const idle = phase === "idle" || phase === "watch";

    let cls = "is-offline";
    let label = t("status.offline");
    if (running) {
      if (paused) {
        cls = "is-paused";
        label = t("status.paused");
      } else if (indexing) {
        cls = "is-live";
        const short = phaseShortFor(phase);
        label = (s.phase_total > 0)
          ? `${short} ${s.phase_done || 0}/${s.phase_total}`
          : t("status.shortWorking", { short });
      } else if (idle) {
        cls = "is-watch";
        label = t("status.standby");
      } else if (phase === "error") {
        cls = "is-paused";
        label = t("status.error");
      } else {
        cls = "is-live";
        label = t("status.working");
      }
    }
    els.livePill.className = `live-pill ${cls}`;
    els.liveText.textContent = label;

    els.phaseTitle.textContent = running
      ? phaseTitleFor(phase)
      : t("status.offline");
    els.currentFile.textContent = s.current
      ? basename(s.current)
      : (running && idle ? t("ledger.idleHint") : "—");

    if (running && !paused && indexing && s.progress == null) {
      els.bar.className = "bar is-indeterminate";
      els.barFill.style.width = "";
    } else {
      const pct = s.progress != null
        ? Math.max(0, Math.min(1, s.progress)) * 100
        : (idle ? 100 : 0);
      els.bar.className = "bar" + (idle ? " is-done" : "");
      els.barFill.style.width = `${pct}%`;
    }

    if (running && indexing) {
      els.barCount.textContent = s.phase_total > 0
        ? `${NUM.format(s.phase_done || 0)} / ${NUM.format(s.phase_total)}`
        : t("ledger.fileCount", { n: NUM.format(s.files_seen || 0) });
    } else if (running && idle) {
      els.barCount.textContent = t("ledger.indexed", {
        done: NUM.format(stats.ready || 0),
        total: NUM.format(stats.total || 0),
      });
    } else {
      els.barCount.textContent = "—";
    }

    const bits = [];
    if (running && idle) {
      bits.push(s.last_scan_at_text
        ? t("ledger.lastScan", { time: s.last_scan_at_text.slice(5, 16) })
        : t("ledger.noScan"));
      bits.push(t("ledger.manualMode"));
    }
    if (running && indexing && s.files_seen) {
      bits.push(t("ledger.filesSeen", { n: NUM.format(s.files_seen) }));
    }
    if (running && s.errors && s.errors.length) {
      bits.push(t("ledger.pendingCount", { n: s.errors.length }));
    }
    els.barHint.textContent = bits.join(" · ");

    const uniq = Math.max(0, (stats.total || 0) - (stats.duplicates || 0));
    els.statTotal.textContent = NUM.format(uniq);
    els.statDuration.textContent = fmtTotalDuration(stats.total_duration || 0);
    els.statSize.textContent = fmtSize(stats.total_size || 0);
    els.statDup.textContent = NUM.format(stats.duplicates || 0);

    const busy = running && indexing;
    els.btnPause.disabled = !running;
    els.btnRescan.disabled = !running || busy;
    const rescanSpan = els.btnRescan.querySelector("span");
    if (rescanSpan) rescanSpan.textContent = busy ? t("btn.scanBusy") : t("btn.scan");
    const pauseSpan = els.btnPause.querySelector("span");
    if (pauseSpan) pauseSpan.textContent = paused ? t("btn.resume") : t("btn.pause");
    const use = els.btnPause.querySelector("use");
    if (use) use.setAttribute("href", paused ? "#i-play" : "#i-pause");
  }

  function maybeAutoRefresh(s) {
    if (!s || !s.running || s.paused) return;
    if (!PHASE_KEYS.includes(s.phase)) return;
    if (S.q || S.kind || S.collection || S.dups) return;
    const st = s.stats || {};
    const fp = `${st.ready || 0}|${st.total || 0}|${st.duplicates || 0}|${st.errored || 0}`;
    if (!S.fingerprint) {
      S.fingerprint = fp;
      return;
    }
    if (fp !== S.fingerprint) {
      S.fingerprint = fp;
      if (window.scrollY < 260) {
        clearTimeout(S.refreshTimer);
        S.refreshTimer = setTimeout(() => {
          loadItems(true, { soft: true });
          loadFacets();
        }, 1400);
      } else {
        S.pendingNew += 1;
        els.newPill.hidden = false;
        els.newPill.textContent = t("newPillCount", { n: S.pendingNew });
      }
    }
  }

  /* ---------------- 系列与列表 ---------------- */

  async function loadFacets() {
    try {
      const data = await getJSON("/api/facets");
      const current = S.collection;
      const collections = data.collections || [];
      const header = document.createElement("option");
      header.value = "";
      header.textContent = t("filter.collections");
      const frag = document.createDocumentFragment();
      frag.append(header);
      let found = false;
      for (const c of collections) {
        const opt = document.createElement("option");
        opt.value = c.name || "";
        opt.textContent = `${c.name || t("unknownCollection")} · ${c.count}`;
        if (opt.value === current) found = true;
        frag.append(opt);
      }
      els.collectionFilter.replaceChildren(frag);
      if (current && !found) {
        S.collection = "";
        els.collectionFilter.value = "";
        loadItems(true);
      } else {
        els.collectionFilter.value = S.collection;
      }
    } catch (err) {
      /* 索引尚未就绪时忽略 */
    }
  }

  function queryParams() {
    const p = new URLSearchParams();
    if (S.q) p.set("q", S.q);
    if (S.kind) p.set("kind", S.kind);
    if (S.collection) p.set("collection", S.collection);
    p.set("sort", S.sort);
    p.set("limit", "48");
    p.set("offset", "0");
    if (S.dups) p.set("dup", "1");
    return p;
  }

  let reqSeq = 0;

  async function loadItems(reset, opts = {}) {
    if (!reset && (S.loading || S.done)) return;
    const seq = ++reqSeq;
    if (reset) S.items = [];
    S.loading = true;
    if (reset && !opts.soft && S.items.length === 0) showSkeletons();

    const params = queryParams();
    params.set("offset", reset ? "0" : String(S.items.length));
    try {
      const data = await getJSON(`/api/items?${params.toString()}`);
      if (seq !== reqSeq) return;
      if (reset) S.items = data.items || [];
      else S.items = S.items.concat(data.items || []);
      S.total = data.total || 0;
      S.done = S.items.length >= S.total;
      renderGrid();
      updateResultLine();
    } catch (err) {
      if (seq !== reqSeq) return;
      if (!opts.soft) toast(t("toast.loadFail"));
      updateResultLine();
    } finally {
      if (seq === reqSeq) {
        S.loading = false;
        updateResultLine();
      }
      els.loadMore.disabled = false;
    }
  }

  function updateResultLine() {
    if (!S.total) {
      els.resultLine.textContent = S.loading ? t("result.loading") : t("result.noResults");
    } else {
      els.resultLine.textContent = t("result.count", {
        n: NUM.format(S.total),
        m: NUM.format(S.items.length),
      });
    }
    els.loadMoreWrap.hidden = S.done || S.items.length === 0;
    els.empty.hidden = !(S.items.length === 0 && !S.loading);
  }

  function showSkeletons() {
    const frag = document.createDocumentFragment();
    for (let i = 0; i < 10; i++) {
      const d = document.createElement("div");
      d.className = "skel";
      d.innerHTML = '<div class="frame"></div><div class="line"></div><div class="line short"></div>';
      frag.append(d);
    }
    els.grid.replaceChildren(frag);
  }

  const cardRefs = new WeakMap();

  function makeCard(item, index) {
    const card = document.createElement("article");
    card.className = "card";
    card.dataset.id = String(item.id);
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.style.setProperty("--i", String(index % 22));
    card.innerHTML = `
      <div class="frame">
        <div class="ph"><svg><use href="#i-film"/></svg><span>${t("card.processing")}</span></div>
        <img alt="" loading="lazy" decoding="async">
        <span class="index-no"></span>
        <span class="kind-mark"></span>
        <span class="duration"></span>
        <span class="new-flag" hidden>${t("card.new")}</span>
        <div class="play"><i><svg><use href="#i-play"/></svg></i></div>
        <div class="card-progress" hidden><i></i></div>
      </div>
      <div class="card-body">
        <div class="card-title"></div>
        <div class="card-sub"></div>
      </div>`;
    const refs = {
      frame: card.querySelector(".frame"),
      img: card.querySelector("img"),
      index: card.querySelector(".index-no"),
      kind: card.querySelector(".kind-mark"),
      duration: card.querySelector(".duration"),
      newFlag: card.querySelector(".new-flag"),
      phLabel: card.querySelector(".ph span"),
      progress: card.querySelector(".card-progress"),
      progressFill: card.querySelector(".card-progress i"),
      title: card.querySelector(".card-title"),
      sub: card.querySelector(".card-sub"),
    };
    cardRefs.set(card, refs);
    refs.img.addEventListener("load", () => refs.frame.classList.remove("noimg"));
    refs.img.addEventListener("error", () => {
      refs.img.removeAttribute("src");
      refs.frame.classList.add("noimg");
    });
    card.addEventListener("click", () => openDetail(item.id));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openDetail(item.id);
      }
    });
    updateCard(card, item);
    return card;
  }

  function updateCard(card, item) {
    const r = cardRefs.get(card);
    if (!r) return;
    const title = item.title || item.name || t("untitled");
    r.title.textContent = title;
    r.index.textContent = `NO. ${String(item.id).padStart(4, "0")}`;
    r.kind.textContent = item.kind === "audio" ? t("card.kindAudio") : t("card.kindVideo");
    r.kind.classList.toggle("audio", item.kind === "audio");
    r.duration.textContent = fmtDuration(item.duration);
    r.newFlag.textContent = t("card.new");
    if (r.phLabel) r.phLabel.textContent = t("card.processing");
    card.classList.toggle("is-dup", !!item.dup_of);
    card.setAttribute(
      "aria-label",
      t("card.aria", {
        title,
        kind: t(item.kind === "audio" ? "kind.audio" : "kind.video"),
        duration: fmtDuration(item.duration),
      })
    );

    if (item.thumb) {
      const src = `/api/thumb/${item.id}?v=${encodeURIComponent(item.thumb)}`;
      if (r.img.getAttribute("src") !== src) r.img.src = src;
    } else {
      r.frame.classList.add("noimg");
    }

    const subs = [];
    if (item.collection) subs.push(item.collection);
    if (item.width && item.height) subs.push(`${item.width}×${item.height}`);
    subs.push(fmtSize(item.size));
    r.sub.textContent = subs.join(" · ");
    if (item.dup_count > 0) {
      const flag = document.createElement("span");
      flag.className = "dup-flag";
      flag.textContent = item.dup_count === 1
        ? t("card.dupMoreOne", { n: 1 })
        : t("card.dupMore", { n: item.dup_count });
      r.sub.append(" ", flag);
    }

    const isNew = item.added_at && item.added_at > S.sessionStart;
    r.newFlag.hidden = !isNew;

    const prog = readProgress(item.id);
    if (prog && prog.t > 4 && prog.d > 0 && prog.t / prog.d < 0.95) {
      r.progress.hidden = false;
      r.progressFill.style.width = `${Math.min(100, (prog.t / prog.d) * 100)}%`;
    } else {
      r.progress.hidden = true;
    }
  }

  function renderGrid() {
    const existing = new Map();
    for (const child of Array.from(els.grid.children)) {
      if (child.dataset && child.dataset.id) existing.set(child.dataset.id, child);
    }
    const frag = document.createDocumentFragment();
    S.items.forEach((item, i) => {
      let card = existing.get(String(item.id));
      if (card) {
        existing.delete(String(item.id));
        updateCard(card, item);
      } else {
        card = makeCard(item, i);
      }
      frag.append(card);
    });
    els.grid.replaceChildren(frag);
    updateResultLine();
  }

  /* ---------------- 详情与播放 ---------------- */

  function readProgress(id) {
    try {
      const raw = localStorage.getItem(PKEY + id);
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      return null;
    }
  }

  function saveProgress(item, t, d) {
    if (!item || !isFinite(t) || !isFinite(d) || d <= 0) return;
    try {
      localStorage.setItem(
        PKEY + item.id,
        JSON.stringify({
          id: item.id, title: item.title, thumb: item.thumb,
          kind: item.kind, collection: item.collection,
          t, d, at: Date.now(),
        })
      );
    } catch (err) {
      /* 隐私模式或配额满时忽略 */
    }
  }

  function renderContinue() {
    const entries = [];
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!key || !key.startsWith(PKEY)) continue;
        try {
          const e = JSON.parse(localStorage.getItem(key));
          if (e && e.t > 4 && e.d > 0 && e.t / e.d < 0.95) entries.push(e);
        } catch (err) {
          /* ignore */
        }
      }
    } catch (err) {
      return;
    }
    entries.sort((a, b) => (b.at || 0) - (a.at || 0));
    els.continueSection.hidden = entries.length === 0;
    if (!entries.length) return;
    const frag = document.createDocumentFragment();
    for (const e of entries.slice(0, 8)) {
      const card = document.createElement("div");
      card.className = "mini";
      card.innerHTML = `
        <div class="mini-thumb"><img alt="" loading="lazy"></div>
        <div class="mini-body">
          <div class="mini-title"></div>
          <div class="mini-meta"></div>
          <div class="mini-bar"><i></i></div>
        </div>`;
      const img = card.querySelector("img");
      if (e.thumb) img.src = `/api/thumb/${e.id}?v=${encodeURIComponent(e.thumb)}`;
      card.querySelector(".mini-title").textContent = e.title || t("untitled");
      card.querySelector(".mini-meta").textContent =
        `${fmtDuration(e.t)} / ${fmtDuration(e.d)}`;
      card.querySelector(".mini-bar i").style.width =
        `${Math.min(100, (e.t / e.d) * 100)}%`;
      card.addEventListener("click", () => openDetail(e.id));
      frag.append(card);
    }
    els.continueRow.replaceChildren(frag);
  }

  function specRow(dl, label, value, wide = false) {
    if (value == null || value === "" || value === "—") return;
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    if (wide) dd.className = "wide";
    dl.append(dt, dd);
  }

  function specWide(dl, label, value) {
    if (!value) return;
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.className = "wide";
    dd.textContent = value;
    dl.append(dt, dd);
  }

  function buildStage(item) {
    els.stage.replaceChildren();
    els.stage.className = "stage";
    const id = item.id;
    const progress = readProgress(id);
    const mediaBox = els.stage.parentElement;
    if (mediaBox) {
      if (item.thumb) {
        mediaBox.style.setProperty("--poster", `url("/api/thumb/${id}?v=${encodeURIComponent(item.thumb)}")`);
      } else {
        mediaBox.style.removeProperty("--poster");
      }
    }

    if (item.kind === "audio") {
      els.stage.classList.add("audio");
      if (item.thumb) {
        const img = document.createElement("img");
        img.alt = "";
        img.src = `/api/thumb/${id}?v=${encodeURIComponent(item.thumb)}`;
        els.stage.append(img);
      } else {
        const ph = document.createElement("div");
        ph.className = "ph";
        ph.style.cssText = "position:absolute;inset:0;display:grid;place-items:center;color:rgba(239,229,209,.2)";
        ph.innerHTML = '<svg style="width:54px;height:54px"><use href="#i-wave"/></svg>';
        els.stage.append(ph);
      }
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.autoplay = true;
      audio.preload = "metadata";
      audio.src = `/api/stream/${id}`;
      els.stage.append(audio);
      attachProgress(audio, item, progress);
      audio.addEventListener("error", () => showUnsupported(item, t("detail.unsupportedAudio")));
      return audio;
    }

    const video = document.createElement("video");
    video.controls = true;
    video.autoplay = true;
    video.playsInline = true;
    video.preload = "metadata";
    if (item.thumb) {
      video.poster = `/api/thumb/${id}?v=${encodeURIComponent(item.thumb)}`;
    }
    video.src = `/api/stream/${id}`;
    els.stage.append(video);
    attachProgress(video, item, progress);
    let failed = false;
    video.addEventListener("error", () => {
      if (failed) return;
      failed = true;
      showUnsupported(item, t("detail.unsupportedVideo"));
    });
    return video;
  }

  function attachProgress(media, item, progress) {
    media.addEventListener("loadedmetadata", () => {
      const d = media.duration;
      if (progress && progress.t > 5 && isFinite(d) && progress.t < d - 4) {
        media.currentTime = progress.t;
      }
    });
    media.addEventListener("timeupdate", () => {
      const t = Date.now();
      if (t - S.lastSave < 2000) return;
      S.lastSave = t;
      if (media.duration && isFinite(media.duration)) {
        saveProgress(item, media.currentTime, media.duration);
      }
    });
  }

  function showUnsupported(item, message) {
    if (els.stage.querySelector(".unsupported")) return;
    const box = document.createElement("div");
    box.className = "unsupported";
    const strong = document.createElement("strong");
    strong.textContent = message;
    const p = document.createElement("p");
    p.textContent = t("detail.unsupportedHint");
    p.style.margin = "0";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-primary";
    btn.textContent = t("detail.unsupportedButton");
    btn.addEventListener("click", () => playLocal(item));
    box.append(strong, p, btn);
    els.stage.append(box);
  }

  async function playLocal(item) {
    try {
      await postJSON("/api/open", { id: item.id, action: "play" });
      toast(t("toast.playerOpened"));
    } catch (err) {
      toast(t("toast.openFail", { err: err.message }));
    }
  }

  function renderDetailMeta(item) {
    const prevDescScroll = els.detailDesc.scrollTop;
    els.detailKicker.textContent =
      `${item.kind === "audio" ? t("detail.kickerAudio") : t("detail.kickerVideo")} · ${item.collection || item.root || ""}`;
    els.detailTitle.textContent = item.title || item.name || t("untitled");
    const subParts = [];
    if (item.root) subParts.push(item.root);
    if (item.rel_dir) subParts.push(item.rel_dir);
    if (item.added_at) {
      subParts.push(t("detail.added", { date: fmtDate(item.added_at) }));
    }
    els.detailSub.textContent = subParts.join("  ·  ");

    if (item.description) {
      els.detailDesc.hidden = false;
      const label = document.createElement("div");
      label.className = "desc-label";
      label.textContent = t("desc.label");
      els.detailDesc.replaceChildren(label, document.createTextNode(item.description));
      els.detailDesc.scrollTop = prevDescScroll;
    } else {
      els.detailDesc.hidden = true;
      els.detailDesc.replaceChildren();
    }

    const dl = els.detailSpecs;
    dl.replaceChildren();
    specRow(dl, t("detail.duration"), fmtDuration(item.duration));
    specRow(dl, t("detail.resolution"), item.width && item.height ? `${item.width} × ${item.height}` : null);
    specRow(dl, t("detail.fps"), item.fps ? `${item.fps} fps` : null);
    specRow(dl, t("detail.vcodec"), item.vcodec);
    specRow(dl, t("detail.acodec"), item.acodec);
    specRow(dl, t("detail.bitrate"), item.bitrate ? `${Math.round(item.bitrate / 1000)} kbps` : null);
    specRow(dl, t("detail.size"), fmtSize(item.size));
    specRow(dl, t("detail.collection"), item.collection);
    specRow(dl, t("detail.source"), item.root);
    specRow(dl, t("detail.addedSpec"), fmtDate(item.added_at));
    if (item.dup_of) {
      specRow(dl, t("detail.duplicate"), t("detail.duplicateOf", { id: item.dup_of }));
    }
    specWide(dl, t("detail.path"), item.path);
    if (item.bvid) specWide(dl, t("detail.bvid"), item.bvid);
  }

  async function openDetail(id) {
    let item;
    try {
      item = await getJSON(`/api/item/${id}`);
    } catch (err) {
      toast(t("toast.itemFail"));
      return;
    }
    S.detailItem = item;
    renderDetailMeta(item);
    els.detailDesc.scrollTop = 0;

    if (item.strip && item.kind !== "audio") {
      const stripUrl = `/api/strip/${item.id}?v=${encodeURIComponent(item.strip)}`;
      els.detailStrip.hidden = false;
      const stripImg = els.detailStrip.querySelector("img");
      stripImg.src = stripUrl;
      stripImg.onclick = () => window.open(stripUrl, "_blank");
    } else {
      els.detailStrip.hidden = true;
      const stripImg = els.detailStrip.querySelector("img");
      stripImg.removeAttribute("src");
      stripImg.onclick = null;
    }

    buildStage(item);
    els.btnPlayLocal.disabled = false;
    els.btnFolder.disabled = false;
    els.btnCopy.disabled = false;
    els.btnDelete.disabled = false;
    if (els.confirmDelete.open) els.confirmDelete.close();
    if (!els.detail.open) {
      els.detail.showModal();
      document.body.style.overflow = "hidden";
    }
    setTimeout(() => els.closeDetail.focus(), 30);
  }

  function cleanupDetail() {
    if (els.confirmDelete.open) els.confirmDelete.close();
    const media = els.stage.querySelector("video, audio");
    if (media) {
      if (media.duration && isFinite(media.duration) && S.detailItem) {
        saveProgress(S.detailItem, media.currentTime, media.duration);
      }
      try { media.pause(); } catch (err) { /* ignore */ }
      media.removeAttribute("src");
      try { media.load(); } catch (err) { /* ignore */ }
    }
    document.body.style.overflow = "";
    S.detailItem = null;
    renderContinue();
    renderGrid();
  }

  function closeDetail() {
    if (els.detail.open) els.detail.close();
  }

  function releaseMedia() {
    const media = els.stage.querySelector("video, audio");
    if (!media) return;
    try { media.pause(); } catch (err) { /* ignore */ }
    media.removeAttribute("src");
    try { media.load(); } catch (err) { /* ignore */ }
  }

  function translateDeleteError(message) {
    const msg = message || "";
    if (msg === "in_use" || msg.includes("文件正被占用")) {
      return t("confirm.errorInUse");
    }
    if (msg === "not_found" || msg === "not found") return t("error.notFound");
    if (msg.startsWith("delete_failed:")) {
      return t("confirm.errorGeneric", { err: msg.slice("delete_failed:".length) });
    }
    if (msg.startsWith("删除失败：")) {
      return t("confirm.errorGeneric", { err: msg.slice("删除失败：".length) });
    }
    return t("confirm.errorGeneric", { err: msg });
  }

  function openDeleteConfirm() {
    const item = S.detailItem;
    if (!item) return;
    els.confirmName.textContent = item.title || item.name || t("untitled");
    els.confirmPath.textContent = item.path || "";
    els.confirmError.hidden = true;
    els.confirmDeleteBtn.disabled = false;
    els.confirmDeleteBtn.textContent = t("confirm.delete");
    if (!els.confirmDelete.open) els.confirmDelete.showModal();
  }

  async function doDelete() {
    const item = S.detailItem;
    if (!item) return;
    els.confirmDeleteBtn.disabled = true;
    els.confirmDeleteBtn.textContent = t("confirm.deleting");
    els.confirmError.hidden = true;
    releaseMedia();
    try {
      await postJSON("/api/delete", { id: item.id });
      try { localStorage.removeItem(PKEY + item.id); } catch (err) { /* ignore */ }
      S.items = S.items.filter((x) => x.id !== item.id);
      S.total = Math.max(0, S.total - 1);
      if (els.confirmDelete.open) els.confirmDelete.close();
      els.detail.close();
      updateResultLine();
      loadFacets();
      setTimeout(loadStatus, 350);
      toast(t("toast.deleted"));
    } catch (err) {
      els.confirmError.textContent = translateDeleteError(err.message);
      els.confirmError.hidden = false;
      els.confirmDeleteBtn.disabled = false;
      els.confirmDeleteBtn.textContent = t("confirm.delete");
    }
  }

  /* ---------------- 事件 ---------------- */

  function bind() {
    els.search.addEventListener("input", () => {
      clearTimeout(S._st);
      S._st = setTimeout(() => {
        S.q = els.search.value.trim();
        loadItems(true);
      }, 260);
    });

    els.kindSeg.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-kind]");
      if (!btn) return;
      S.kind = btn.dataset.kind;
      for (const b of els.kindSeg.querySelectorAll("button")) {
        b.classList.toggle("on", b === btn);
      }
      loadItems(true);
    });

    els.collectionFilter.addEventListener("change", () => {
      S.collection = els.collectionFilter.value;
      loadItems(true);
    });

    els.sort.addEventListener("change", () => {
      S.sort = els.sort.value;
      loadItems(true);
    });

    els.showDups.addEventListener("change", () => {
      S.dups = els.showDups.checked;
      loadItems(true);
    });

    els.loadMore.addEventListener("click", () => {
      els.loadMore.disabled = true;
      loadItems(false);
    });

    els.btnPause.addEventListener("click", async () => {
      const paused = !!S.status?.paused;
      try {
        await postJSON("/api/control", { action: paused ? "resume" : "pause" });
        toast(paused ? t("toast.resumed") : t("toast.paused"));
        setTimeout(loadStatus, 400);
      } catch (err) {
        toast(t("toast.actionFail", { err: err.message }));
      }
    });

    els.btnRescan.addEventListener("click", async () => {
      try {
        await postJSON("/api/control", { action: "rescan" });
        toast(t("toast.scanQueued"));
        S.fingerprint = "";
      } catch (err) {
        toast(t("toast.actionFail", { err: err.message }));
      }
    });

    els.closeDetail.addEventListener("click", closeDetail);
    els.detail.addEventListener("click", (e) => {
      if (e.target === els.detail) closeDetail();
    });
    els.detail.addEventListener("close", cleanupDetail);
    els.detail.addEventListener("cancel", (e) => {
      e.preventDefault();
      closeDetail();
    });

    els.btnPlayLocal.addEventListener("click", () => {
      if (S.detailItem) playLocal(S.detailItem);
    });
    els.btnFolder.addEventListener("click", async () => {
      if (!S.detailItem) return;
      try {
        await postJSON("/api/open", { id: S.detailItem.id, action: "folder" });
        toast(t("toast.folderOpened"));
      } catch (err) {
        toast(t("toast.openFail", { err: err.message }));
      }
    });
    els.btnCopy.addEventListener("click", async () => {
      if (!S.detailItem) return;
      try {
        await navigator.clipboard.writeText(S.detailItem.path);
        toast(t("toast.pathCopied"));
      } catch (err) {
        toast(t("toast.copyFail"));
      }
    });

    els.btnDelete.addEventListener("click", openDeleteConfirm);
    els.cancelDelete.addEventListener("click", () => {
      if (!els.confirmDeleteBtn.disabled) els.confirmDelete.close();
    });
    els.confirmDeleteBtn.addEventListener("click", doDelete);
    els.confirmDelete.addEventListener("click", (e) => {
      if (e.target === els.confirmDelete && !els.confirmDeleteBtn.disabled) {
        els.confirmDelete.close();
      }
    });
    els.confirmDelete.addEventListener("cancel", (e) => {
      if (els.confirmDeleteBtn.disabled) e.preventDefault();
    });

    els.newPill.addEventListener("click", () => {
      S.pendingNew = 0;
      els.newPill.hidden = true;
      window.scrollTo({ top: 0, behavior: "smooth" });
      loadItems(true, { soft: true });
    });

    els.langToggle.addEventListener("click", () => {
      setLanguage(LANG === "zh" ? "en" : "zh");
    });

    document.addEventListener("keydown", (e) => {
      const tag = (e.target.tagName || "").toLowerCase();
      const typing = tag === "input" || tag === "textarea" || tag === "select";
      if (e.key === "/" && !typing && !els.detail.open) {
        e.preventDefault();
        els.search.focus();
      }
      if (e.key === "Escape" && document.activeElement === els.search) {
        els.search.value = "";
        S.q = "";
        loadItems(true);
        els.search.blur();
      }
    });

    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entries) => {
        if (entries.some((en) => en.isIntersecting) && !S.done && !S.loading && S.items.length) {
          loadItems(false);
        }
      }, { rootMargin: "500px" });
      io.observe(els.loadMoreWrap);
    }

    window.addEventListener("storage", (e) => {
      if (e.key && e.key.startsWith(PKEY)) renderContinue();
    });
  }

  function applyStaticI18n() {
    document.documentElement.lang = LANG === "zh" ? "zh-CN" : "en";
    document.title = t("doc.title");
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.placeholder = t(el.dataset.i18nPlaceholder);
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      el.title = t(el.dataset.i18nTitle);
    });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
      el.setAttribute("aria-label", t(el.dataset.i18nAria));
    });
    document.querySelectorAll("[data-i18n-alt]").forEach((el) => {
      el.alt = t(el.dataset.i18nAlt);
    });
  }

  function updateLangButton() {
    if (!els.langToggle || !els.langLabel) return;
    els.langLabel.textContent = LANG === "zh" ? "EN" : "中文";
    const title = LANG === "zh" ? t("lang.toEn") : t("lang.toZh");
    els.langToggle.title = title;
    els.langToggle.setAttribute("aria-label", title);
  }

  function setLanguage(lang, persist = true) {
    LANG = lang === "zh" ? "zh" : "en";
    if (persist) {
      try { localStorage.setItem(LANG_KEY, LANG); } catch (err) { /* ignore */ }
    }
    NUM = new Intl.NumberFormat(LANG === "zh" ? "zh-CN" : "en-US");
    applyStaticI18n();
    updateLangButton();
    if (S.status) renderStatus(S.status);
    else renderOffline();
    renderGrid();
    updateResultLine();
    renderContinue();
    if (S.detailItem) renderDetailMeta(S.detailItem);
    if (!els.newPill.hidden) {
      els.newPill.textContent = t("newPillCount", { n: S.pendingNew });
    }
    loadFacets();
  }

  function init() {
    applyStaticI18n();
    updateLangButton();
    bind();
    renderContinue();
    loadFacets();
    loadStatus();
    loadItems(true);
    setInterval(loadStatus, 1500);
    setInterval(() => {
      if (S.status?.running) loadFacets();
    }, 20000);
    setInterval(renderContinue, 30000);
  }

  init();
})();
