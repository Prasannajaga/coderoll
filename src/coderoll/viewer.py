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
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #f8f9fc;
      --card: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --border: #e5e7eb;
      --ok: #059669;
      --ok-bg: #ecfdf5;
      --ok-border: #a7f3d0;
      --bad: #dc2626;
      --bad-bg: #fef2f2;
      --bad-border: #fca5a5;
      --warn: #d97706;
      --warn-bg: #fffbeb;
      --accent: #4f46e5;
      --accent-light: #eef2ff;
      --radius: 10px;
      --shadow-sm: 0 1px 2px rgba(0,0,0,.04);
      --shadow-md: 0 2px 8px rgba(0,0,0,.06);
      --transition: 150ms ease;
    }
    * { box-sizing: border-box; margin: 0; }
    body {
      margin: 0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      color: var(--text);
      background: var(--bg);
      -webkit-font-smoothing: antialiased;
    }
    .wrap {
      max-width: 1360px;
      margin: 0 auto;
      padding: 24px 28px;
      display: grid;
      gap: 20px;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.3;
    }
    .subtitle {
      margin-top: 6px;
      color: var(--muted);
      font-size: 14px;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(6, minmax(110px, 1fr));
      gap: 12px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 14px 16px;
      box-shadow: var(--shadow-sm);
      transition: box-shadow var(--transition), transform var(--transition);
      position: relative;
      overflow: hidden;
    }
    .card:hover {
      box-shadow: var(--shadow-md);
      transform: translateY(-1px);
    }
    .card::before {
      content: '';
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 3px;
      background: var(--border);
    }
    .card.card-ok::before { background: var(--ok); }
    .card.card-bad::before { background: var(--bad); }
    .card.card-warn::before { background: var(--warn); }
    .card.card-accent::before { background: var(--accent); }
    .label {
      color: var(--muted);
      font-size: 11px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 6px;
    }
    .value {
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.01em;
    }
    .controls {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 12px 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      box-shadow: var(--shadow-sm);
    }
    input, select, button {
      font-family: inherit;
      font-size: 13px;
      border: 1px solid var(--border);
      border-radius: 7px;
      padding: 7px 10px;
      background: #fff;
      color: var(--text);
      transition: border-color var(--transition), box-shadow var(--transition);
      outline: none;
    }
    input:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(79,70,229,.1);
    }
    input[type="search"] {
      min-width: 240px;
      flex: 1;
    }
    button {
      cursor: pointer;
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
      font-weight: 600;
      font-size: 13px;
      transition: opacity var(--transition);
    }
    button:hover { opacity: 0.88; }
    .table-panel, .detail {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      box-shadow: var(--shadow-sm);
    }
    .table-wrap {
      overflow: auto;
      max-height: 52vh;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    thead th {
      text-align: left;
      position: sticky;
      top: 0;
      z-index: 2;
      background: #f9fafb;
      border-bottom: 2px solid var(--border);
      padding: 10px 12px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }
    tbody td {
      border-bottom: 1px solid #f3f4f6;
      padding: 9px 12px;
      vertical-align: middle;
    }
    tbody tr {
      transition: background var(--transition);
      cursor: pointer;
    }
    tbody tr:hover {
      background: #f9fafb;
    }
    tbody tr.pass {
      background: var(--ok-bg);
    }
    tbody tr.fail {
      background: var(--bad-bg);
    }
    tbody tr.selected {
      outline: 2px solid var(--accent);
      outline-offset: -2px;
      background: var(--accent-light);
    }
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 600;
      border: 1px solid var(--border);
      background: #f9fafb;
    }
    .status-pill.pass {
      border-color: var(--ok-border);
      background: var(--ok-bg);
      color: var(--ok);
    }
    .status-pill.fail {
      border-color: var(--bad-border);
      background: var(--bad-bg);
      color: var(--bad);
    }
    .mono {
      font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    .snip {
      max-width: 520px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .hidden {
      display: none;
    }
    .detail {
      display: grid;
      grid-template-rows: auto auto 1fr;
      min-height: 280px;
    }
    .detail-head {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .detail-head strong {
      font-size: 14px;
      font-weight: 600;
    }
    .detail-meta {
      display: grid;
      grid-template-columns: repeat(3, minmax(120px, 1fr));
      gap: 8px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      background: #fafbfc;
    }
    .meta-item {
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      transition: box-shadow var(--transition);
    }
    .meta-item:hover {
      box-shadow: var(--shadow-sm);
    }
    .meta-item .label {
      margin: 0 0 4px 0;
      font-size: 10px;
    }
    .meta-item .value {
      font-size: 12px;
      font-weight: 600;
      word-break: break-all;
    }
    .tabs {
      display: flex;
      gap: 0;
      border-bottom: 2px solid var(--border);
      padding: 0 16px;
      background: #fafbfc;
    }
    .tab-btn {
      border: none;
      border-bottom: 2px solid transparent;
      border-radius: 0;
      padding: 10px 14px;
      background: transparent;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      color: var(--muted);
      margin-bottom: -2px;
      transition: color var(--transition), border-color var(--transition);
    }
    .tab-btn:hover {
      color: var(--text);
    }
    .tab-btn.active {
      color: var(--accent);
      border-bottom-color: var(--accent);
      font-weight: 600;
    }
    pre {
      margin: 0;
      padding: 16px;
      white-space: pre-wrap;
      word-break: break-word;
      overflow: auto;
      max-height: 36vh;
      background: #1e1e2e;
      color: #cdd6f4;
      font-size: 13px;
      line-height: 1.55;
      border-top: 0;
    }
    @media (max-width: 980px) {
      .cards { grid-template-columns: repeat(3, minmax(100px, 1fr)); }
      .detail-meta { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
      input[type="search"] { min-width: 160px; }
    }
    @media (max-width: 640px) {
      .wrap { padding: 16px; gap: 14px; }
      .cards { grid-template-columns: repeat(2, 1fr); }
      .detail-meta { grid-template-columns: 1fr; }
      .tabs { overflow-x: auto; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>__TITLE__</h1>
      <div class="subtitle">Standalone static report. No server required.</div>
    </header>

    <section class="cards" id="summary-cards"></section>

    <section class="controls">
      <input id="search" type="search" placeholder="Search candidate_id, task_id, error, code, stdout, stderr...">
      <select id="status-filter" title="Status filter">
        <option value="all">all</option>
        <option value="passed">passed</option>
        <option value="failed">failed</option>
        <option value="timeout">timeout</option>
      </select>
      <select id="language-filter" title="Language filter">
        <option value="all">all languages</option>
      </select>
      <select id="phase-filter" title="Phase filter">
        <option value="all">all phases</option>
      </select>
      <select id="mode-filter" title="Mode filter">
        <option value="all">all modes</option>
      </select>
      <select id="candidate-mode-filter" title="Candidate mode filter">
        <option value="all">all candidate modes</option>
      </select>
      <label><input id="partial-only" type="checkbox"> partial only</label>
      <input id="score-min" type="number" min="0" max="1" step="0.01" placeholder="score min">
      <select id="sort-by" title="Sort by">
        <option value="score_desc">score desc</option>
        <option value="duration_asc">duration asc</option>
        <option value="candidate_id">candidate id</option>
      </select>
      <label><input id="show-code-table" type="checkbox"> show code snippets in table</label>
      <button id="export-json" type="button">Export filtered JSON</button>
    </section>

    <section class="table-panel">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>mode</th>
              <th>candidate_id</th>
              <th>candidate_mode</th>
              <th>phase</th>
              <th>score</th>
              <th>passed</th>
              <th>tests</th>
              <th>setup</th>
              <th>duration_ms</th>
              <th>exit_code</th>
              <th>timed_out</th>
              <th>error</th>
              <th id="code-header" class="hidden">code_snippet</th>
            </tr>
          </thead>
          <tbody id="rows"></tbody>
        </table>
      </div>
    </section>

    <section class="detail">
      <div class="detail-head">
        <strong>Detail</strong>
        <span id="detail-id" class="mono"></span>
      </div>
      <div class="detail-meta" id="detail-meta"></div>
      <div>
        <div class="tabs" id="tabs"></div>
        <pre id="tab-content" class="mono"></pre>
      </div>
    </section>
  </div>

  <script id="coderoll-data" type="application/json">__DATA__</script>
  <script>
  (function () {
    const records = JSON.parse(document.getElementById("coderoll-data").textContent);
    const ui = {
      search: document.getElementById("search"),
      status: document.getElementById("status-filter"),
      language: document.getElementById("language-filter"),
      phase: document.getElementById("phase-filter"),
      mode: document.getElementById("mode-filter"),
      candidateMode: document.getElementById("candidate-mode-filter"),
      partialOnly: document.getElementById("partial-only"),
      scoreMin: document.getElementById("score-min"),
      sort: document.getElementById("sort-by"),
      showCode: document.getElementById("show-code-table"),
      exportBtn: document.getElementById("export-json"),
      rows: document.getElementById("rows"),
      codeHeader: document.getElementById("code-header"),
      cards: document.getElementById("summary-cards"),
      detailId: document.getElementById("detail-id"),
      detailMeta: document.getElementById("detail-meta"),
      tabs: document.getElementById("tabs"),
      tabContent: document.getElementById("tab-content"),
    };

    const TAB_NAMES = ["Summary", "Files", "Code", "Setup results", "Eval command results", "stdout", "stderr", "Score", "Prompt", "Metadata", "Raw JSON"];
    let state = {
      filtered: [],
      selectedIndex: -1,
      activeTab: "Code",
    };

    function asText(value) {
      if (value === null || value === undefined) return "";
      return String(value);
    }

    function codeSnippet(text) {
      return asText(text).replace(/\\s+/g, " ").slice(0, 160);
    }

    function rank(a, b) {
      if (b.score !== a.score) return b.score - a.score;
      if ((b.passed ? 1 : 0) !== (a.passed ? 1 : 0)) return (b.passed ? 1 : 0) - (a.passed ? 1 : 0);
      if (a.duration_ms !== b.duration_ms) return a.duration_ms - b.duration_ms;
      return asText(a.candidate_id).localeCompare(asText(b.candidate_id));
    }

    function matchesSearch(record, query) {
      if (!query) return true;
      const haystack = [
        record.candidate_id,
        record.task_id,
        record.error,
        record.code,
        record.files ? JSON.stringify(record.files) : "",
        record.stdout,
        record.stderr,
        record.language,
        record.phase,
        record.mode,
        record.candidate_mode,
        record.project_path,
        record.score_details ? JSON.stringify(record.score_details) : "",
      ].map(asText).join(" ").toLowerCase();
      return haystack.includes(query);
    }

    function matchesStatus(record, status) {
      if (status === "all") return true;
      if (status === "passed") return !!record.passed;
      if (status === "failed") return !record.passed;
      if (status === "timeout") return !!record.timed_out;
      return true;
    }

    function matchesLanguage(record, language) {
      if (language === "all") return true;
      return asText(record.language || "").toLowerCase() === language;
    }

    function matchesPhase(record, phase) {
      if (phase === "all") return true;
      return asText(record.phase || "").toLowerCase() === phase;
    }

    function matchesMode(record, mode) {
      if (mode === "all") return true;
      return asText(record.mode || "").toLowerCase() === mode;
    }

    function matchesCandidateMode(record, mode) {
      if (mode === "all") return true;
      return asText(record.candidate_mode || "").toLowerCase() === mode;
    }

    function filterSortRecords() {
      const query = ui.search.value.trim().toLowerCase();
      const status = ui.status.value;
      const language = ui.language.value;
      const phase = ui.phase.value;
      const mode = ui.mode.value;
      const candidateMode = ui.candidateMode.value;
      const partialOnly = ui.partialOnly.checked;
      const minRaw = ui.scoreMin.value.trim();
      const scoreMin = minRaw === "" ? null : Number(minRaw);
      const sort = ui.sort.value;
      const filtered = records.filter((r) => {
        const score = Number(r.score) || 0;
        return matchesSearch(r, query)
          && matchesStatus(r, status)
          && matchesLanguage(r, language)
          && matchesPhase(r, phase)
          && matchesMode(r, mode)
          && matchesCandidateMode(r, candidateMode)
          && (!partialOnly || (score > 0 && !r.passed))
          && (scoreMin === null || score >= scoreMin);
      });

      if (sort === "score_desc") {
        filtered.sort(rank);
      } else if (sort === "duration_asc") {
        filtered.sort((a, b) => {
          if (a.duration_ms !== b.duration_ms) return a.duration_ms - b.duration_ms;
          return asText(a.candidate_id).localeCompare(asText(b.candidate_id));
        });
      } else if (sort === "candidate_id") {
        filtered.sort((a, b) => asText(a.candidate_id).localeCompare(asText(b.candidate_id)));
      }
      state.filtered = filtered;
    }

    function summaryFrom(list) {
      const total = list.length;
      const passed = list.filter((r) => !!r.passed).length;
      const failed = list.filter((r) => !r.passed).length;
      const timeout = list.filter((r) => !!r.timed_out).length;
      const best = total ? Math.max(...list.map((r) => Number(r.score) || 0)) : 0;
      const avgDuration = total
        ? Math.round(list.reduce((acc, r) => acc + (Number(r.duration_ms) || 0), 0) / total)
        : 0;
      return { total, passed, failed, timeout, best, avgDuration };
    }

    function renderSummary() {
      const sum = summaryFrom(state.filtered);
      const cards = [
        ["Total", sum.total, "card-accent"],
        ["Passed", sum.passed, "card-ok"],
        ["Failed", sum.failed, "card-bad"],
        ["Timeout", sum.timeout, "card-warn"],
        ["Best Score", sum.best.toFixed(3), "card-accent"],
        ["Avg Duration", sum.avgDuration + "ms", ""],
      ];
      ui.cards.innerHTML = "";
      cards.forEach(([label, value, cls]) => {
        const card = document.createElement("div");
        card.className = "card" + (cls ? " " + cls : "");
        const labelEl = document.createElement("div");
        labelEl.className = "label";
        labelEl.textContent = label;
        const valueEl = document.createElement("div");
        valueEl.className = "value mono";
        valueEl.textContent = String(value);
        card.appendChild(labelEl);
        card.appendChild(valueEl);
        ui.cards.appendChild(card);
      });
    }

    function renderRows() {
      ui.rows.innerHTML = "";
      const showCode = ui.showCode.checked;
      ui.codeHeader.classList.toggle("hidden", !showCode);

      state.filtered.forEach((record, idx) => {
        const tr = document.createElement("tr");
        tr.className = record.passed ? "pass" : "fail";
        if (state.selectedIndex === idx) tr.classList.add("selected");
        tr.addEventListener("click", function () {
          state.selectedIndex = idx;
          if (state.activeTab === "") state.activeTab = "Code";
          renderRows();
          renderDetail();
        });

        addCell(tr, asText(record.mode || ""), "mono");
        addCell(tr, asText(record.candidate_id), "mono");
        addCell(tr, asText(record.candidate_mode || ""), "mono");
        addCell(tr, asText(record.phase || ""), "mono");
        addCell(tr, Number(record.score || 0).toFixed(3), "mono");
        const statusCell = document.createElement("td");
        const pill = document.createElement("span");
        pill.className = "status-pill " + (record.passed ? "pass" : "fail");
        pill.textContent = record.passed ? "\u2713 pass" : "\u2717 fail";
        statusCell.appendChild(pill);
        tr.appendChild(statusCell);
        addCell(tr, testsText(record), "mono");
        addCell(tr, setupText(record), "mono");
        addCell(tr, asText(record.duration_ms), "mono");
        addCell(tr, asText(record.exit_code), "mono");
        addCell(tr, asText(record.timed_out), "mono");
        addCell(tr, asText(record.error), "mono");
        const codeTd = addCell(tr, codeSnippet(record.files ? JSON.stringify(record.files) : record.code), "mono snip");
        codeTd.classList.toggle("hidden", !showCode);

        ui.rows.appendChild(tr);
      });
    }

    function testsText(record) {
      const passed = record.tests_passed;
      const total = record.tests_total;
      if (passed === null || passed === undefined || total === null || total === undefined) return "";
      return asText(passed) + "/" + asText(total);
    }

    function setupText(record) {
      if (record.setup_passed !== null && record.setup_passed !== undefined) {
        return record.setup_passed ? "pass" : "fail";
      }
      if (record.build_passed === null || record.build_passed === undefined) return "n/a";
      return record.build_passed ? "pass" : "fail";
    }

    function addCell(tr, text, className) {
      const td = document.createElement("td");
      if (className) td.className = className;
      td.textContent = asText(text);
      tr.appendChild(td);
      return td;
    }

    function renderTabs() {
      ui.tabs.innerHTML = "";
      TAB_NAMES.forEach((name) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "tab-btn";
        btn.textContent = name;
        if (state.activeTab === name) btn.classList.add("active");
        btn.addEventListener("click", function () {
          state.activeTab = name;
          renderTabs();
          renderDetailContent();
        });
        ui.tabs.appendChild(btn);
      });
    }

    function renderDetail() {
      const record = state.filtered[state.selectedIndex];
      if (!record) {
        ui.detailId.textContent = " (select a row)";
        ui.detailMeta.innerHTML = "";
        renderTabs();
        ui.tabContent.textContent = "Select a candidate to inspect details.";
        return;
      }

      ui.detailId.textContent = " " + asText(record.candidate_id);
      const pairs = [
        ["candidate_id", record.candidate_id],
        ["task_id", record.task_id],
        ["config_id", record.config_id],
        ["mode", record.mode],
        ["candidate_mode", record.candidate_mode],
        ["project_path", record.project_path],
        ["language", record.language],
        ["phase", record.phase],
        ["image", record.image],
        ["score", Number(record.score || 0).toFixed(3)],
        ["passed", record.passed],
        ["tests", testsText(record)],
        ["setup", setupText(record)],
        ["setup_exit_code", record.setup_exit_code],
        ["duration_ms", record.duration_ms],
        ["exit_code", record.exit_code],
        ["code_hash", record.code_hash],
        ["test_hash", record.test_hash],
        ["created_at", record.created_at],
      ];

      ui.detailMeta.innerHTML = "";
      pairs.forEach(([key, value]) => {
        const box = document.createElement("div");
        box.className = "meta-item";
        const l = document.createElement("div");
        l.className = "label";
        l.textContent = key;
        const v = document.createElement("div");
        v.className = "value mono";
        v.textContent = asText(value);
        box.appendChild(l);
        box.appendChild(v);
        ui.detailMeta.appendChild(box);
      });

      renderTabs();
      renderDetailContent();
    }

    function renderDetailContent() {
      const record = state.filtered[state.selectedIndex];
      if (!record) {
        ui.tabContent.textContent = "Select a candidate to inspect details.";
        return;
      }
      const tab = state.activeTab;
      if (tab === "Summary") {
        ui.tabContent.textContent = JSON.stringify({
          mode: record.mode,
          candidate_id: record.candidate_id,
          candidate_mode: record.candidate_mode,
          project_path: record.project_path,
          score: record.score,
          passed: record.passed,
          phase: record.phase,
          tests_passed: record.tests_passed,
          tests_total: record.tests_total,
          duration_ms: record.duration_ms,
          error: record.error,
        }, null, 2);
      } else if (tab === "Files") {
        ui.tabContent.textContent = record.files ? JSON.stringify(record.files, null, 2) : "";
      } else if (tab === "Code") {
        ui.tabContent.textContent = asText(record.code);
      } else if (tab === "stdout") {
        ui.tabContent.textContent = asText(record.stdout);
      } else if (tab === "stderr") {
        ui.tabContent.textContent = asText(record.stderr);
      } else if (tab === "Setup results") {
        ui.tabContent.textContent = JSON.stringify(record.setup_results || [], null, 2);
      } else if (tab === "Eval command results") {
        ui.tabContent.textContent = JSON.stringify((record.command_results || []).filter((r) => r.phase === "eval"), null, 2);
      } else if (tab === "Score") {
        ui.tabContent.textContent = JSON.stringify(record.score_details || {}, null, 2);
      } else if (tab === "Prompt") {
        ui.tabContent.textContent = asText(record.prompt);
      } else if (tab === "Metadata") {
        ui.tabContent.textContent = JSON.stringify(record.metadata || {}, null, 2);
      } else {
        ui.tabContent.textContent = JSON.stringify(record, null, 2);
      }
    }

    function exportFiltered() {
      const data = JSON.stringify(state.filtered, null, 2);
      const blob = new Blob([data], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "coderoll.filtered.json";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }

    function refresh() {
      filterSortRecords();
      if (state.selectedIndex >= state.filtered.length) {
        state.selectedIndex = state.filtered.length ? 0 : -1;
      }
      if (state.selectedIndex === -1 && state.filtered.length) {
        state.selectedIndex = 0;
      }
      renderSummary();
      renderRows();
      renderDetail();
    }

    ui.search.addEventListener("input", refresh);
    ui.status.addEventListener("change", refresh);
    ui.language.addEventListener("change", refresh);
    ui.phase.addEventListener("change", refresh);
    ui.mode.addEventListener("change", refresh);
    ui.candidateMode.addEventListener("change", refresh);
    ui.partialOnly.addEventListener("change", refresh);
    ui.scoreMin.addEventListener("input", refresh);
    ui.sort.addEventListener("change", refresh);
    ui.showCode.addEventListener("change", renderRows);
    ui.exportBtn.addEventListener("click", exportFiltered);

    populateSelect(ui.language, uniqueValues(records.map((r) => asText(r.language || "").toLowerCase()).filter(Boolean)));
    populateSelect(ui.phase, uniqueValues(records.map((r) => asText(r.phase || "").toLowerCase()).filter(Boolean)));
    populateSelect(ui.mode, uniqueValues(records.map((r) => asText(r.mode || "").toLowerCase()).filter(Boolean)));
    populateSelect(ui.candidateMode, uniqueValues(records.map((r) => asText(r.candidate_mode || "").toLowerCase()).filter(Boolean)));
    refresh();

    function uniqueValues(values) {
      return Array.from(new Set(values)).sort();
    }

    function populateSelect(select, values) {
      values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      });
    }
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
