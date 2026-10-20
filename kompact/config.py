"""Configuration: a quality-vs-tokens preset, optional per-knob overrides,
language profiles, and per-project overrides.

Stored in ~/.kompact/config.json and edited from the dashboard (`kompact ui`):

    {
      "preset": 3,
      "overrides": {"bash_max_lines": 250},
      "languages": {"mode": "auto", "selected": ["python", "go", "typescript", "react"]},
      "projects": {"/path/to/repo": {"preset": 4, "overrides": {}}}
    }
"""

import json
import os
from pathlib import Path

from . import store

PRESETS = {
    1: {"name": "Max quality", "blurb": "Only trims huge outputs and exact noise. Claude sees almost everything.",
        "bash": True, "bash_plain": False, "bash_min_tokens": 1500, "bash_max_lines": 600, "max_line_chars": 2000, "grep_per_file": 50, "test_hide_passing": False, "test_boilerplate": False,
        "trim_stack_frames": False, "diff_context": -1, "git_log_compact": False, "read_outline": False,
        "read_outline_lines": 1500, "graph": True, "session_map_tokens": 0, "read_graph_context": False, "read_dedupe": True, "style": "off", "code_style": "normal", "subagent_rules": True, "never_compact": []},
    2: {"name": "Quality", "blurb": "Compacts noisy commands; big files are still read whole.",
        "bash": True, "bash_plain": False, "bash_min_tokens": 1000, "bash_max_lines": 400, "max_line_chars": 1000, "grep_per_file": 25, "test_hide_passing": True, "test_boilerplate": False,
        "trim_stack_frames": False, "diff_context": -1, "git_log_compact": True, "read_outline": True,
        "read_outline_lines": 800, "graph": True, "session_map_tokens": 0, "read_graph_context": True, "read_dedupe": True, "style": "lite", "code_style": "normal", "subagent_rules": True, "never_compact": []},
    3: {"name": "Balanced", "blurb": "Recommended. Outline-first reads, compact tool output, terse replies.",
        "bash": True, "bash_plain": False, "bash_min_tokens": 300, "bash_max_lines": 200, "max_line_chars": 500, "grep_per_file": 12, "test_hide_passing": True, "test_boilerplate": False,
        "trim_stack_frames": True, "diff_context": -1, "git_log_compact": True, "read_outline": True,
        "read_outline_lines": 400, "graph": True, "session_map_tokens": 500, "read_graph_context": True, "read_dedupe": True, "style": "lite", "code_style": "lean", "subagent_rules": True, "never_compact": []},
    4: {"name": "Savings", "blurb": "Tighter caps, trimmed diff context, smaller file threshold.",
        "bash": True, "bash_plain": False, "bash_min_tokens": 150, "bash_max_lines": 120, "max_line_chars": 300, "grep_per_file": 8, "test_hide_passing": True, "test_boilerplate": True,
        "trim_stack_frames": True, "diff_context": 3, "git_log_compact": True, "read_outline": True,
        "read_outline_lines": 250, "graph": True, "session_map_tokens": 700, "read_graph_context": True, "read_dedupe": True, "style": "full", "code_style": "lean", "subagent_rules": True, "never_compact": []},
    5: {"name": "Max savings", "blurb": "Most aggressive. Claude may need `kompact show` more often.",
        "bash": True, "bash_plain": False, "bash_min_tokens": 80, "bash_max_lines": 80, "max_line_chars": 200, "grep_per_file": 5, "test_hide_passing": True, "test_boilerplate": True,
        "trim_stack_frames": True, "diff_context": 1, "git_log_compact": True, "read_outline": True,
        "read_outline_lines": 150, "graph": True, "session_map_tokens": 900, "read_graph_context": True, "read_dedupe": True, "style": "ultra", "code_style": "lean", "subagent_rules": True, "never_compact": []},
}
KNOBS = [k for k in PRESETS[3] if k not in ("name", "blurb")]

# UI metadata for every knob: label, help, type and range.
KNOB_INFO = {
    "bash": ("Compact command output", "Shrink Bash/terminal output before Claude reads it.", "bool"),
    "bash_plain": ("Let Kompact trim command output", "Tells Claude to run commands without `| head`, `| tail` or "
                   "`| grep`: Kompact keeps every failure, so Claude needs fewer follow-up runs.", "bool"),
    "bash_min_tokens": ("Leave outputs smaller than", "Outputs under this many tokens are passed through untouched.",
                        "int", 0, 5000, 50),
    "bash_max_lines": ("Max lines kept per output", "Head and tail are kept; error lines from the middle are always kept.",
                       "int", 40, 1000, 10),
    "max_line_chars": ("Longest line kept", "Longer lines (minified code, giant JSON) are clipped with a '+N chars' note.",
                       "int", 120, 4000, 20),
    "grep_per_file": ("Search matches per file", "grep/rg matches shown per file before '+N more'.", "int", 1, 100, 1),
    "test_hide_passing": ("Hide passing tests", "Keep failures and the summary; drop the passing-test lines.", "bool"),
    "test_boilerplate": ("Drop test-runner headers", "Remove session banners, separators and timing lines.", "bool"),
    "trim_stack_frames": ("Trim library stack frames",
                          "Collapse site-packages / node_modules / Go runtime frames in tracebacks.", "bool"),
    "diff_context": ("Diff context lines", "Unchanged lines kept around each change in diffs (-1 = all).", "int", -1, 10, 1),
    "git_log_compact": ("One-line git log", "Turn verbose git log into 'sha date author: subject'.", "bool"),
    "read_outline": ("Outline-first file reads",
                     "First full read of a big file returns its structure; reading again returns the whole file.", "bool"),
    "read_outline_lines": ("Outline files longer than", "Line count from which a file is outlined first.",
                           "int", 50, 3000, 50),
    "graph": ("Code graph", "Index functions, classes, imports and calls so Claude can find code without reading "
              "whole files (`kompact graph query`).", "bool"),
    "session_map_tokens": ("Code map", "Token budget for a map of the most depended-on modules, given to Claude the "
                           "first time it searches or reads code in a session (0 = off). Sessions that only run "
                           "commands don't pay for it.", "int", 0, 3000, 100),
    "read_graph_context": ("Show usages in outlines", "Outlines also say which modules import the file and which "
                           "tests cover it.", "bool"),
    "read_dedupe": ("Skip unchanged re-reads", "Re-reading an unchanged file gets a short note (once).", "bool"),
    "style": ("Prose style", "How Claude writes: off, lite (answer first, no recap), full (short sentences, no "
              "narration), ultra (telegraphic). Code, commands and errors are never shortened.",
              "choice", ["off", "lite", "full", "ultra"]),
    "code_style": ("Code style", "How much code Claude writes: normal, lean (reuse first, smallest diff, check callers "
                   "and tests), strict (also proposes a smaller alternative before building).",
                   "choice", ["normal", "lean", "strict"]),
    "subagent_rules": ("Apply rules to subagents", "Subagents get the same prose and code rules.", "bool"),
    "never_compact": ("Never compact these commands", "Commands whose output is always passed through untouched, "
                      "comma separated (e.g. terraform plan, kubectl describe).", "list"),
}

GENERAL = {"turn_summary": True, "statusline": True, "retention_days": 30}

DEFAULT_FILE = {"preset": 3, "overrides": {}, "languages": {"mode": "auto", "selected": []}, "projects": {},
                "general": dict(GENERAL)}


def path() -> Path:
    return store.home() / "config.json"


def read_file() -> dict:
    data = json.loads(json.dumps(DEFAULT_FILE))
    p = path()
    if p.exists():
        try:
            raw = json.loads(p.read_text())
        except (OSError, ValueError):
            raw = {}
        if "preset" not in raw and any(k in raw for k in KNOBS):  # v0.1 flat format
            raw = {"overrides": {k: v for k, v in raw.items() if k in KNOBS}}
        for k, v in raw.items():
            if isinstance(v, dict) and isinstance(data.get(k), dict):
                data[k].update(v)
            else:
                data[k] = v
    return data


def write_file(data: dict) -> None:
    p = path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, p)


def project_root(cwd: str) -> str:
    """Nearest ancestor with a VCS or project marker; cwd itself otherwise."""
    if not cwd:
        return ""
    p = Path(cwd).resolve()
    for d in [p, *p.parents]:
        if any((d / m).exists() for m in (".git", "go.mod", "pyproject.toml", "package.json", ".hg")):
            return str(d)
    return str(p)


def coerce(key: str, value):
    info = KNOB_INFO.get(key)
    if not info:
        return value
    if info[2] == "bool":
        return value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "on")
    if info[2] == "int":
        return max(info[3], min(info[4], int(value)))
    if info[2] == "choice" and value not in info[3]:
        raise ValueError(f"{key} must be one of {info[3]}")
    if info[2] == "list":
        items = value if isinstance(value, list) else str(value).split(",")
        return [str(v).strip() for v in items if str(v).strip()][:50]
    return value


def load(cwd: str = "") -> dict:
    """Effective settings for a working directory: preset ⊕ overrides ⊕ project ⊕ env."""
    data = read_file()
    root = project_root(cwd) if cwd else ""
    proj = data["projects"].get(root, {}) if root else {}
    preset = int(proj.get("preset", data.get("preset", 3)))
    preset = preset if preset in PRESETS else 3
    cfg = {k: PRESETS[preset][k] for k in KNOBS}
    cfg.update({k: v for k, v in data.get("overrides", {}).items() if k in KNOBS})
    cfg.update({k: v for k, v in proj.get("overrides", {}).items() if k in KNOBS})
    for k in KNOBS:
        env = os.environ.get(f"KOMPACT_{k.upper()}")
        if env is not None:
            try:
                cfg[k] = coerce(k, env)
            except ValueError:
                pass
    if os.environ.get("KOMPACT_PRESET", "").isdigit() and int(os.environ["KOMPACT_PRESET"]) in PRESETS:
        preset = int(os.environ["KOMPACT_PRESET"])
        cfg.update({k: PRESETS[preset][k] for k in KNOBS})
    cfg["preset"] = preset
    cfg["project"] = root
    cfg.update({k: v for k, v in data.get("general", {}).items() if k in GENERAL})

    from . import langs
    lang_cfg = data.get("languages", {})
    if lang_cfg.get("mode") == "manual" and lang_cfg.get("selected"):
        cfg["languages"] = list(lang_cfg["selected"])
    else:
        cfg["languages"] = langs.detect(root) if root else []
    return cfg


def save(key: str, value) -> None:
    """CLI helper: `kompact config preset 4` or `kompact config bash_max_lines 150`."""
    data = read_file()
    if key == "preset":
        data["preset"] = int(value)
    elif key in KNOBS:
        data["overrides"][key] = coerce(key, value)
    elif key in GENERAL:
        data["general"][key] = int(value) if isinstance(GENERAL[key], int) and not isinstance(GENERAL[key], bool) \
            else coerce("bash", value)
    elif key == "languages":
        data["languages"] = ({"mode": "auto", "selected": []} if value == "auto"
                             else {"mode": "manual", "selected": [v.strip() for v in str(value).split(",") if v.strip()]})
    else:
        raise KeyError(key)
    write_file(data)
