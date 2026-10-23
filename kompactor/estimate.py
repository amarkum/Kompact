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

from . import filters, outline, store, tokens

LINE_NO = re.compile(r"^\s*\d+[\t→]", re.M)
# After an outline, assume Claude still reads this share of the file by range.
OUTLINE_FOLLOWUP = 0.4
# Tokens Claude writes when it summarises the conversation, for compacting earlier.
SUMMARY_TOKENS = 8000
# What the request after a compaction writes to the cache: the summary plus the files, plan and to-dos Claude Code
# restores (18.7K and 26.3K in two real ~968K compactions); the system prompt and tools before it stay cached.
POST_COMPACT_TOKENS = 25000


def _ctx(u) -> int:
    return sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))


def _write_weight(u) -> float:
    """Cache-write price as a multiple of input for this request: 2x for the 1-hour cache Claude Code uses, 1.25x
    for the 5-minute one, mixed when the usage splits them."""
    cc = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else {}
    h1, m5 = cc.get("ephemeral_1h_input_tokens", 0) or 0, cc.get("ephemeral_5m_input_tokens", 0) or 0
    return (h1 * store.CACHE_WRITE + m5 * store.CACHE_WRITE_5M) / (h1 + m5) if h1 + m5 else store.CACHE_WRITE


def call_cost(u, model: str, prompt_tokens: int = None) -> float:
    """What one API call cost in USD, at its model's rates for a prompt that size."""
    inp, read = store.rates(model, _ctx(u) if prompt_tokens is None else prompt_tokens)
    return ((u.get("input_tokens", 0) or 0) * inp + (u.get("cache_creation_input_tokens", 0) or 0) * inp * _write_weight(u)
            + (u.get("cache_read_input_tokens", 0) or 0) * read + (u.get("output_tokens", 0) or 0) * inp * store.OUTPUT) / 1e6


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
    models = []           # the model of each call
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
                    models.append(msg.get("model") or "")
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
    session_cost = 0.0
    write_usd, read_usd = [], []  # per call: USD per token written to / read from the cache
    for u, m in zip(calls, models):
        i, cw, cr, o = (u.get("input_tokens", 0) or 0, u.get("cache_creation_input_tokens", 0) or 0,
                        u.get("cache_read_input_tokens", 0) or 0, u.get("output_tokens", 0) or 0)
        stats["billed"] += i + cw + cr + o
        session_cost += call_cost(u, m)
        inp, read = store.rates(m, _ctx(u))
        write_usd.append(inp * _write_weight(u) / 1e6)
        read_usd.append(read / 1e6)
        stats["output"] += o
        stats["output_cost"] += o * inp * store.OUTPUT / 1e6
        stats["calls"] += 1
    stats["cost"] += session_cost
    reads_from = [0.0] * (len(calls) + 1)  # reads_from[k]: one token read by every call from k on
    for k in range(len(calls) - 1, -1, -1):
        reads_from[k] = reads_from[k + 1] + read_usd[k]
    window = int((opts or {}).get("compact_window") or 0)
    windowed, added = compact_earlier(calls, min(1_000_000, max(100_000, window)), models) if window else (session_cost, 0)
    stats["saved_compact"] += session_cost - windowed
    stats["compactions_added"] += added
    tool_before, per_session = stats["saved_cost"], {}

    def lifetime(k):
        """Number of API calls that would re-send a result first ingested at call k."""
        end = next((b for b in boundaries if b > k), len(calls))
        return max(1, end - k)

    def usd(k, n):
        """A token ingested at call k: written to the cache once, then read by the next n - 1 calls."""
        if k >= len(calls):
            return 0.0
        return write_usd[k] + reads_from[k + 1] - reads_from[min(len(calls), k + n)]

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
            stats["saved_cost"] += saved * usd(k, n)
            stats["by_feature"][feature] += saved * n
            stats["count_feature"][feature] += 1
            per_session[feature] = per_session.get(feature, 0.0) + saved * usd(k, n)
    # a shorter conversation re-sends a trimmed output fewer times: scale this session's trimming saving with it
    scale = windowed / session_cost if session_cost else 1
    stats["saved_total"] += (session_cost - windowed) + (stats["saved_cost"] - tool_before) * scale
    for feature, v in per_session.items():
        stats["cost_by_feature"][feature] += v * scale


def compact_earlier(calls: list, window: int, models: list = None):
    """This session's cost in USD if Claude Code had compacted whenever the context passed `window` tokens, and how
    many compactions that adds. Each later request re-reads less, at the price for its shorter prompt. Each
    compaction is priced as measured in Claude Code: one request over the whole conversation, read from the cache
    except the newest part (the previous request's cache write, sent again uncached), a summary written as output,
    and the next request writing the summary and restored files to the cache."""
    models = models or [""] * len(calls)
    base, total, offset, prev, added = _ctx(calls[0]), 0.0, 0, 0, 0
    last_ctx, last_write = 0, 0  # the previous request as simulated: its prompt and what it wrote to the cache
    for u, m in zip(calls, models):
        c = _ctx(u)
        if c < prev * 0.6:
            offset = 0  # the session compacted here itself
        prev = c
        i, cw, cr, o = (u.get("input_tokens", 0) or 0, u.get("cache_creation_input_tokens", 0) or 0,
                        u.get("cache_read_input_tokens", 0) or 0, u.get("output_tokens", 0) or 0)
        if c - offset > window:
            conv, fresh = (last_ctx, last_write) if last_ctx else (c - offset, cw)
            inp, read = store.rates(m, conv)
            total += ((conv - fresh) * read + fresh * inp + SUMMARY_TOKENS * inp * store.OUTPUT) / 1e6
            sent = base + POST_COMPACT_TOKENS + cw
            inp, read = store.rates(m, sent)
            total += (base * read + (POST_COMPACT_TOKENS + cw) * inp * _write_weight(u) + i * inp
                      + o * inp * store.OUTPUT) / 1e6
            offset, added = c - sent, added + 1
            last_ctx, last_write = sent, POST_COMPACT_TOKENS + cw
            continue
        sim = {**u, "cache_read_input_tokens": max(0, cr - offset)}
        total += call_cost(sim, m)
        last_ctx, last_write = _ctx(sim), cw
    return total, added


def run(root=None, project=None, limit=None, style_pct=None, opts=None):
    """Replay transcripts. `opts` are effective settings (config.load()); defaults to the current global config."""
    if opts is None:
        from . import config
        opts = config.load()
    stats = defaultdict(float)
    stats.update(tool_by_name=defaultdict(int), by_feature=defaultdict(int), count_feature=defaultdict(int),
                 cost_by_feature=defaultdict(float), top_cmds=[])
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
        stats["style_cost"] = stats["output_cost"] * style_pct
    return stats
