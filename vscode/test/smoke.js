// Smoke test for extension.js against a mock `vscode` API.
//   node vscode/test/smoke.js
// Exercises: status bar from live.json, enabling hooks, per-turn message,
// preset picker, dashboard server + webview. Uses temp HOME / KOMPACT_HOME.

const assert = require("assert");
const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const Module = require("module");

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "kompact-vsc-"));
process.env.HOME = tmp;
process.env.USERPROFILE = tmp;
process.env.KOMPACT_HOME = path.join(tmp, ".kompact");
fs.mkdirSync(process.env.KOMPACT_HOME, { recursive: true });
const repo = path.resolve(__dirname, "..", "..");

const calls = { info: [], statusMsg: [], errors: [] };
let quickPickAnswer = null;
const commands = {};
const statusItem = { text: "", tooltip: "", shown: false, show() { this.shown = true; }, hide() { this.shown = false; }, dispose() {} };
let webviewHtml = "";

class MarkdownString { constructor(v) { this.value = v; this.isTrusted = false; } }
const vscodeMock = {
  StatusBarAlignment: { Left: 1, Right: 2 },
  ViewColumn: { Active: -1 },
  MarkdownString,
  Uri: { parse: (s) => { const u = new URL(s); return { scheme: u.protocol.replace(":", ""), authority: u.host, toString: () => s }; } },
  env: { asExternalUri: async (u) => u, openExternal: async () => true },
  window: {
    createStatusBarItem: () => statusItem,
    showInformationMessage: async (msg) => { calls.info.push(msg); return undefined; },
    showErrorMessage: async (msg) => { calls.errors.push(msg); },
    setStatusBarMessage: (msg) => { calls.statusMsg.push(msg); return { dispose() {} }; },
    showQuickPick: async (items) => (typeof quickPickAnswer === "function" ? quickPickAnswer(items) : undefined),
    createWebviewPanel: () => ({
      webview: { set html(v) { webviewHtml = v; }, get html() { return webviewHtml; }, postMessage() {} },
      reveal() {}, onDidDispose() {},
    }),
  },
  commands: { registerCommand: (id, fn) => { commands[id] = fn; return { dispose() {} }; } },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: "/work/shop" } }],
    getConfiguration: () => ({ get: (k) => ({ turnSummary: "statusBar", showStatusBar: true, pythonPath: "" }[k]) }),
    onDidChangeConfiguration: () => ({ dispose() {} }),
  },
};
const origResolve = Module._resolveFilename;
Module._resolveFilename = function (req, ...rest) { return req === "vscode" ? "vscode" : origResolve.call(this, req, ...rest); };
require.cache.vscode = { id: "vscode", filename: "vscode", loaded: true, exports: vscodeMock };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const writeLive = (obj) => fs.writeFileSync(path.join(process.env.KOMPACT_HOME, "live.json"), JSON.stringify(obj));
const get = (url) => new Promise((res, rej) => http.get(url, (r) => { let b = ""; r.on("data", (d) => (b += d)); r.on("end", () => res(b)); }).on("error", rej));

(async () => {
  const ext = require(path.join(repo, "vscode", "extension.js"));
  const state = {};
  const ctx = { extensionPath: path.join(repo, "vscode"), subscriptions: [],
    globalState: { get: (k) => state[k], update: async (k, v) => { state[k] = v; } } };

  writeLive({ ts: 1, session: "s1", project: "/work/shop", preset_name: "Balanced",
    turn: { saved: 1200, raw: 2000, kept: 800 }, session_totals: { saved: 5000, context: 30000, in_context_saved: 5000 },
    message: "⚡ Kompact: −1.2k tokens this turn" });
  ext.activate(ctx);
  await sleep(100);
  assert.match(statusItem.text, /\$\(zap\) −5\.0k · ctx −14%/, "status bar shows session savings");
  assert.ok(calls.info.some((m) => m.includes("Enable it?")), "first run offers to enable");
  for (const id of ["kompact.openDashboard", "kompact.choosePreset", "kompact.enable", "kompact.disable", "kompact.menu"])
    assert.ok(commands[id], `command ${id} registered`);

  // enable -> hooks in ~/.claude/settings.json pointing at this repo's launcher
  await commands["kompact.enable"]();
  const settings = JSON.parse(fs.readFileSync(path.join(tmp, ".claude", "settings.json"), "utf8"));
  for (const ev of ["PostToolUse", "PreToolUse", "PreCompact", "SessionStart", "Stop"])
    assert.ok(JSON.stringify(settings.hooks[ev]).includes("_launch.py"), `${ev} hook installed`);

  // a new turn is announced in the status bar
  writeLive({ ts: 2, session: "s1", project: "/work/shop/api", preset_name: "Balanced",
    turn: { saved: 3000, raw: 4000, kept: 1000 }, session_totals: { saved: 8000, context: 32000, in_context_saved: 8000 },
    message: "⚡ Kompact: −3.0k tokens this turn (4.0k → 1.0k, −75%)" });
  await sleep(2500);
  assert.ok(calls.statusMsg.some((m) => m.includes("−3.0k tokens this turn")), "turn summary flashed");
  assert.match(statusItem.text, /−8\.0k/);

  // turns from other windows' projects are not announced here
  const before = calls.statusMsg.length;
  writeLive({ ts: 3, session: "s2", project: "/elsewhere/repo", turn: { saved: 999, raw: 2000, kept: 1001 },
    session_totals: { saved: 999 }, message: "⚡ Kompact: other window" });
  await sleep(2500);
  assert.strictEqual(calls.statusMsg.length, before, "other project's turn ignored");

  // preset picker writes config.json
  quickPickAnswer = (items) => items.find((i) => i.n === "4");
  await commands["kompact.choosePreset"]();
  const conf = JSON.parse(fs.readFileSync(path.join(process.env.KOMPACT_HOME, "config.json"), "utf8"));
  assert.strictEqual(conf.preset, 4, "preset saved");

  // dashboard: server starts, webview iframes it
  await commands["kompact.openDashboard"]();
  const m = webviewHtml.match(/src="(http:\/\/127\.0\.0\.1:\d+\/)"/);
  assert.ok(m, "webview iframes the dashboard");
  assert.ok((await get(m[1] + "api/ping")).includes("kompact"), "dashboard server answers");
  assert.ok((await get(m[1])).includes("Quality vs tokens"), "dashboard page served");

  ext.deactivate();
  for (const s of ctx.subscriptions) s.dispose && s.dispose();
  assert.deepStrictEqual(calls.errors, [], "no error messages");
  console.log("vscode extension smoke test: OK");
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
