"""Wire Kompact into Claude Code (CLI and VS Code extension share ~/.claude/settings.json)."""

import glob
import json
import os
import shutil
import sys
from pathlib import Path

HOOKS = {  # event -> (matcher, handler)
    "PostToolUse": ("Bash", "post-bash"),
    "PreToolUse": ("Read", "pre-read"),
    "PreCompact": (None, "pre-compact"),
    "SessionStart": (None, "session-start"),
    "Stop": (None, "stop"),
}
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
    return sh


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


def plugin_enabled(settings: dict) -> bool:
    return any(k.startswith("kompact@") and v for k, v in (settings.get("enabledPlugins") or {}).items())


def status(project: str = "") -> dict:
    user = _read(settings_path("user"))
    hooks = user.get("hooks", {})
    installed = {ev: any(_ours(e) for e in hooks.get(ev, [])) for ev in HOOKS}
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


def install(scope: str = "user", project: str = "", statusline: bool = True, uninstall: bool = False) -> Path:
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
    for event, (matcher, handler) in HOOKS.items():
        entries = [e for e in hooks_cfg.get(event, []) if not _ours(e)]
        if not uninstall and not via_plugin:
            entry = {"hooks": [{"type": "command", "command": f"{cmd} hook {handler}", "timeout": 15}]}
            if matcher:
                entry = {"matcher": matcher, **entry}
            entries.append(entry)
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
