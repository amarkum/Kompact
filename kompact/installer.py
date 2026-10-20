"""Wire Kompact into Claude Code (CLI and VS Code extension share ~/.claude/settings.json)."""

import glob
import json
import os
import shutil
import sys
from pathlib import Path

HOOKS = [  # (event, matcher, handler)
    ("PostToolUse", "Bash", "post-bash"),
    ("PostToolUse", "Edit|Write|NotebookEdit", "post-edit"),
    ("PostToolUse", "Grep|Glob|Read", "post-explore"),
    ("PreToolUse", "Read", "pre-read"),
    ("PreCompact", None, "pre-compact"),
    ("SessionStart", None, "session-start"),
    ("SubagentStart", None, "subagent-start"),
    ("Stop", None, "stop"),
]
EVENTS = sorted({e for e, _, _ in HOOKS})
MARK = "kompact"


def settings_path(scope: str = "user", project: str = "") -> Path:
    if scope == "project":
        return Path(project or os.getcwd()) / ".claude" / "settings.json"
    return Path.home() / ".claude" / "settings.json"


def launcher() -> str:
    """Command prefix that runs this copy of Kompact."""
    script = Path(__file__).with_name("_launch.py")
    py = sys.executable or shutil.which("python3") or "python3"
    return f'"{py}" "{script}"'


def shim_dir() -> Path:
    return Path.home() / ".kompact" / "bin"


def write_shim() -> Path:
    """A stable `~/.kompact/bin/kompact` that Claude's Bash tool can always call,
    however Kompact was installed (pip, clone, VS Code bundle, plugin)."""
    d = shim_dir()
    d.mkdir(parents=True, exist_ok=True)
    py = sys.executable or "python3"
    script = Path(__file__).with_name("_launch.py")
    sh = d / "kompact"
    sh.write_text(f'#!/bin/sh\nexec "{py}" "{script}" "$@"\n')
    sh.chmod(0o755)
    (d / "kompact.cmd").write_text(f'@"{py}" "{script}" %*\r\n')
    if os.name != "nt":
        prefix = d / "kompact-shell"
        prefix.write_text(SHELL_PREFIX.format(py=py, script=script))
        prefix.chmod(0o755)
    return sh


PREFIX_ENV = "CLAUDE_CODE_SHELL_PREFIX"
# Claude Code runs every Bash command as `kompact-shell '<command>'`. Only commands that look like
# tests, builds, linters or installs start Python; the rest (and everything, if Kompact is gone)
# run untouched. Keep this POSIX sh: it sits in front of every command Claude runs.
SHELL_PREFIX = """#!/bin/sh
# Kompact shell prefix (Claude Code setting {env}). Compacts test, build and lint
# output even when the command fails, keeping its exit code. Remove: kompact uninstall
case "$1" in *snapshot-zsh-*) s=zsh ;; *) s=bash ;; esac
command -v "$s" >/dev/null 2>&1 || s=sh
c=${{1#* eval }}
if [ -z "$KOMPACT_RAW" ] && [ -x "{py}" ] && [ -f "{script}" ]; then
  case "$c" in
    *test*|*build*|*lint*|*check*|*tsc*|*make*|*cargo*|*mvn*|*gradle*|*install*|*jest*|*mocha*|*mypy*|*ruff*|\\
    *pyright*|*flake8*|*vet*|*npm*|*pnpm*|*yarn*|*bun*|*uv\\ *|*pip*|*poetry*|*docker*|*golangci*|*tox*|*nox*)
      exec "{py}" "{script}" shell "$s" "$1" ;;
  esac
fi
exec "$s" -c "$1"
""".replace("{env}", PREFIX_ENV)


def prefix_path() -> Path:
    return shim_dir() / "kompact-shell"


def prefix_active() -> bool:
    """True inside a Claude Code session whose Bash commands run through Kompact's shell prefix."""
    cur = os.environ.get(PREFIX_ENV, "")
    return "kompact-shell" in cur and os.path.exists(cur)


def cli_name() -> str:
    """How Claude should invoke Kompact from its Bash tool."""
    if shutil.which("kompact"):
        return "kompact"
    if (shim_dir() / "kompact").exists():
        return "~/.kompact/bin/kompact"
    return launcher()


def _read(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def _ours(entry) -> bool:
    return MARK in json.dumps(entry)


def _prefix_state(settings: dict) -> str:
    cur = (settings.get("env") or {}).get(PREFIX_ENV, "")
    if not cur:
        return "none"
    if "kompact-shell" not in cur:
        return "other"
    return "kompact" if os.path.exists(cur) else "missing"


def plugin_enabled(settings: dict) -> bool:
    return any(k.startswith("kompact@") and v for k, v in (settings.get("enabledPlugins") or {}).items())


def status(project: str = "") -> dict:
    user = _read(settings_path("user"))
    hooks = user.get("hooks", {})
    installed = {f"{ev}:{h}": any(f"hook {h}" in json.dumps(e) for e in hooks.get(ev, [])) for ev, _, h in HOOKS}
    sl = (user.get("statusLine") or {}).get("command", "")
    home = Path.home()
    vscode = sorted(glob.glob(str(home / ".vscode*" / "extensions" / "anthropic.claude-code-*")))
    cursor = sorted(glob.glob(str(home / ".cursor" / "extensions" / "anthropic.claude-code-*")))
    return {
        "claude_cli": shutil.which("claude") or "",
        "vscode_extension": os.path.basename(vscode[-1]) if vscode else "",
        "cursor_extension": os.path.basename(cursor[-1]) if cursor else "",
        "settings_file": str(settings_path("user")),
        "hooks": installed,
        "hooks_installed": all(installed.values()),
        "plugin_enabled": plugin_enabled(user),
        "statusline": "kompact" if MARK in sl else ("other" if sl else "none"),
        "shell_prefix": _prefix_state(user),
        "launcher": launcher(),
    }


SKILL = """---
name: kompact
description: Kompact token saver and code graph. Use when the user says /kompact (status, a level name, review, audit, debt, graph), asks about token savings, or when you need to find code by topic, see who uses something, or check what a change affects.
---

Run these with Bash and report briefly. Kompact token saver.

Levels: `{cmd} presets`; change with `{cmd} config preset <N>` (1 Max quality, 2 Quality, 3 Balanced, 4 Savings, 5 Max savings; map words like "balanced" or "more savings").
Savings: `{cmd} gain`. Dashboard: start `{cmd} ui --no-browser` in the background and give the user the URL.

Code graph (local, instant):
- `{cmd} graph query "words"` find code by topic; `{cmd} graph explain Name` one symbol, its users and tests
- `{cmd} graph callers Name` · `{cmd} graph impact <file|Name>` what a change affects and which tests to run
- `{cmd} graph report` overview · `{cmd} symbol Name` print a definition

/kompact review: run `git diff HEAD`, then list concrete cuts, one line each (file:line, what to remove, why): code that duplicates an existing helper (check with graph query), options or abstractions nobody asked for, dead branches. Never cut validation, error handling, security or accessibility.
/kompact audit: run `{cmd} graph unused` and `{cmd} graph report`; rank removals (likely dead first) with risks. Don't edit unless asked.
/kompact debt: run `{cmd} debt` and summarize by severity.

Compacted output in full: `{cmd} show <id>`; search earlier outputs: `{cmd} search "text"`.
"""


def skill_path(scope: str = "user", project: str = "") -> Path:
    base = Path(project or os.getcwd()) if scope == "project" else Path.home()
    return base / ".claude" / "skills" / "kompact" / "SKILL.md"


def install(scope: str = "user", project: str = "", statusline: bool = True, uninstall: bool = False,
            shell_prefix: bool = True) -> Path:
    """Add (or remove) Kompact's hooks, status line and /kompact skill.

    When the Kompact plugin is enabled it already provides the hooks and the
    skill, so only the status line (which plugins can't set) is managed."""
    target = settings_path(scope, project)
    settings = _read(target)
    via_plugin = plugin_enabled(settings) and not uninstall
    cmd = launcher()
    if not uninstall:
        write_shim()
    hooks_cfg = settings.setdefault("hooks", {})
    for event in EVENTS:
        entries = [e for e in hooks_cfg.get(event, []) if not _ours(e)]
        if not uninstall and not via_plugin:
            for ev, matcher, handler in HOOKS:
                if ev != event:
                    continue
                entry = {"hooks": [{"type": "command", "command": f"{cmd} hook {handler}", "timeout": 15}]}
                entries.append({"matcher": matcher, **entry} if matcher else entry)
        if entries:
            hooks_cfg[event] = entries
        else:
            hooks_cfg.pop(event, None)
    if not hooks_cfg:
        settings.pop("hooks", None)
    sl = settings.get("statusLine") or {}
    if uninstall or not statusline:
        if MARK in sl.get("command", ""):
            settings.pop("statusLine", None)
    elif not sl or MARK in sl.get("command", ""):  # never replace someone else's status line
        settings["statusLine"] = {"type": "command", "command": f"{cmd} statusline", "padding": 0}
    env = settings.get("env") or {}
    cur = env.get(PREFIX_ENV, "")
    if uninstall or not shell_prefix:
        if "kompact-shell" in cur:
            env.pop(PREFIX_ENV)
    elif scope == "user" and os.name != "nt" and (not cur or "kompact-shell" in cur):
        # user scope only: a project's settings.json is often committed, and a teammate without Kompact
        # would get a shell prefix that doesn't exist. Never replace someone else's prefix.
        env[PREFIX_ENV] = str(prefix_path())
    if env:
        settings["env"] = env
    else:
        settings.pop("env", None)
    skill = skill_path(scope, project)
    if uninstall:
        if skill.exists() and "Kompact token saver" in skill.read_text():
            skill.unlink()
            try:
                skill.parent.rmdir()
            except OSError:
                pass
    elif not via_plugin and (not skill.exists() or "Kompact token saver" in skill.read_text()):  # never clobber
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(SKILL.format(cmd=cli_name()))
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        backup = target.with_suffix(".json.kompact-backup")
        if not backup.exists():
            shutil.copyfile(target, backup)
    target.write_text(json.dumps(settings, indent=2) + "\n")
    return target


# ---------------------------------------------------------------------------
# self-test: run every installed hook command exactly as Claude Code would


def selftest() -> list:
    """Run each Kompact hook from settings.json with a realistic event in an isolated
    KOMPACT_HOME. Returns [{hook, ok, ms, detail}]."""
    import subprocess
    import tempfile
    import time as _time
    settings = _read(settings_path("user"))
    hooks_cfg = settings.get("hooks", {})
    tmp = tempfile.mkdtemp(prefix="kompact-selftest-")
    big = Path(tmp, "big_module.py")
    big.write_text("".join(f"def handler_{i}(request):\n" + "    value = request * 2\n" * 6 + "    return value\n\n"
                           for i in range(80)))
    log = "".join(f"commit {i:040x}\nAuthor: Dev <d@x.io>\nDate:   Mon Oct 5 12:00:00 2026 +0000\n\n    change {i}\n\n"
                  for i in range(40))
    events = {
        "post-bash": {"tool_name": "Bash", "tool_input": {"command": "git log -n 40"},
                      "tool_response": {"stdout": log, "stderr": "", "interrupted": False, "isImage": False}},
        "pre-read": {"tool_name": "Read", "tool_input": {"file_path": str(big)}},
        "session-start": {"source": "startup"},
        "subagent-start": {"agent_type": "general-purpose"},
        "stop": {"stop_hook_active": False},
        "pre-compact": {"trigger": "manual"},
        "post-edit": {"tool_name": "Edit", "tool_input": {"file_path": str(big)}},
        "post-explore": {"tool_name": "Grep", "tool_input": {"pattern": "handler"}},
    }
    checks = {
        "post-bash": lambda o: "updatedToolOutput" in o.get("hookSpecificOutput", {}),
        "pre-read": lambda o: o.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
        "session-start": lambda o: "additionalContext" in o.get("hookSpecificOutput", {}) or o == {},
        "subagent-start": lambda o: "additionalContext" in o.get("hookSpecificOutput", {}) or o == {},
    }
    results = []
    plugin = plugin_enabled(settings)
    for event, matcher, handler in HOOKS:
        cmd = None
        for entry in hooks_cfg.get(event, []):
            for h in entry.get("hooks", []):
                if f"hook {handler}" in h.get("command", "") and MARK in h.get("command", ""):
                    cmd = h["command"]
        if cmd is None:
            if not plugin:
                results.append({"hook": f"{event} {handler}", "ok": False, "ms": 0, "detail": "not installed"})
                continue
            cmd = f"{launcher()} hook {handler}"  # plugin hooks: exercise the same code path
        ev = {"session_id": "kompact-selftest", "cwd": tmp, "hook_event_name": event, **events[handler]}
        env = dict(os.environ, KOMPACT_HOME=tmp)
        t0 = _time.time()
        try:
            p = subprocess.run(cmd, shell=True, input=json.dumps(ev), capture_output=True, text=True, timeout=20,
                               env=env)
            ms = int((_time.time() - t0) * 1000)
            out = json.loads(p.stdout) if p.stdout.strip() else {}
            ok = p.returncode == 0 and checks.get(handler, lambda o: True)(out)
            detail = "ok" if ok else (p.stderr.strip()[-200:] or f"unexpected output: {p.stdout[:160]}")
            errlog = Path(tmp, "hook-errors.log")
            if errlog.exists():
                ok, detail = False, errlog.read_text()[-200:]
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            ms, ok, detail = int((_time.time() - t0) * 1000), False, repr(e)[:200]
        results.append({"hook": f"{event} {handler}", "ok": ok, "ms": ms, "detail": detail})
    prefix = (settings.get("env") or {}).get(PREFIX_ENV, "")
    if "kompact-shell" in prefix:
        results.append(_check_prefix(prefix, tmp))
    return results


def _check_prefix(prefix: str, tmp: str) -> dict:
    """Run the shell prefix the way Claude Code does, on a failing test run with 300 passing lines."""
    import shlex
    import subprocess
    import time as _time
    fake = Path(tmp, "pytest")
    fake.write_text("#!/bin/sh\ni=0\nwhile [ $i -lt 300 ]; do echo \"tests/test_x.py::test_$i PASSED\"; i=$((i+1)); "
                    "done\necho 'FAILED tests/test_x.py::test_boom - AssertionError'\necho '1 failed, 300 passed'\n"
                    "exit 1\n")
    fake.chmod(0o755)
    full = f"true && eval {shlex.quote(f'cd {shlex.quote(tmp)} && ./pytest -q')} < /dev/null"
    t0 = _time.time()
    try:
        p = subprocess.run([prefix, full], capture_output=True, text=True, timeout=30,
                           env=dict(os.environ, KOMPACT_HOME=tmp))
        ok = p.returncode == 1 and "test_boom" in p.stdout and "test_7 PASSED" not in p.stdout and "[kompact:" in p.stdout
        detail = "ok" if ok else f"exit {p.returncode}: {(p.stdout + p.stderr)[-160:]}"
    except (OSError, subprocess.TimeoutExpired) as e:
        ok, detail = False, repr(e)[:200]
    return {"hook": "Shell prefix (failing commands)", "ok": ok, "ms": int((_time.time() - t0) * 1000), "detail": detail}
