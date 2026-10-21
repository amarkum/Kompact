"""Wire Kompactor into Claude Code (CLI and VS Code extension share ~/.claude/settings.json)."""

import glob
import json
import os
import re
import shlex
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
# Settings entries written by this tool, including those from its earlier name (Kompact). The patterns are
# precise so an unrelated tool called `kompact` (there is one on PyPI) never has its settings touched.
OURS = re.compile(r"kompactor|[\\/]+kompact[\\/]+_launch\.py|[\\/]+\.kompact[\\/]+bin[\\/]+kompact\b")
PREFIX_OURS = re.compile(r"kompactor-shell|[\\/]+\.kompact[\\/]+bin[\\/]+kompact-shell")


def settings_path(scope: str = "user", project: str = "") -> Path:
    if scope == "project":
        return Path(project or os.getcwd()) / ".claude" / "settings.json"
    return Path.home() / ".claude" / "settings.json"


def launcher() -> str:
    """Command prefix that runs this copy of Kompactor."""
    script = Path(__file__).with_name("_launch.py")
    py = sys.executable or shutil.which("python3") or "python3"
    return f'"{py}" "{script}"'


def shim_dir() -> Path:
    return Path.home() / ".kompactor" / "bin"


def write_shim(only_if_changed: bool = False) -> Path:
    """A stable `~/.kompactor/bin/kompactor` that Claude's Bash tool can always call,
    however Kompactor was installed (pip, clone, VS Code bundle, plugin), plus the shell prefix
    script. With only_if_changed, files that already point at this copy are left alone."""
    d = shim_dir()
    d.mkdir(parents=True, exist_ok=True)
    py = sys.executable or "python3"
    script = Path(__file__).with_name("_launch.py")
    files = {"kompactor": f'#!/bin/sh\nexec {shlex.quote(py)} {shlex.quote(str(script))} "$@"\n',
             "kompactor.cmd": f'@"{py}" "{script}" %*\r\n'}
    if os.name != "nt":
        files["kompactor-shell"] = SHELL_PREFIX.format(py=shlex.quote(py), script=shlex.quote(str(script)))
    for name, text in files.items():
        f = d / name
        if only_if_changed and f.exists() and f.read_text() == text:
            continue
        f.write_text(text)
        if not name.endswith(".cmd"):
            f.chmod(0o755)
    return d / "kompactor"

PREFIX_ENV = "CLAUDE_CODE_SHELL_PREFIX"
# Claude Code runs every Bash command as `kompactor-shell '<command>'`. Only commands that look like
# tests, builds, linters or installs start Python; the rest (and everything, if Kompactor is gone)
# run untouched. Keep this POSIX sh: it sits in front of every command Claude runs.
SHELL_PREFIX = """#!/bin/sh
# Kompactor shell prefix (Claude Code setting {env}). Compacts test, build and lint
# output even when the command fails, keeping its exit code. Remove: kompactor uninstall
case "$1" in *snapshot-zsh-*) s=zsh ;; *) s=bash ;; esac
command -v "$s" >/dev/null 2>&1 || s=sh
c=${{1#* eval }}
if [ -z "$KOMPACTOR_RAW" ] && [ -x {py} ] && [ -f {script} ]; then
  case "$c" in
    *test*|*build*|*lint*|*check*|*tsc*|*make*|*cargo*|*mvn*|*gradle*|*install*|*jest*|*mocha*|*mypy*|*ruff*|\\
    *pyright*|*flake8*|*vet*|*npm*|*pnpm*|*yarn*|*bun*|*uv\\ *|*pip*|*poetry*|*docker*|*golangci*|*tox*|*nox*)
      exec {py} {script} shell "$s" "$1" ;;
  esac
fi
exec "$s" -c "$1"
""".replace("{env}", PREFIX_ENV)


def prefix_path() -> Path:
    return shim_dir() / "kompactor-shell"


def prefix_active() -> bool:
    """True inside a Claude Code session whose Bash commands run through Kompactor's shell prefix."""
    cur = os.environ.get("CLAUDE_CODE_SHELL_PREFIX", "")
    return bool(PREFIX_OURS.search(cur)) and os.path.exists(cur)


def cli_name() -> str:
    """How Claude should invoke Kompactor from its Bash tool."""
    if shutil.which("kompactor"):
        return "kompactor"
    if (shim_dir() / "kompactor").exists():
        return "~/.kompactor/bin/kompactor"
    return launcher()


DEFAULT_REPO = "https://github.com/amarkum/kompactor"


def parse_source(url: str) -> dict:
    """{"repo", "clone", "marketplace", "dir"} for a git remote URL, or {} if it isn't one."""
    url = re.sub(r"^(https?://)[^/@\s]+@", r"\1", (url or "").strip())  # never show tokens (ssh keeps git@)
    m = re.match(r"^(?:[a-z+]+://)?(?:[\w.-]+@)?([\w.-]+)(?::\d+)?[/:](.+?)(?:\.git)?/?$", url)
    if not m:
        return {}
    host, parts = m.group(1), [x for x in m.group(2).split("/") if x]
    if len(parts) < 2:
        return {}
    repo = "/".join(parts[-2:])
    if host == "github.com":
        return {"repo": repo, "clone": f"https://github.com/{repo}.git", "marketplace": repo, "dir": parts[-1]}
    return {"repo": repo, "clone": url, "marketplace": url, "dir": parts[-1]}


def source(repo=None) -> dict:
    """The repo the dashboard's setup instructions name: Kompactor's public repo, or a team's fork set
    with KOMPACTOR_REPO (owner/repo or a git URL). Nothing is read from git or install records."""
    url = (os.environ.get("KOMPACTOR_REPO", "") if repo is None else repo).strip() or DEFAULT_REPO
    if re.fullmatch(r"[\w.-]+/[\w.-]+", url):
        url = f"https://github.com/{url}"
    return parse_source(url)


def _read(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def _ours(entry) -> bool:
    return bool(OURS.search(json.dumps(entry)))


def _prefix_state(settings: dict) -> str:
    cur = (settings.get("env") or {}).get(PREFIX_ENV, "")
    if not cur:
        return "none"
    if not PREFIX_OURS.search(cur):
        return "other"
    return "kompactor" if os.path.exists(cur) else "missing"


def plugin_enabled(settings: dict) -> bool:
    return any(k in ("stackcone@kompactor", "kompactor@claude-plugins-official") and v for k, v in (settings.get("enabledPlugins") or {}).items())


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
        "statusline": "kompactor" if OURS.search(sl) else ("other" if sl else "none"),
        "shell_prefix": _prefix_state(user),
        "launcher": launcher(),
        "source": source(),
    }


# The plugin's skills/kompactor/SKILL.md is this template rendered with these values: plugins no longer ship a bin/,
# so it calls the launcher that the session-start hook writes.
PLUGIN_SKILL = {"cmd": "~/.kompactor/bin/kompactor",
                "note": " `~/.kompactor/bin/kompactor` is created at session start; if it's missing, use"
                        " `python3 \"${CLAUDE_PLUGIN_ROOT}/kompactor/_launch.py\"` instead."}

SKILL = """---
name: kompactor
description: Kompactor token saver and code graph. Use when the user says /kompactor (setup, start, stop, uninstall, status, a level name, review, audit, debt, graph), asks about token savings, or when you need to find code by topic, see who uses something, or check what a change affects.
---

Run these with Bash and report briefly. Kompactor token saver.{note}

/kompactor status (or just /kompactor): run `{cmd} status` and summarise it in a few lines.
/kompactor setup: run `{cmd} setup --no-ui` (adds the status line and the shell prefix that compacts failing commands, which a plugin can't set itself), report what it printed, and tell the user to restart Claude Code.
Levels: `{cmd} presets`; change with `{cmd} config preset <N>` (1 Max quality, 2 Quality, 3 Balanced, 4 Savings, 5 Max savings; map words like "balanced" or "more savings").
Savings: `{cmd} gain`. Dashboard: run `{cmd} start --no-browser` (returns at once, picks a free port) and give the user the URL it prints.
/kompactor stop: `{cmd} stop` (pauses compaction, closes the dashboard). /kompactor start: `{cmd} start --no-browser`. /kompactor uninstall: `{cmd} uninstall`, then relay any extra command it prints.

Code graph (local, instant):
- `{cmd} graph query "words"` find code by topic; `{cmd} graph explain Name` one symbol, its users and tests
- `{cmd} graph callers Name` · `{cmd} graph impact <file|Name>` what a change affects and which tests to run
- `{cmd} graph report` overview · `{cmd} symbol Name` print a definition

/kompactor review: run `git diff HEAD`, then list concrete cuts, one line each (file:line, what to remove, why): code that duplicates an existing helper (check with graph query), options or abstractions nobody asked for, dead branches. Never cut validation, error handling, security or accessibility.
/kompactor audit: run `{cmd} graph unused` and `{cmd} graph report`; rank removals (likely dead first) with risks. Don't edit unless asked.
/kompactor debt: run `{cmd} debt` and summarize by severity.

Compacted output in full: `{cmd} show <id>`; search earlier outputs: `{cmd} search "text"`.
"""


def skill_path(scope: str = "user", project: str = "") -> Path:
    base = Path(project or os.getcwd()) if scope == "project" else Path.home()
    return base / ".claude" / "skills" / "kompactor" / "SKILL.md"


def install(scope: str = "user", project: str = "", statusline: bool = True, uninstall: bool = False,
            shell_prefix: bool = True) -> Path:
    """Add (or remove) Kompactor's hooks, status line and /kompactor skill.

    When the Kompactor plugin is enabled it already provides the hooks and the
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
        if OURS.search(sl.get("command", "")):
            settings.pop("statusLine", None)
    elif not sl or OURS.search(sl.get("command", "")):  # never replace someone else's status line
        settings["statusLine"] = {"type": "command", "command": f"{cmd} statusline", "padding": 0}
    env = settings.get("env") or {}
    cur = env.get(PREFIX_ENV, "")
    if uninstall or not shell_prefix:
        if PREFIX_OURS.search(cur):
            env.pop(PREFIX_ENV)
    elif scope == "user" and os.name != "nt" and (not cur or PREFIX_OURS.search(cur)):
        # user scope only: a project's settings.json is often committed, and a teammate without Kompactor
        # would get a shell prefix that doesn't exist. Never replace someone else's prefix.
        env[PREFIX_ENV] = str(prefix_path())
    if env:
        settings["env"] = env
    else:
        settings.pop("env", None)
    legacy = Path.home() / ".claude" / "skills" / "kompact" / "SKILL.md"  # the /kompact skill, before the rename
    if scope == "user" and legacy.exists() and "Kompact token saver" in legacy.read_text():
        legacy.unlink()
        try:
            legacy.parent.rmdir()
        except OSError:
            pass
    skill = skill_path(scope, project)
    if uninstall:
        if skill.exists() and "Kompactor token saver" in skill.read_text():
            skill.unlink()
            try:
                skill.parent.rmdir()
            except OSError:
                pass
    elif not via_plugin and (not skill.exists() or "Kompactor token saver" in skill.read_text()):  # never clobber
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(SKILL.format(cmd=cli_name(), note=""))
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        backup = target.with_suffix(".json.kompactor-backup")
        if not backup.exists():
            shutil.copyfile(target, backup)
    target.write_text(json.dumps(settings, indent=2) + "\n")
    return target


# ---------------------------------------------------------------------------
# self-test: run every installed hook command exactly as Claude Code would


def _selftest_env(tmp: str) -> dict:
    """Only what a hook needs to start: the self-test never hands hooks the rest of your environment."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""),
           "USERPROFILE": os.environ.get("USERPROFILE", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
           "TMPDIR": os.environ.get("TMPDIR", ""), "TEMP": os.environ.get("TEMP", ""),
           "TMP": os.environ.get("TMP", ""), "LANG": os.environ.get("LANG", "")}
    return {**{k: v for k, v in env.items() if v}, "KOMPACTOR_HOME": tmp}


def selftest() -> list:
    """Run each Kompactor hook from settings.json with a realistic event in an isolated
    KOMPACTOR_HOME. Returns [{hook, ok, ms, detail}]."""
    import subprocess
    import tempfile
    import time as _time
    settings = _read(settings_path("user"))
    hooks_cfg = settings.get("hooks", {})
    tmp = tempfile.mkdtemp(prefix="kompactor-selftest-")
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
                if f"hook {handler}" in h.get("command", "") and OURS.search(h.get("command", "")):
                    cmd = h["command"]
        if cmd is None:
            if not plugin:
                results.append({"hook": f"{event} {handler}", "ok": False, "ms": 0, "detail": "not installed"})
                continue
            cmd = f"{launcher()} hook {handler}"  # plugin hooks: exercise the same code path
        ev = {"session_id": "kompactor-selftest", "cwd": tmp, "hook_event_name": event, **events[handler]}
        env = _selftest_env(tmp)
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
    if PREFIX_OURS.search(prefix):
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
                           env=_selftest_env(tmp))
        ok = p.returncode == 1 and "test_boom" in p.stdout and "test_7 PASSED" not in p.stdout and "[kompactor:" in p.stdout
        detail = "ok" if ok else f"exit {p.returncode}: {(p.stdout + p.stderr)[-160:]}"
    except (OSError, subprocess.TimeoutExpired) as e:
        ok, detail = False, repr(e)[:200]
    return {"hook": "Shell prefix (failing commands)", "ok": ok, "ms": int((_time.time() - t0) * 1000), "detail": detail}
