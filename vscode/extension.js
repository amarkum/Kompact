// Kompactor for VS Code: wires Kompactor's hooks into Claude Code (the VS Code
// extension and the CLI share ~/.claude/settings.json), shows tokens and
// dollars saved in the status bar and an activity-bar sidebar, and hosts the
// settings dashboard in a webview.
// Plain JavaScript, no dependencies, no build step.

const vscode = require("vscode");
const cp = require("child_process");
const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");

let ctx;
let status;
let server;          // child process running `kompactor ui`
let dashboardUrl;    // http://127.0.0.1:port/
let panel;           // webview panel
let lastTs = 0;
let pythonCmd;       // [exe, ...args]
let summary = null;  // latest `kompactor gain --json`: tokens and dollars saved
let view = null;     // the activity-bar sidebar
let refreshing = null; // the summary refresh in flight, shared by everyone who asks meanwhile
let refreshAgain = false;

const kompactorHome = () => process.env.KOMPACTOR_HOME || path.join(os.homedir(), ".kompactor");
const livePath = () => path.join(kompactorHome(), "live.json");
const claudeSettings = () => path.join(os.homedir(), ".claude", "settings.json");
const cfg = () => vscode.workspace.getConfiguration("kompactor");

const price = () => Math.max(0, Number(cfg().get("pricePerMillionTokens")) || 0);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function usd(n) {
  n = Number(n) || 0;
  return n >= 1 ? "$" + n.toFixed(2) : n >= 0.0001 ? "$" + n.toFixed(4) : n > 0 ? "$" + n.toPrecision(2) : "$0";
}

// How the dollars were worked out, from the per-model pricing `kompactor gain --json` returns.
function pricingNote(pricing) {
  const rate = (m) => `${m.model} (${usd(m.input)}/M input, cache write ${usd(m.cache_write)}/M, cache read ${usd(m.cache_read)}/M)`;
  const rows = (pricing || []).filter((m) => m.saved > 0);
  if (!rows.length) return "";
  const reads = rows.reduce((a, m) => a + m.rereads, 0) / Math.max(1, rows.reduce((a, m) => a + m.saved, 0));
  const unknown = rows.filter((m) => !m.known);
  return `Dollars are at the API prices of the model each session ran on: ${rows.map(rate).join("; ")}. ` +
    `Each token kept out counts once as a prompt-cache write and again at the cache-read price for every later request ` +
    `that would have re-read it until compaction (${Math.round(reads)} on average).` +
    (unknown.length ? ` Sessions without a model from the status line use ${unknown.map((m) => m.model).join(", ")}.` : "");
}

function fmt(n) {
  n = Number(n) || 0;
  const a = Math.abs(n);
  return a >= 1e6 ? (n / 1e6).toFixed(1) + "M" : a >= 1e3 ? (n / 1e3).toFixed(1) + "k" : String(Math.round(n));
}

// ---------------------------------------------------------------------------
// Python + launcher

function launcher() {
  const bundled = path.join(ctx.extensionPath, "python", "kompactor", "_launch.py");
  if (fs.existsSync(bundled)) return bundled;
  return path.join(ctx.extensionPath, "..", "kompactor", "_launch.py"); // running from the repo
}

function findPython() {
  if (pythonCmd) return pythonCmd;
  const configured = cfg().get("pythonPath");
  const candidates = configured ? [[configured]] :
    process.platform === "win32" ? [["py", "-3"], ["python"], ["python3"]] : [["python3"], ["python"]];
  for (const c of candidates) {
    try {
      const r = cp.spawnSync(c[0], [...c.slice(1), "-c", "import sys; print(sys.version_info >= (3, 9))"],
        { encoding: "utf8", timeout: 5000 });
      if (r.status === 0 && r.stdout.trim() === "True") return (pythonCmd = c);
    } catch (e) { /* try next */ }
  }
  return null;
}

function runKompactor(args, input) {
  return new Promise((resolve) => {
    const py = findPython();
    if (!py) return resolve({ code: -1, stdout: "", stderr: "Python 3.9+ not found. Set kompactor.pythonPath." });
    const p = cp.spawn(py[0], [...py.slice(1), launcher(), ...args], { env: process.env });
    let stdout = "", stderr = "";
    p.stdout.on("data", (d) => (stdout += d));
    p.stderr.on("data", (d) => (stderr += d));
    p.on("error", (e) => resolve({ code: -1, stdout, stderr: String(e) }));
    p.on("close", (code) => resolve({ code, stdout, stderr }));
    if (input) p.stdin.end(input); else p.stdin.end();
  });
}

// ---------------------------------------------------------------------------
// Claude Code settings

function hookCommands() {
  try {
    const s = JSON.parse(fs.readFileSync(claudeSettings(), "utf8"));
    const cmds = [];
    for (const entries of Object.values(s.hooks || {}))
      for (const e of entries || []) for (const h of e.hooks || []) if (String(h.command || "").includes("kompactor")) cmds.push(h.command);
    const plugin = Object.entries(s.enabledPlugins || {}).some(([k, v]) => ["amarkum@kompactor", "kompactor@claude-plugins-official"].includes(k) && v);
    return { cmds, plugin };
  } catch (e) {
    return { cmds: [], plugin: false };
  }
}

async function enable(silent) {
  const r = await runKompactor(["install"]);
  if (r.code !== 0) {
    vscode.window.showErrorMessage(`Kompactor: couldn't enable (${(r.stderr || r.stdout).trim().split("\n").pop()})`);
    return false;
  }
  if (!silent) {
    const pick = await vscode.window.showInformationMessage(
      "Kompactor is on for Claude Code (VS Code and CLI). New sessions will use it.", "Choose quality level", "Open dashboard");
    if (pick === "Choose quality level") choosePreset();
    if (pick === "Open dashboard") openDashboard();
  }
  return true;
}

async function disable() {
  const r = await runKompactor(["install", "--uninstall"]);
  vscode.window.showInformationMessage(r.code === 0 ? "Kompactor hooks removed from Claude Code." : "Kompactor: " + r.stderr);
}

// After an extension update the bundled path changes; keep hooks pointing at it.
async function refreshHooks() {
  const { cmds } = hookCommands();
  const ours = cmds.filter((c) => /extensions[\\/][^"]*kompactor[^"]*_launch\.py/i.test(c));
  if (ours.length && !ours.every((c) => c.includes(launcher()))) await enable(true);
}

async function firstRun() {
  const { cmds, plugin } = hookCommands();
  if (cmds.length || plugin) return refreshHooks();
  if (ctx.globalState.get("kompactor.prompted")) return;
  await ctx.globalState.update("kompactor.prompted", true);
  const pick = await vscode.window.showInformationMessage(
    "Kompactor can cut the tokens Claude Code spends on tool output (often 40–80%). Enable it?",
    "Enable", "Open dashboard", "Not now");
  if (pick === "Enable") enable(false);
  if (pick === "Open dashboard") openDashboard();
}

// ---------------------------------------------------------------------------
// Status bar + per-turn summary

function inThisWindow(project) {
  const folders = vscode.workspace.workspaceFolders || [];
  if (!project || !folders.length) return true;
  return folders.some((f) => {
    const p = f.uri.fsPath;
    return project === p || project.startsWith(p + path.sep) || p.startsWith(project + path.sep);
  });
}

function readLive() {
  try { return JSON.parse(fs.readFileSync(livePath(), "utf8")); } catch (e) { return null; }
}

function sessionUsd(live) {
  return summary && summary.session && live && live.session ? summary.session.usd : null;
}

function renderStatus(live) {
  if (!cfg().get("showStatusBar")) return status.hide();
  const tot = (live && live.session_totals) || {};
  const turn = (live && live.turn) || {};
  if (live && inThisWindow(live.project) && tot.saved > 0) {
    const ctxPct = tot.context && tot.in_context_saved > 0 ? Math.round(100 * tot.in_context_saved / (tot.context + tot.in_context_saved)) : 0;
    const dollars = sessionUsd(live);
    status.text = `$(kompactor-logo) −${fmt(tot.saved)}` + (dollars ? ` · ${usd(dollars)}` : "");
    const md = new vscode.MarkdownString(
      `**Kompactor** · ${live.preset_name || ""}\n\n` +
      (turn.saved > 0 ? `Last turn: **−${fmt(turn.saved)} tokens** (${fmt(turn.raw)} › ${fmt(turn.kept)})\n\n` : "Last turn: nothing to trim\n\n") +
      `This session: −${fmt(tot.saved)} tokens` + (dollars ? `, ${usd(dollars)} saved` : "") +
      (ctxPct ? `, context ≈${ctxPct}% smaller` : "") +
      `\n\n[Open dashboard](command:kompactor.openDashboard) · [Change level](command:kompactor.choosePreset)`);
    md.isTrusted = true;
    status.tooltip = md;
  } else {
    status.text = "$(kompactor-logo) Kompactor";
    status.tooltip = "Kompactor: click for the dashboard or to change the quality vs tokens level";
  }
  status.show();
}

function onLiveChange() {
  const live = readLive();
  renderStatus(live);
  refreshSummary();
  if (!live || live.ts === lastTs) return;
  const isNew = lastTs !== 0;
  lastTs = live.ts;
  if (!isNew || !inThisWindow(live.project) || !(live.turn && live.turn.saved > 0)) return;
  const mode = cfg().get("turnSummary");
  if (mode === "notification") vscode.window.showInformationMessage(live.message);
  else if (mode === "statusBar") vscode.window.setStatusBarMessage(live.message, 8000);
}

async function menu() {
  const live = readLive();
  const items = [
    { label: "$(dashboard) Open dashboard", run: openDashboard },
    { label: "$(settings) Choose quality vs tokens level", run: choosePreset },
    { label: "$(info) Show last turn savings", run: showLastTurn, description: live && live.message ? "" : "no turns yet" },
    { label: "$(link-external) Open dashboard in browser", run: openInBrowser },
  ];
  const { cmds, plugin } = hookCommands();
  items.push(cmds.length || plugin ? { label: "$(circle-slash) Disable for Claude Code", run: disable }
    : { label: "$(check) Enable for Claude Code", run: () => enable(false) });
  const pick = await vscode.window.showQuickPick(items, { title: "Kompactor" });
  if (pick) pick.run();
}

function showLastTurn() {
  const live = readLive();
  vscode.window.showInformationMessage(live && live.message ? live.message : "Kompactor hasn't seen a Claude Code turn yet.");
}

// ---------------------------------------------------------------------------
// Savings summary + activity-bar sidebar

function refreshSummary() {
  if (refreshing) { refreshAgain = true; return refreshing; }
  refreshing = (async () => {
    do {
      refreshAgain = false;
      try {
        const live = readLive();
        const args = ["gain", "--json"];
        if (price() > 0) args.push("--price", String(price()));
        if (live && live.session) args.push("--session", live.session);
        const folder = (vscode.workspace.workspaceFolders || [])[0];
        if (folder) args.push("--project", folder.uri.fsPath);
        const r = await runKompactor(args);
        if (r.code === 0) summary = JSON.parse(r.stdout);
      } catch (e) { /* keep the last summary */ }
    } while (refreshAgain);
    refreshing = null;
    renderStatus(readLive());
    renderView();
  })();
  return refreshing;
}

function ago(ts) {
  const s = Math.max(0, Date.now() / 1000 - ts);
  return s < 60 ? "just now" : s < 3600 ? `${Math.round(s / 60)} min ago` : s < 86400 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`;
}

function viewHtml(webview) {
  const live = readLive();
  const { cmds, plugin } = hookCommands();
  const connected = cmds.length > 0 || plugin;
  const paused = summary && summary.paused;
  const state = !connected ? "Not connected" : paused ? "Stopped" : "On";
  const dot = !connected ? "off" : paused ? "paused" : "on";
  const tot = (live && live.session_totals) || {};
  const turn = (live && live.turn) || {};
  const ctxPct = tot.context && tot.in_context_saved > 0 ? Math.round(100 * tot.in_context_saved / (tot.context + tot.in_context_saved)) : 0;
  const card = (title, p, extra) => p && p.saved > 0
    ? `<div class="card"><div class="lbl">${title}</div><div class="big">−${fmt(p.saved)} <span>tokens</span></div>
       <div class="usd">${usd(p.usd)} saved</div>${extra || ""}</div>`
    : `<div class="card"><div class="lbl">${title}</div><div class="none">Nothing saved yet</div></div>`;
  const sessionExtra = (ctxPct ? `<div class="sub">Context ≈${ctxPct}% smaller</div>` : "") +
    (turn.saved > 0 ? `<div class="sub">Last turn −${fmt(turn.saved)} (${fmt(turn.raw)} › ${fmt(turn.kept)})</div>` : "");
  const all = (summary && summary.turns) || [];
  const helped = all.filter((t) => t.saved > 0);
  const what = (t) => (t.shortened || []).map((x) => esc(x.what) + (x.times > 1 ? ` ×${x.times}` : "")).join(", ") || "tool output";
  const turns = helped.slice(0, 6).map((t) =>
    `<li class="reply"><div class="row"><span class="what">${what(t)}</span><span class="s">−${fmt(t.saved)}</span></div>
     <div class="meta">${ago(t.ts)} · ${fmt(t.raw)} › ${fmt(t.kept)} tokens${t.usd > 0 ? ` · ${usd(t.usd)}` : ""}</div></li>`).join("");
  const quiet = all.length - helped.length;
  const projectName = summary && summary.project_path ? summary.project_path.split(/[\\/]/).pop() : "";
  const top = ((summary && summary.top) || []).filter((t) => t.raw > t.kept).map((t) =>
    `<li><code>${esc(t.cmd)}</code><span>${fmt(t.raw)} › ${fmt(t.kept)}</span></li>`).join("");
  const nonce = Math.random().toString(36).slice(2);
  const action = !connected ? `<button data-cmd="enable">Enable for Claude Code</button>`
    : paused ? `<button data-cmd="start">Start</button>` : `<button class="secondary" data-cmd="stop">Stop</button>`;
  return `<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
<style>
body{padding:4px 12px 16px;color:var(--vscode-foreground);font-family:var(--vscode-font-family);font-size:var(--vscode-font-size)}
.state{display:flex;align-items:center;gap:6px;margin:6px 0 12px;font-weight:600}
.state small{font-weight:400;color:var(--vscode-descriptionForeground)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--vscode-descriptionForeground)}
.dot.on{background:var(--vscode-testing-iconPassed,#3fb950)}.dot.paused{background:var(--vscode-editorWarning-foreground,#d29922)}
.card{border:1px solid var(--vscode-widget-border,var(--vscode-panel-border));border-radius:6px;padding:10px 12px;margin-bottom:10px}
.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--vscode-descriptionForeground);margin-bottom:4px}
.big{font-size:20px;font-weight:600}.big span{font-size:12px;font-weight:400;color:var(--vscode-descriptionForeground)}
.usd{font-size:13px;color:var(--vscode-charts-green,#3fb950);margin-top:2px}
.sub,.none,.note{font-size:12px;color:var(--vscode-descriptionForeground);margin-top:4px}
h3{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--vscode-descriptionForeground);margin:14px 0 6px}
ul{list-style:none;padding:0;margin:0}li{display:flex;justify-content:space-between;gap:8px;padding:3px 0;font-size:12px}
li code{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}li span{color:var(--vscode-descriptionForeground);white-space:nowrap}
li .s{color:var(--vscode-charts-green,#3fb950)}
li.reply{display:block;padding:5px 0;border-bottom:1px solid var(--vscode-widget-border,transparent)}
li.reply .row{display:flex;justify-content:space-between;gap:8px}
li.reply .what{font-family:var(--vscode-editor-font-family);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
li.reply .meta{font-size:11px;color:var(--vscode-descriptionForeground);margin-top:1px}
.btns{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 8px}
button{border:0;border-radius:2px;padding:5px 10px;cursor:pointer;background:var(--vscode-button-background);color:var(--vscode-button-foreground);font:inherit}
button:hover{background:var(--vscode-button-hoverBackground)}
button.secondary{background:var(--vscode-button-secondaryBackground);color:var(--vscode-button-secondaryForeground)}
</style></head><body>
<div class="state"><span class="dot ${dot}"></span>${state}${live && live.preset_name ? ` <small>· ${esc(live.preset_name)}</small>` : ""}</div>
${card("This session", summary && summary.session, sessionExtra)}
${projectName ? card(`This project · ${esc(projectName)}`, summary && summary.project) : ""}
${card("Today", summary && summary.today)}
${card("Last 30 days", summary && summary.all, summary && summary.sessions ? `<div class="sub">${summary.sessions} session${summary.sessions === 1 ? "" : "s"}</div>` : "")}
${all.length ? `<h3>Recent replies${projectName ? " in this project" : ""}</h3>
<div class="sub" style="margin:-2px 0 6px">What Kompactor shortened in each of Claude's replies</div>
${turns ? `<ul>${turns}</ul>` : ""}
${quiet ? `<div class="sub">${quiet} ${quiet === 1 ? "reply" : "replies"} had nothing to shorten</div>` : ""}` : ""}
${top ? `<h3>Biggest wins</h3><ul>${top}</ul>` : ""}
<div class="btns"><button data-cmd="dashboard">Open dashboard</button><button class="secondary" data-cmd="level">Change level</button>${action}</div>
${summary && summary.pricing ? `<div class="note">${esc(pricingNote(summary.pricing))}</div>` : ""}
<script nonce="${nonce}">const vs=acquireVsCodeApi();document.querySelectorAll("[data-cmd]").forEach((b)=>b.addEventListener("click",()=>vs.postMessage({cmd:b.dataset.cmd})));</script>
</body></html>`;
}

function renderView() {
  if (view) view.webview.html = viewHtml(view.webview);
}

const viewProvider = {
  resolveWebviewView(v) {
    view = v;
    v.webview.options = { enableScripts: true };
    v.webview.onDidReceiveMessage((m) => {
      const after = () => refreshSummary();
      if (m.cmd === "dashboard") openDashboard();
      else if (m.cmd === "level") choosePreset().then(after);
      else if (m.cmd === "enable") enable(false).then(after);
      else if (m.cmd === "start") runKompactor(["start", "--no-browser"]).then(after);
      else if (m.cmd === "stop") runKompactor(["stop"]).then(after);
    });
    v.onDidChangeVisibility(() => v.visible && refreshSummary());
    v.onDidDispose(() => (view = null));
    renderView();
    refreshSummary();
  },
};

// ---------------------------------------------------------------------------
// Quality level

async function choosePreset() {
  const r = await runKompactor(["presets", "--json"]);
  let data;
  try { data = JSON.parse(r.stdout); } catch (e) {
    return vscode.window.showErrorMessage("Kompactor: " + (r.stderr || "couldn't read presets"));
  }
  const items = Object.entries(data.presets).map(([n, p]) => ({
    label: `${Number(n) === data.current ? "$(check) " : "      "}${n} · ${p.name}`,
    description: `≈${data.savings[n]}% fewer tokens on samples`,
    detail: p.blurb,
    n,
  }));
  const pick = await vscode.window.showQuickPick(items, {
    title: "Kompactor: quality vs tokens", placeHolder: "Left = more quality, right = more savings",
  });
  if (!pick) return;
  const res = await runKompactor(["config", "preset", pick.n]);
  if (res.code === 0) vscode.window.setStatusBarMessage(`Kompactor: ${data.presets[pick.n].name} (applies to the next tool call)`, 5000);
  else vscode.window.showErrorMessage("Kompactor: " + res.stderr);
  if (panel) panel.webview.postMessage({ type: "reload" });
}

// ---------------------------------------------------------------------------
// Dashboard

function ping(url) {
  return new Promise((resolve) => {
    const req = http.get(url + "api/ping", { timeout: 800 }, (res) => {
      let b = "";
      res.on("data", (d) => (b += d));
      res.on("end", () => resolve(res.statusCode === 200 && b.includes("kompactor")));
    });
    req.on("error", () => resolve(false));
    req.on("timeout", () => { req.destroy(); resolve(false); });
  });
}

async function ensureServer() {
  if (dashboardUrl && (await ping(dashboardUrl))) return dashboardUrl;
  const py = findPython();
  if (!py) throw new Error("Python 3.9+ not found. Set kompactor.pythonPath.");
  return new Promise((resolve, reject) => {
    server = cp.spawn(py[0], [...py.slice(1), launcher(), "ui", "--no-browser", "--port", "7420"], { env: process.env });
    let out = "";
    const timer = setTimeout(() => reject(new Error("dashboard didn't start: " + out)), 8000);
    server.stdout.on("data", (d) => {
      out += d;
      const m = out.match(/http:\/\/127\.0\.0\.1:\d+\//);
      if (m) { clearTimeout(timer); dashboardUrl = m[0]; resolve(dashboardUrl); }
    });
    server.stderr.on("data", (d) => (out += d));
    server.on("exit", () => { server = null; dashboardUrl = null; });
  });
}

async function openDashboard() {
  let url;
  try { url = await ensureServer(); } catch (e) { return vscode.window.showErrorMessage("Kompactor: " + e.message); }
  const ext = await vscode.env.asExternalUri(vscode.Uri.parse(url));
  if (panel) { panel.reveal(); return; }
  panel = vscode.window.createWebviewPanel("kompactor", "Kompactor", vscode.ViewColumn.Active,
    { enableScripts: true, retainContextWhenHidden: true });
  const origin = `${ext.scheme}://${ext.authority}`;
  panel.webview.html = `<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; frame-src ${origin} http://127.0.0.1:* http://localhost:*; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
<style>html,body{margin:0;padding:0;height:100%;overflow:hidden;background:transparent}iframe{border:0;width:100%;height:100vh}</style></head>
<body><iframe id="f" src="${ext.toString()}"></iframe>
<script>window.addEventListener("message",(e)=>{if(e.data&&e.data.type==="reload"){const f=document.getElementById("f");f.src=f.src;}});</script>
</body></html>`;
  panel.onDidDispose(() => (panel = null));
}

async function openInBrowser() {
  try { vscode.env.openExternal(vscode.Uri.parse(await ensureServer())); } catch (e) { vscode.window.showErrorMessage("Kompactor: " + e.message); }
}

// ---------------------------------------------------------------------------

function activate(context) {
  ctx = context;
  status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  status.command = "kompactor.menu";
  context.subscriptions.push(status,
    vscode.commands.registerCommand("kompactor.menu", menu),
    vscode.commands.registerCommand("kompactor.openDashboard", openDashboard),
    vscode.commands.registerCommand("kompactor.openInBrowser", openInBrowser),
    vscode.commands.registerCommand("kompactor.choosePreset", choosePreset),
    vscode.commands.registerCommand("kompactor.enable", () => enable(false)),
    vscode.commands.registerCommand("kompactor.disable", disable),
    vscode.commands.registerCommand("kompactor.showLastTurn", showLastTurn),
    vscode.commands.registerCommand("kompactor.refresh", refreshSummary),
    vscode.window.registerWebviewViewProvider("kompactor.savings", viewProvider),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("kompactor.pythonPath")) pythonCmd = null;
      if (e.affectsConfiguration("kompactor")) refreshSummary();
    }));

  fs.mkdirSync(kompactorHome(), { recursive: true });
  const live = readLive();
  lastTs = (live && live.ts) || 0;
  renderStatus(live);
  fs.watchFile(livePath(), { interval: 1000 }, onLiveChange);
  const timer = setInterval(() => view && view.visible && refreshSummary(), 60000);
  context.subscriptions.push({ dispose: () => { fs.unwatchFile(livePath(), onLiveChange); clearInterval(timer); } });
  refreshSummary();
  firstRun();
}

function deactivate() {
  if (server) server.kill();
}

module.exports = { activate, deactivate };
