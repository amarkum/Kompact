"""User config: ~/.kompact/config.json, overridable by KOMPACT_* env vars."""

import json
import os

from . import store

DEFAULTS = {
    "style": "lite",           # output-style rules injected at session start: off | lite | full
    "bash": True,              # compress Bash tool output
    "bash_min_tokens": 150,    # leave small outputs untouched
    "bash_max_lines": 200,     # head/tail cap after filtering
    "read_outline": True,      # first full Read of a big source file returns its outline instead
    "read_outline_lines": 400,
    "read_dedupe": True,       # re-Read of an unchanged file is answered from memory once
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    path = store.home() / "config.json"
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text()))
        except (OSError, ValueError):
            pass
    for k, v in DEFAULTS.items():
        env = os.environ.get(f"KOMPACT_{k.upper()}")
        if env is None:
            continue
        if isinstance(v, bool):
            cfg[k] = env.lower() in ("1", "true", "yes", "on")
        elif isinstance(v, int):
            cfg[k] = int(env)
        else:
            cfg[k] = env
    return cfg


def save(key: str, value) -> None:
    path = store.home() / "config.json"
    cur = json.loads(path.read_text()) if path.exists() else {}
    if key in DEFAULTS and isinstance(DEFAULTS[key], bool):
        value = str(value).lower() in ("1", "true", "yes", "on")
    elif key in DEFAULTS and isinstance(DEFAULTS[key], int):
        value = int(value)
    cur[key] = value
    path.write_text(json.dumps(cur, indent=2))
