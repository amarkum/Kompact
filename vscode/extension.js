// Kompactor for VS Code: wires Kompactor's hooks into Claude Code (the VS Code
// extension and the CLI share ~/.claude/settings.json), shows per-turn savings
// in the status bar, and hosts the settings dashboard in a webview.
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

const kompactorHome = () => process.env.KOMPACTOR_HOME || path.join(os.homedir(), ".kompactor");
const livePath = () => path.join(kompactorHome(), "live.json");
const claudeSettings = () => path.join(os.homedir(), ".claude", "settings.json");
const cfg = () => vscode.workspace.getConfiguration("kompactor");

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
    const plugin = Object.entries(s.enabledPlugins || {}).some(([k, v]) => ["stackcone@kompactor", "kompactor@claude-plugins-official"].includes(k) && v);
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

function renderStatus(live) {
  if (!cfg().get("showStatusBar")) return status.hide();
  const tot = (live && live.session_totals) || {};
  const turn = (live && live.turn) || {};
  if (live && inThisWindow(live.project) && tot.saved > 0) {
    const ctxPct = tot.context && tot.in_context_saved > 0 ? Math.round(100 * tot.in_context_saved / (tot.context + tot.in_context_saved)) : 0;
    status.text = `$(fold) −${fmt(tot.saved)}` + (ctxPct ? ` · ctx −${ctxPct}%` : "");
    const md = new vscode.MarkdownString(
      `**Kompactor** · ${live.preset_name || ""}\n\n` +
      (turn.saved > 0 ? `Last turn: **−${fmt(turn.saved)} tokens** (${fmt(turn.raw)} › ${fmt(turn.kept)})\n\n` : "Last turn: nothing to trim\n\n") +
      `This session: −${fmt(tot.saved)} tokens` + (ctxPct ? `, context ≈${ctxPct}% smaller` : "") +
      `\n\n[Open dashboard](command:kompactor.openDashboard) · [Change level](command:kompactor.choosePreset)`);
    md.isTrusted = true;
    status.tooltip = md;
  } else {
    status.text = "$(fold) Kompactor";
    status.tooltip = "Kompactor: click for the dashboard or to change the quality vs tokens level";
  }
  status.show();
}

function onLiveChange() {
  const live = readLive();
  renderStatus(live);
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
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("kompactor.pythonPath")) pythonCmd = null;
      if (e.affectsConfiguration("kompactor")) renderStatus(readLive());
    }));

  fs.mkdirSync(kompactorHome(), { recursive: true });
  const live = readLive();
  lastTs = (live && live.ts) || 0;
  renderStatus(live);
  fs.watchFile(livePath(), { interval: 1000 }, onLiveChange);
  context.subscriptions.push({ dispose: () => fs.unwatchFile(livePath(), onLiveChange) });
  firstRun();
}

function deactivate() {
  if (server) server.kill();
}

module.exports = { activate, deactivate };
