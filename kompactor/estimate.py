"""Replay past Claude Code sessions through Kompactor to estimate savings.

Reads ~/.claude/projects/**/*.jsonl, finds every Bash and Read tool result,
and runs them through the same filters the hooks use. A token removed from a
tool result is not just saved once: it would have been re-sent (as a cache
read) on every later API call in that session until the next compaction. The
estimate accounts for that, which is why context savings compound.
"""

import glob
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from . import filters, outline, tokens

# Relative price weights (input = 1). Same ratios across current Claude models.
W_INPUT, W_CACHE_WRITE, W_CACHE_READ, W_OUTPUT = 1.0, 1.25, 0.1, 5.0
LINE_NO = re.compile(r"^\s*\d+[\t→]", re.M)
# After an outline, assume Claude still reads this share of the file by range.
OUTLINE_FOLLOWUP = 0.4


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def transcripts(root=None, project=None):
    root = Path(root or Path.home() / ".claude" / "projects")
    pattern = f"{glob.escape(str(root / project)) if project else glob.escape(str(root)) + '/*'}/**/*.jsonl"
    return sorted(glob.glob(pattern, recursive=True), key=os.path.getmtime)


def analyze_file(path: str, stats: dict, opts=None) -> None:
    calls = []            # ordered unique API calls: (usage dict)
    seen_ids = set()
    pending = {}          # tool_use_id -> (name, input)
    results = []          # (call_index_when_ingested, name, input, text, is_error)
    boundaries = []       # call indexes where compaction happened
    with open(path, errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") == "system" and d.get("subtype") == "compact_boundary":
                boundaries.append(len(calls))
            msg = d.get("message")
            if not isinstance(msg, dict):
                continue
            if d.get("type") == "assistant":
                mid = msg.get("id") or d.get("requestId")
                if mid and mid not in seen_ids and isinstance(msg.get("usage"), dict):
                    seen_ids.add(mid)
                    calls.append(msg["usage"])
                for b in msg.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        pending[b.get("id")] = (b.get("name"), b.get("input") or {})
            elif d.get("type") == "user" and isinstance(msg.get("content"), list):
                for b in msg["content"]:
                    if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                        name, inp = pending.pop(b["tool_use_id"])
                        results.append((len(calls), name, inp, _text(b.get("content")), bool(b.get("is_error"))))
    if not calls:
        return

    stats["sessions"] += 1
    for u in calls:
        i, cw, cr, o = (u.get("input_tokens", 0) or 0, u.get("cache_creation_input_tokens", 0) or 0,
                        u.get("cache_read_input_tokens", 0) or 0, u.get("output_tokens", 0) or 0)
        stats["billed"] += i + cw + cr + o
        stats["cost"] += i * W_INPUT + cw * W_CACHE_WRITE + cr * W_CACHE_READ + o * W_OUTPUT
        stats["output"] += o
        stats["calls"] += 1

    def lifetime(k):
        """Number of API calls that would re-send a result first ingested at call k."""
        end = next((b for b in boundaries if b > k), len(calls))
        return max(1, end - k)

    reads = {}  # path -> (signature, text) of last read, for dedupe
    for k, name, inp, text, is_err in results:
        n = lifetime(k)
        t = tokens.count(text)
        stats["tool_tokens"] += t
        stats["tool_by_name"][name] += t
        saved, feature = 0, None
        if name == "Bash" and t >= (opts or {}).get("bash_min_tokens", 150):
            cmd = inp.get("command", "")
            new = filters.compress(cmd, text, 1 if is_err else 0, stash_id=1, opts=opts)
            kept = tokens.count(new) + 15  # + the "[kompactor: …]" footer
            if kept < t * 0.9:
                saved, feature = t - kept, "bash:" + filters.classify(cmd)
                stats["top_cmds"].append((saved * n, cmd[:80], t, kept))
        elif name == "Read":
            p = inp.get("file_path", "")
            key = (p, inp.get("offset"), inp.get("limit"))
            if key in reads and reads[key] == text and (opts or {}).get("read_dedupe", True):
                saved, feature = max(0, t - 60), "read:dedupe"
            elif (opts or {}).get("read_outline", True) and inp.get("offset") is None and inp.get("limit") is None \
                    and os.path.splitext(p)[1] in outline.SOURCE_EXT:
                src = LINE_NO.sub("", text)
                if src.count("\n") + 1 >= (opts or {}).get("read_outline_lines", 400):
                    skel = tokens.count(outline.render_outline(p, src)) + 60
                    saved = max(0, int(t * (1 - OUTLINE_FOLLOWUP)) - skel)
                    feature = "read:outline"
            reads[key] = text
        elif name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            p = inp.get("file_path", "")
            for key in [k_ for k_ in reads if k_[0] == p]:
                del reads[key]
        if saved:
            stats["saved_tool"] += saved
            stats["saved_billed"] += saved * n
            stats["saved_cost"] += saved * W_CACHE_WRITE + saved * (n - 1) * W_CACHE_READ
            stats["by_feature"][feature] += saved * n
            stats["count_feature"][feature] += 1


def run(root=None, project=None, limit=None, style_pct=None, opts=None):
    """Replay transcripts. `opts` are effective settings (config.load()); defaults to the current global config."""
    if opts is None:
        from . import config
        opts = config.load()
    stats = defaultdict(float)
    stats.update(tool_by_name=defaultdict(int), by_feature=defaultdict(int), count_feature=defaultdict(int), top_cmds=[])
    files = transcripts(root, project)
    if limit:
        files = files[-limit:]
    for f in files:
        try:
            analyze_file(f, stats, opts)
        except OSError:
            continue
    stats["files"] = len(files)
    if style_pct:
        # Output-style rules are not replayable; apply an assumed prose reduction to output tokens.
        stats["style_cost"] = stats["output"] * style_pct * W_OUTPUT
    return stats
