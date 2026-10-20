"""Shell prefix: compact test, build and lint output even when the command fails.

Claude Code only lets hooks rewrite the output of commands that succeed. When a
command exits non-zero it skips PostToolUse, fires PostToolUseFailure (which can
add context but not replace anything) and cuts the output to its first and last
few thousand characters, which usually drops the failures at the end of a test
run. Claude Code's CLAUDE_CODE_SHELL_PREFIX setting runs every Bash command as
`<prefix> '<shell command>'`. Kompact's prefix (~/.kompact/bin/kompact-shell)
sends finite, noisy commands here: they run to completion, the output is
compacted, and the exit code is passed through unchanged. Permission rules
still see Claude's original command, because the prefix applies only when the
command runs.

Everything else, and any problem inside Kompact before the command starts,
runs the command untouched.
"""

import os
import shlex
import signal
import subprocess
import sys
from collections import deque

from . import config, filters, installer, store, tokens

HEAD_BYTES = 16 << 20  # keep at most 16 MB from the start and 8 MB from the end of the output
TAIL_BYTES = 8 << 20
SHOWN_LIMIT = 30000  # Claude Code saves longer successful outputs to a file and shows a 2 KB preview
PREVIEW_CHARS = 2048
ERROR_LIMIT = 10000  # failed commands: Claude Code keeps about this many characters


def user_command(full: str) -> str:
    """Claude's own command inside the string Claude Code hands the prefix:
    `source <snapshot> ... && eval '<command>' < /dev/null && pwd -P >| <cwd file>`."""
    i = full.find(" eval ")
    if i < 0:
        return ""
    try:
        lex = shlex.shlex(full[i + 6:], posix=True)
        lex.whitespace_split = True
        return lex.get_token() or ""
    except ValueError:
        return ""


def decide(full: str):
    """(command, config) when the command should run through Kompact, else (None, None)."""
    if os.environ.get("KOMPACT_RAW"):
        return None, None
    cmd = user_command(full)
    if not cmd or cmd.lstrip().startswith("KOMPACT_RAW=1") or not filters.wrappable(cmd):
        return None, None
    cfg = config.load(os.getcwd())
    if not cfg.get("bash") or not cfg.get("bash_wrap"):
        return None, None
    words = " ".join(filters.argv0(cmd))
    if any(words.startswith(c.strip()) for c in cfg.get("never_compact", []) if c.strip()):
        return None, None
    return cmd, cfg


def shown_tokens(text: str, code: int) -> int:
    """Roughly what Claude would have read without Kompact (the honest baseline for the ledger)."""
    if code != 0:
        if len(text) > ERROR_LIMIT:
            return tokens.count(text[:ERROR_LIMIT // 2]) + tokens.count(text[-ERROR_LIMIT // 2:])
        return tokens.count(text)
    if len(text) > int(os.environ.get("BASH_MAX_OUTPUT_LENGTH") or SHOWN_LIMIT):
        return tokens.count(text[:PREVIEW_CHARS]) + 60
    return tokens.count(text)


def compact(cmd: str, raw: str, code: int, cfg: dict, stopped: bool = False) -> str:
    raw_tokens = tokens.count(raw)
    if raw_tokens < cfg["bash_min_tokens"]:
        return raw
    sid = store.stash(cmd, raw)
    new = filters.compress(cmd, raw, code, stash_id=sid, opts=cfg)
    kept = tokens.count(new)
    if kept > raw_tokens * 0.9 and len(raw) <= (ERROR_LIMIT if code else SHOWN_LIMIT):
        return raw  # barely compressible, and Claude Code would show all of it anyway
    note = "; the command was stopped before it finished" if stopped else ""
    new = new.rstrip("\n") + f"\n[kompact: {raw_tokens}›{kept} tokens{note}; full output: {installer.cli_name()} show {sid}]\n"
    store.record("bash", shown_tokens(raw, code), kept, cmd, os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
                 project=cfg["project"])
    return new


def run(shell: str, full: str, cmd: str, cfg: dict) -> int:
    proc = subprocess.Popen([shell, "-c", full], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stopped = []

    def forward(sig, _frame):  # a timeout or Esc in Claude Code: stop the command, still report what it printed
        stopped.append(sig)
        try:
            proc.send_signal(sig)
        except OSError:
            pass

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, forward)
    head, tail, tail_size, dropped = bytearray(), deque(), 0, 0
    try:
        while True:
            chunk = proc.stdout.read1(65536)
            if not chunk:
                break
            room = HEAD_BYTES - len(head)
            if room > 0:
                head += chunk[:room]
                chunk = chunk[room:]
            if chunk:
                tail.append(chunk)
                tail_size += len(chunk)
                while tail_size - len(tail[0]) >= TAIL_BYTES:
                    tail_size -= len(tail[0])
                    dropped += len(tail.popleft())
    except OSError:
        pass
    code = proc.wait()
    if code < 0:
        code = 128 - code
    raw = head.decode("utf-8", "replace")
    if dropped:
        raw += f"\n… [kompact: {dropped} bytes from the middle were not kept] …\n"
    raw += b"".join(tail).decode("utf-8", "replace")
    try:
        text = compact(cmd, raw, code, cfg, bool(stopped))
    except Exception:  # never lose the output to a Kompact bug
        text = raw
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except OSError:
        pass
    return code


def main(argv) -> int:
    shell, full = argv[0], argv[1]
    try:
        cmd, cfg = decide(full)
    except Exception:
        cmd = cfg = None
    if not cmd:
        os.execvp(shell, [shell, "-c", full])
    return run(shell, full, cmd, cfg)
