from pathlib import Path
import json
from .result import RunRecord


def default_viewer_path(results_path: str | Path) -> Path:
    path = Path(results_path)
    if path.suffix:
        return path.with_name(f"{path.stem}.viewer.html")
    return path.with_name(f"{path.name}.viewer.html")


def write_viewer(
    records: list[RunRecord], out_path: str | Path, title: str | None = None
) -> Path:
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html(records, title=title), encoding="utf-8")
    return target


def render_html(records: list[RunRecord], title: str | None = None) -> str:
    page_title = title or "coderoll Results Viewer"
    records_payload = [record.to_dict() for record in records]
    data_json = json.dumps(records_payload, ensure_ascii=False).replace("</", "<\\/")
    safe_title = _escape_html(page_title)

    template = """<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root,[data-theme="light"]{
      --bg:#f4f5f7;--surface:#ffffff;--surface-2:#f9fafb;--text:#111827;
      --muted:#6b7280;--border:#e5e7eb;--border-2:#d1d5db;
      --ok:#059669;--ok-bg:#ecfdf5;--ok-border:#a7f3d0;
      --bad:#dc2626;--bad-bg:#fef2f2;--bad-border:#fca5a5;
      --warn:#d97706;--warn-bg:#fffbeb;
      --accent:#4f46e5;--accent-bg:#eef2ff;
      --code-bg:#1e1e2e;--code-fg:#cdd6f4;
      --row-hover:#f3f4f6;--row-alt:#fafbfc;
      --shadow:0 1px 3px rgba(0,0,0,.06);
    }
    [data-theme="dark"]{
      --bg:#0f1117;--surface:#1a1b26;--surface-2:#1e1f2e;--text:#e2e8f0;
      --muted:#9ca3af;--border:#2d2f3e;--border-2:#3f4257;
      --ok:#22c55e;--ok-bg:rgba(34,197,94,.1);--ok-border:rgba(34,197,94,.25);
      --bad:#ef4444;--bad-bg:rgba(239,68,68,.1);--bad-border:rgba(239,68,68,.25);
      --warn:#f59e0b;--warn-bg:rgba(245,158,11,.1);
      --accent:#818cf8;--accent-bg:rgba(129,140,248,.1);
      --code-bg:#13141f;--code-fg:#c9d1d9;
      --row-hover:#242538;--row-alt:#161722;
      --shadow:0 1px 3px rgba(0,0,0,.3);
    }
    *{box-sizing:border-box;margin:0}
    body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;color:var(--text);background:var(--bg);-webkit-font-smoothing:antialiased;transition:background .2s,color .2s}
    .wrap{max-width:1440px;margin:0 auto;padding:16px 20px;display:grid;gap:12px;height:100vh;grid-template-rows:auto auto auto 1fr}
    .topbar{display:flex;align-items:center;justify-content:space-between}
    .topbar h1{font-size:18px;font-weight:700;letter-spacing:-.02em}
    .theme-btn{background:var(--surface);border:1px solid var(--border);border-radius:8px;width:36px;height:36px;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:18px;transition:all .15s}
    .theme-btn:hover{border-color:var(--accent);color:var(--accent)}
    .stats{display:flex;gap:8px;flex-wrap:wrap}
    .stat{display:flex;align-items:center;gap:8px;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 14px;font-size:13px;font-weight:500;box-shadow:var(--shadow);transition:all .15s}
    .stat:hover{border-color:var(--border-2)}
    .dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
    .dot-accent{background:var(--accent)}.dot-ok{background:var(--ok)}.dot-bad{background:var(--bad)}.dot-warn{background:var(--warn)}
    .stat .num{font-weight:700;font-family:'JetBrains Mono',monospace}
    .controls{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
    input,select,button{font-family:inherit;font-size:12px;border:1px solid var(--border);border-radius:6px;padding:6px 10px;background:var(--surface);color:var(--text);outline:none;transition:border-color .15s,box-shadow .15s}
    input:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 2px rgba(79,70,229,.12)}
    input[type="search"]{min-width:200px;flex:1}
    select{cursor:pointer}
    .btn{cursor:pointer;background:var(--accent);border-color:transparent;color:#fff;font-weight:600;border-radius:6px;padding:6px 12px;transition:opacity .15s}
    .btn:hover{opacity:.88}
    .btn-ghost{background:transparent;border-color:var(--border);color:var(--muted);font-weight:500;cursor:pointer}
    .btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
    .main{display:grid;grid-template-columns:1fr 380px;gap:12px;min-height:0;overflow:hidden}
    .table-panel{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden;box-shadow:var(--shadow);display:flex;flex-direction:column;min-height:0}
    .table-wrap{overflow:auto;flex:1}
    table{width:100%;border-collapse:collapse;font-size:12px}
    thead th{text-align:left;position:sticky;top:0;z-index:2;background:var(--surface-2);border-bottom:1px solid var(--border);padding:8px 10px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);white-space:nowrap}
    tbody td{border-bottom:1px solid var(--border);padding:7px 10px;vertical-align:middle;white-space:nowrap}
    tbody tr{transition:background .1s;cursor:pointer}
    tbody tr:hover{background:var(--row-hover)}
    tbody tr:nth-child(even){background:var(--row-alt)}
    tbody tr:nth-child(even):hover{background:var(--row-hover)}
    tbody tr.selected{background:var(--accent-bg)!important;outline:2px solid var(--accent);outline-offset:-2px}
    .pill{display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:999px;font-size:10px;font-weight:600;border:1px solid}
    .pill-pass{border-color:var(--ok-border);background:var(--ok-bg);color:var(--ok)}
    .pill-fail{border-color:var(--bad-border);background:var(--bad-bg);color:var(--bad)}
    .mono{font-family:'JetBrains Mono',ui-monospace,monospace}
    .sidebar{background:var(--surface);border:1px solid var(--border);border-radius:10px;box-shadow:var(--shadow);display:flex;flex-direction:column;min-height:0;overflow:hidden}
    .sb-head{padding:10px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px}
    .sb-head strong{font-size:13px;font-weight:600}
    .sb-head .pill{margin-left:auto}
    .sb-meta{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border);border-bottom:1px solid var(--border)}
    .meta-cell{background:var(--surface);padding:8px 12px}
    .meta-cell .lbl{font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:2px}
    .meta-cell .val{font-size:12px;font-weight:600;font-family:'JetBrains Mono',monospace;word-break:break-all}
    .tabs{display:flex;border-bottom:1px solid var(--border);background:var(--surface-2);overflow-x:auto}
    .tab-btn{border:none;border-bottom:2px solid transparent;border-radius:0;padding:8px 12px;background:transparent;cursor:pointer;font-size:11px;font-weight:500;color:var(--muted);margin-bottom:-1px;transition:color .12s,border-color .12s;white-space:nowrap}
    .tab-btn:hover{color:var(--text)}
    .tab-btn.active{color:var(--accent);border-bottom-color:var(--accent);font-weight:600}
    .code-out{margin:0;padding:12px 14px;white-space:pre-wrap;word-break:break-word;overflow:auto;flex:1;background:var(--code-bg);color:var(--code-fg);font-size:12px;line-height:1.5;font-family:'JetBrains Mono',monospace;min-height:0}
    .hidden{display:none}
    label{font-size:12px;display:flex;align-items:center;gap:4px;color:var(--muted);cursor:pointer;white-space:nowrap}
    input[type="checkbox"]{accent-color:var(--accent)}
    input[type="number"]{width:80px}
    @media(max-width:1024px){.main{grid-template-columns:1fr}.sidebar{max-height:50vh}}
    @media(max-width:640px){.wrap{padding:12px;gap:10px}.stats{gap:6px}.controls{gap:4px}input[type="search"]{min-width:140px}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <h1>__TITLE__</h1>
      <button class="theme-btn" id="theme-toggle" title="Toggle theme">\u2600</button>
    </div>
    <div class="stats" id="summary-cards"></div>
    <div class="controls">
      <input id="search" type="search" placeholder="Search candidates, errors, code\u2026">
      <select id="status-filter" title="Status"><option value="all">All status</option><option value="passed">Passed</option><option value="failed">Failed</option><option value="timeout">Timeout</option></select>
      <select id="language-filter" title="Language"><option value="all">All languages</option></select>
      <select id="phase-filter" title="Phase"><option value="all">All phases</option></select>
      <select id="mode-filter" title="Mode"><option value="all">All modes</option></select>
      <select id="candidate-mode-filter" title="Candidate mode"><option value="all">All candidates</option></select>
      <select id="sort-by" title="Sort"><option value="score_desc">Score \u2193</option><option value="duration_asc">Duration \u2191</option><option value="candidate_id">ID</option></select>
      <label><input id="partial-only" type="checkbox"> Partial</label>
      <input id="score-min" type="number" min="0" max="1" step="0.01" placeholder="Min score">
      <button class="btn-ghost" id="export-json" type="button">\u2b07 Export</button>
    </div>
    <div class="main">
      <div class="table-panel">
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th>Candidate</th><th>Score</th><th>Status</th><th>Tests</th><th>Duration</th><th>Phase</th><th>Exit</th>
            </tr></thead>
            <tbody id="rows"></tbody>
          </table>
        </div>
      </div>
      <div class="sidebar" id="sidebar">
        <div class="sb-head"><strong>Detail</strong><span id="detail-id" class="mono"></span></div>
        <div class="sb-meta" id="detail-meta"></div>
        <div class="tabs" id="tabs"></div>
        <pre class="code-out" id="tab-content">Select a row to inspect.</pre>
      </div>
    </div>
  </div>

  <script id="coderoll-data" type="application/json">__DATA__</script>
  <script>
  (function () {
    var records = JSON.parse(document.getElementById("coderoll-data").textContent);
    var ui = {
      search: document.getElementById("search"),
      status: document.getElementById("status-filter"),
      language: document.getElementById("language-filter"),
      phase: document.getElementById("phase-filter"),
      mode: document.getElementById("mode-filter"),
      candidateMode: document.getElementById("candidate-mode-filter"),
      partialOnly: document.getElementById("partial-only"),
      scoreMin: document.getElementById("score-min"),
      sort: document.getElementById("sort-by"),
      exportBtn: document.getElementById("export-json"),
      rows: document.getElementById("rows"),
      cards: document.getElementById("summary-cards"),
      detailId: document.getElementById("detail-id"),
      detailMeta: document.getElementById("detail-meta"),
      tabs: document.getElementById("tabs"),
      tabContent: document.getElementById("tab-content"),
      themeBtn: document.getElementById("theme-toggle"),
    };

    var TAB_NAMES = ["Code", "Files", "stdout", "stderr", "Score", "Prompt", "Setup", "Eval", "Meta", "Raw"];
    var state = { filtered: [], selectedIndex: -1, activeTab: "Code" };

    function applyTheme(t) {
      document.documentElement.setAttribute("data-theme", t);
      ui.themeBtn.textContent = t === "dark" ? "\\u2600" : "\\u263e";
      try { localStorage.setItem("coderoll-theme", t); } catch(e) {}
    }
    ui.themeBtn.addEventListener("click", function() {
      applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
    });
    try { var saved = localStorage.getItem("coderoll-theme"); if (saved) applyTheme(saved); } catch(e) {}

    function asText(v) { return v === null || v === undefined ? "" : String(v); }

    function rank(a, b) {
      if (b.score !== a.score) return b.score - a.score;
      if ((b.passed?1:0) !== (a.passed?1:0)) return (b.passed?1:0) - (a.passed?1:0);
      if (a.duration_ms !== b.duration_ms) return a.duration_ms - b.duration_ms;
      return asText(a.candidate_id).localeCompare(asText(b.candidate_id));
    }

    function matchesSearch(r, q) {
      if (!q) return true;
      return [r.candidate_id,r.task_id,r.error,r.code,r.files?JSON.stringify(r.files):"",r.stdout,r.stderr,r.language,r.phase,r.mode,r.candidate_mode,r.project_path,r.score_details?JSON.stringify(r.score_details):""].map(asText).join(" ").toLowerCase().includes(q);
    }

    function filterSort() {
      var q = ui.search.value.trim().toLowerCase();
      var st = ui.status.value, lang = ui.language.value, ph = ui.phase.value;
      var mo = ui.mode.value, cm = ui.candidateMode.value;
      var po = ui.partialOnly.checked;
      var minR = ui.scoreMin.value.trim(), sMin = minR === "" ? null : Number(minR);
      var sort = ui.sort.value;
      state.filtered = records.filter(function(r) {
        var score = Number(r.score) || 0;
        if (!matchesSearch(r, q)) return false;
        if (st !== "all") {
          if (st === "passed" && !r.passed) return false;
          if (st === "failed" && r.passed) return false;
          if (st === "timeout" && !r.timed_out) return false;
        }
        if (lang !== "all" && asText(r.language||"").toLowerCase() !== lang) return false;
        if (ph !== "all" && asText(r.phase||"").toLowerCase() !== ph) return false;
        if (mo !== "all" && asText(r.mode||"").toLowerCase() !== mo) return false;
        if (cm !== "all" && asText(r.candidate_mode||"").toLowerCase() !== cm) return false;
        if (po && !(score > 0 && !r.passed)) return false;
        if (sMin !== null && score < sMin) return false;
        return true;
      });
      if (sort === "score_desc") state.filtered.sort(rank);
      else if (sort === "duration_asc") state.filtered.sort(function(a,b){ return (a.duration_ms||0)-(b.duration_ms||0); });
      else if (sort === "candidate_id") state.filtered.sort(function(a,b){ return asText(a.candidate_id).localeCompare(asText(b.candidate_id)); });
    }

    function renderSummary() {
      var f = state.filtered, t = f.length;
      var p = f.filter(function(r){return !!r.passed}).length;
      var fl = t - p;
      var to = f.filter(function(r){return !!r.timed_out}).length;
      var avg = t ? Math.round(f.reduce(function(a,r){return a+(Number(r.duration_ms)||0)},0)/t) : 0;
      var best = t ? Math.max.apply(null, f.map(function(r){return Number(r.score)||0})) : 0;
      var data = [
        ["Total", t, "dot-accent"],
        ["Passed", p, "dot-ok"],
        ["Failed", fl, "dot-bad"],
        ["Timeout", to, "dot-warn"],
        ["Best", best.toFixed(2), "dot-accent"],
        ["Avg", avg + "ms", "dot-warn"],
      ];
      ui.cards.innerHTML = "";
      data.forEach(function(d) {
        var el = document.createElement("div"); el.className = "stat";
        el.innerHTML = '<span class="dot '+d[2]+'"></span>'+d[0]+': <span class="num">'+d[1]+'</span>';
        ui.cards.appendChild(el);
      });
    }

    function testsText(r) {
      if (r.tests_passed == null || r.tests_total == null) return "";
      return r.tests_passed + "/" + r.tests_total;
    }

    function renderRows() {
      ui.rows.innerHTML = "";
      state.filtered.forEach(function(r, i) {
        var tr = document.createElement("tr");
        if (state.selectedIndex === i) tr.className = "selected";
        tr.addEventListener("click", function() {
          state.selectedIndex = i;
          renderRows(); renderDetail();
        });
        var cells = [
          [asText(r.candidate_id), "mono"],
          [Number(r.score||0).toFixed(3), "mono"],
          null,
          [testsText(r), "mono"],
          [asText(r.duration_ms)+"ms", "mono"],
          [asText(r.phase||""), ""],
          [asText(r.exit_code), "mono"],
        ];
        cells.forEach(function(c, ci) {
          var td = document.createElement("td");
          if (ci === 2) {
            var pill = document.createElement("span");
            pill.className = "pill " + (r.passed ? "pill-pass" : "pill-fail");
            pill.textContent = r.passed ? "\\u2713 pass" : "\\u2717 fail";
            td.appendChild(pill);
          } else {
            if (c[1]) td.className = c[1];
            td.textContent = c[0];
          }
          tr.appendChild(td);
        });
        ui.rows.appendChild(tr);
      });
    }

    function renderTabs() {
      ui.tabs.innerHTML = "";
      TAB_NAMES.forEach(function(name) {
        var btn = document.createElement("button");
        btn.type = "button"; btn.className = "tab-btn";
        btn.textContent = name;
        if (state.activeTab === name) btn.classList.add("active");
        btn.addEventListener("click", function() {
          state.activeTab = name; renderTabs(); renderContent();
        });
        ui.tabs.appendChild(btn);
      });
    }

    function renderDetail() {
      var r = state.filtered[state.selectedIndex];
      if (!r) {
        ui.detailId.textContent = "";
        ui.detailMeta.innerHTML = "";
        ui.tabContent.textContent = "Select a row to inspect.";
        renderTabs(); return;
      }
      ui.detailId.textContent = " " + asText(r.candidate_id);
      var pairs = [
        ["Score", Number(r.score||0).toFixed(3)],
        ["Duration", (r.duration_ms||0)+"ms"],
        ["Language", asText(r.language||"n/a")],
        ["Phase", asText(r.phase||"n/a")],
        ["Tests", testsText(r)||"n/a"],
        ["Exit Code", asText(r.exit_code)],
        ["Mode", asText(r.mode||"n/a")],
        ["Setup", r.setup_passed==null?"n/a":(r.setup_passed?"pass":"fail")],
      ];
      ui.detailMeta.innerHTML = "";
      pairs.forEach(function(p) {
        var d = document.createElement("div"); d.className = "meta-cell";
        d.innerHTML = '<div class="lbl">'+p[0]+'</div><div class="val">'+p[1]+'</div>';
        ui.detailMeta.appendChild(d);
      });
      renderTabs(); renderContent();
    }

    function renderContent() {
      var r = state.filtered[state.selectedIndex];
      if (!r) { ui.tabContent.textContent = "Select a row to inspect."; return; }
      var t = state.activeTab;
      if (t==="Code") ui.tabContent.textContent = asText(r.code);
      else if (t==="Files") ui.tabContent.textContent = r.files ? JSON.stringify(r.files,null,2) : "";
      else if (t==="stdout") ui.tabContent.textContent = asText(r.stdout);
      else if (t==="stderr") ui.tabContent.textContent = asText(r.stderr);
      else if (t==="Score") ui.tabContent.textContent = JSON.stringify(r.score_details||{},null,2);
      else if (t==="Prompt") ui.tabContent.textContent = asText(r.prompt);
      else if (t==="Setup") ui.tabContent.textContent = JSON.stringify(r.setup_results||[],null,2);
      else if (t==="Eval") ui.tabContent.textContent = JSON.stringify((r.command_results||[]).filter(function(c){return c.phase==="eval"}),null,2);
      else if (t==="Meta") ui.tabContent.textContent = JSON.stringify(r.metadata||{},null,2);
      else ui.tabContent.textContent = JSON.stringify(r,null,2);
    }

    function exportFiltered() {
      var d = JSON.stringify(state.filtered,null,2);
      var b = new Blob([d],{type:"application/json;charset=utf-8"});
      var u = URL.createObjectURL(b);
      var a = document.createElement("a"); a.href = u; a.download = "coderoll.filtered.json";
      document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(u);
    }

    function refresh() {
      filterSort();
      if (state.selectedIndex >= state.filtered.length) state.selectedIndex = state.filtered.length ? 0 : -1;
      if (state.selectedIndex === -1 && state.filtered.length) state.selectedIndex = 0;
      renderSummary(); renderRows(); renderDetail();
    }

    [ui.search].forEach(function(el){el.addEventListener("input",refresh)});
    [ui.status,ui.language,ui.phase,ui.mode,ui.candidateMode,ui.sort].forEach(function(el){el.addEventListener("change",refresh)});
    ui.partialOnly.addEventListener("change",refresh);
    ui.scoreMin.addEventListener("input",refresh);
    ui.exportBtn.addEventListener("click",exportFiltered);

    function unique(arr){return Array.from(new Set(arr)).sort()}
    function populate(sel,vals){vals.forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;sel.appendChild(o)})}
    populate(ui.language, unique(records.map(function(r){return asText(r.language||"").toLowerCase()}).filter(Boolean)));
    populate(ui.phase, unique(records.map(function(r){return asText(r.phase||"").toLowerCase()}).filter(Boolean)));
    populate(ui.mode, unique(records.map(function(r){return asText(r.mode||"").toLowerCase()}).filter(Boolean)));
    populate(ui.candidateMode, unique(records.map(function(r){return asText(r.candidate_mode||"").toLowerCase()}).filter(Boolean)));
    refresh();
  })();
  </script>
</body>
</html>
"""
    return template.replace("__TITLE__", safe_title).replace("__DATA__", data_json)


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
