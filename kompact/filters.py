"""Command-output compressors.

Each filter takes the (ANSI-stripped) output lines and returns fewer lines that
carry the same information for an agent. Errors, failures and summaries are
always preserved; progress bars, passing tests, download chatter, library
stack frames and repeated lines are not. How aggressive each step is comes
from the quality-vs-tokens preset (see config.PRESETS).
"""

import os
import re
import shlex
from collections import OrderedDict

from . import langs

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*(\x07|\x1b\\)|\x1b[=>]")
IMPORTANT = re.compile(r"error|fail|fatal|exception|traceback|panic|denied|not found|cannot|unable|warning: |assert", re.I)
MAX_LINE = 300

DEFAULT_OPTS = {"bash_max_lines": 200, "max_line_chars": 500, "grep_per_file": 12, "test_hide_passing": True, "test_boilerplate": False,
                "trim_stack_frames": True,
                "diff_context": -1, "git_log_compact": True, "languages": []}

# ---------------------------------------------------------------------------
# command classification


WRAPPERS = {"sudo", "time", "nice", "env", "npx", "bunx", "pnpx", "command"}
RUN_PREFIXES = (("uv", "run"), ("poetry", "run"), ("pipenv", "run"), ("python", "-m"), ("python3", "-m"),
                ("bundle", "exec"), ("npm", "exec"), ("pnpm", "exec"), ("yarn", "exec"), ("pdm", "run"),
                ("hatch", "run"), ("rye", "run"))
BUILD_TOOLS = {"npm", "pnpm", "yarn", "pip", "pip3", "uv", "poetry", "pdm", "cargo", "go", "mvn", "gradle", "gradlew",
               "docker", "apt", "apt-get", "brew", "bundle", "composer", "make", "cmake", "tsc", "bun", "conda",
               "vite", "next", "webpack", "turbo", "nx", "rollup", "esbuild", "parcel", "expo", "docker-compose"}


SETUP_WORDS = {"cd", "pushd", "popd", "export", "source", ".", "set", "unset", "alias", "ulimit", "umask", "exit", "true", ":"}


def argv0(cmd: str):
    """Return the meaningful words of the first real command in a shell string,
    skipping setup steps like `cd repo &&` or `export X=1;`."""
    words = []
    for seg in re.split(r"&&|;|\|\|", cmd.split("|", 1)[0] if "||" not in cmd else cmd):
        try:
            words = shlex.split(seg)
        except ValueError:
            words = seg.split()
        if words and words[0] not in SETUP_WORDS:
            break
        words = []
    while words and (re.match(r"^\w+=", words[0]) or words[0] in WRAPPERS):
        words = words[1:]
    while len(words) >= 2 and tuple(words[:2]) in RUN_PREFIXES:
        words = words[2:]
    if words:
        words[0] = os.path.basename(words[0])
    return words


def classify(cmd: str) -> str:
    w = argv0(cmd)
    if not w:
        return "generic"
    p, sub = w[0], (w[1] if len(w) > 1 else "")
    if p == "git":
        if sub == "status":
            return "git_status"
        if sub == "log":
            return "git_log"
        if sub in ("diff", "show"):
            return "git_diff"
        if sub in ("push", "pull", "fetch", "clone", "checkout", "switch", "merge", "rebase", "submodule"):
            return "git_net"
        if sub == "grep":
            return "grep"
        if sub == "ls-files":
            return "listing"
    if p in ("pytest", "py.test", "jest", "vitest", "mocha", "ava", "tap", "rspec", "phpunit", "ctest", "tox", "nox",
             "playwright", "cypress", "gotestsum", "unittest"):
        return "test"
    if p in ("go", "cargo", "dotnet", "mix", "deno", "bun", "swift") and sub == "test":
        return "test"
    if p in ("npm", "pnpm", "yarn") and ("test" in sub or (sub == "run" and len(w) > 2 and "test" in w[2])):
        return "test"
    if p in ("make", "gradle", "gradlew", "mvn", "mvnw", "turbo", "nx") and any("test" in x for x in w[1:]):
        return "test"
    if p in BUILD_TOOLS:
        return "build"
    if p in ("find", "fd", "tree") or (p == "ls" and any(a.startswith("-") and "R" in a for a in w[1:])):
        return "listing"
    if p in ("grep", "egrep", "rg", "ag", "ack"):
        return "grep"
    if p in ("cat", "head", "tail", "nl", "bat", "less", "more", "type") or (p == "sed" and "-n" in w[1:]):
        return "view"
    return "generic"


# ---------------------------------------------------------------------------
# generic passes


def clean(text: str):
    text = ANSI.sub("", text)
    lines = []
    for ln in text.split("\n"):
        if "\r" in ln:  # progress redraws: keep only the final frame
            parts = [p for p in ln.split("\r") if p.strip()]
            ln = parts[-1] if parts else ""
        lines.append(ln.rstrip())
    while lines and not lines[-1]:
        lines.pop()
    return lines


# A progress line needs a real progress signal: a bar, a spinner, curl's meter, or a
# transfer speed next to a percentage/count. A bare "50%" is data, not progress.
BAR = re.compile(r"[█▓▒░━■▇▆▅▄▃▂▁]{3,}|\[[#=>\-.\s]{6,}\]|[⠁-⣿]|--:--:--")
SPEED = re.compile(r"\d+(\.\d+)?\s?[kKMG]i?B/s|\beta\b|\bETA\b|\d+(\.\d+)?\s?it/s")
PCT_OR_COUNT = re.compile(r"\b\d{1,3}(\.\d+)?%|\b\d+/\d+\b")
LEADING_PCT = re.compile(r"^\s*\d{1,3}%\s")  # webpack/vite "45% building …"
TEST_RESULT = re.compile(r"\b(PASS|PASSED|FAIL|FAILED|SKIP|SKIPPED|XFAIL|XPASS|ERROR|ok)\b")


def is_progress(ln: str) -> bool:
    if len(ln) >= 200 or IMPORTANT.search(ln) or TEST_RESULT.search(ln) or ln.startswith(("+", "-", "@@")):
        return False
    return bool(BAR.search(ln) or LEADING_PCT.match(ln) or (SPEED.search(ln) and PCT_OR_COUNT.search(ln)))


def drop_progress(lines):
    """Drop progress bars and download meters (never data, test results, diff lines or errors)."""
    return [ln for ln in lines if not is_progress(ln)]


def _shape(ln: str) -> str:
    return re.sub(r"0x[0-9a-f]+|\d+(\.\d+)?", "#", ln)


LOG_LINE = re.compile(r"^\s*[\[(]?(\d{2,4}[-/.]\d{2}[-/.]\d{2}|\d{2}:\d{2}:\d{2}|#\d+ \d)")


def collapse_repeats(lines, min_run: int = 4, shapes: str = "none"):
    """Collapse runs of identical lines ("[x50]"). With shapes="all" (build output) or
    "logs" (timestamped log lines only), also collapse runs of lines that differ just
    in numbers ("… 120 similar lines …"); never for tables or data, where the
    numbers are the information."""
    out, i = [], 0
    while i < len(lines):
        j = i + 1
        exact = True
        shape_ok = shapes == "all" or (shapes == "logs" and bool(LOG_LINE.match(lines[i])))
        while j < len(lines) and (lines[j] == lines[i] or (shape_ok and _shape(lines[j]) == _shape(lines[i]))):
            exact &= lines[j] == lines[i]
            j += 1
        run = j - i
        if run >= (min_run if exact else max(min_run, 6)) and lines[i].strip():
            if exact:
                out.append(f"{lines[i]}  [x{run}]")
            else:
                out += [lines[i], f"  … {run - 2} similar lines …", lines[j - 1]]
        elif run >= 2 and not lines[i].strip():
            out.append("")  # squeeze blank lines
        else:
            out += lines[i:j]
        i = j
    return out


def truncate_long(lines, limit: int = MAX_LINE):
    return [ln if len(ln) <= limit else f"{ln[:limit]}…[+{len(ln) - limit} chars]" for ln in lines]


def cap(lines, max_lines: int, head: int, tail: int, stash_id=None):
    """Keep head and tail; from the middle keep only lines that look important."""
    if len(lines) <= max_lines:
        return lines
    middle = lines[head:len(lines) - tail]
    keep = [ln for ln in middle if IMPORTANT.search(ln)][:30]
    ref = f"; full output: kompact show {stash_id}" if stash_id else ""
    note = f"… {len(middle) - len(keep)} lines omitted{ref} …"
    return lines[:head] + [note] + keep + (["… (end of omitted section) …"] if keep else []) + lines[-tail:]


# ---------------------------------------------------------------------------
# stack traces: collapse frames that live in libraries / the runtime

PY_FRAME = re.compile(r'^\s*File "([^"]+)", line \d+')
PYTEST_FRAME = re.compile(r"^(\S+\.py):\d+: in \S+")
NODE_FRAME = re.compile(r"^\s+at \S")
GO_FUNC = re.compile(r"^([\w./*()\-\[\]{},]+\(.*\)|created by .+)$")
GO_FILE = re.compile(r"^\t\S+\.go:\d+")


def _frames(lines):
    """Yield (start, end, header_text, innermost_last) for each stack frame found in lines."""
    i, n = 0, len(lines)
    while i < n:
        ln = lines[i]
        if PY_FRAME.match(ln):
            ind = len(ln) - len(ln.lstrip())
            j = i + 1
            while j < n and lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) > ind \
                    and not PY_FRAME.match(lines[j]):
                j += 1
            yield i, j, ln, True
            i = j
        elif PYTEST_FRAME.match(ln):
            j = i + 1
            while j < n and not PYTEST_FRAME.match(lines[j]) and not lines[j].startswith(("E ", "_ _", "=", "___")):
                j += 1
            yield i, j, ln, True
            i = j
        elif NODE_FRAME.match(ln):
            yield i, i + 1, ln, False
            i += 1
        elif GO_FUNC.match(ln) and i + 1 < n and GO_FILE.match(lines[i + 1]):
            yield i, i + 2, lines[i + 1], False
            i += 2
        else:
            i += 1


def trim_frames(lines, lib_re):
    if lib_re is None:
        return lines
    frames = list(_frames(lines))
    if len(frames) < 3:
        return lines
    out, pos, k = [], 0, 0
    while k < len(frames):
        s, e, head, innermost_last = frames[k]
        if not lib_re.search(head):
            k += 1
            continue
        # gather a run of consecutive library frames
        run = [frames[k]]
        while k + len(run) < len(frames) and frames[k + len(run)][0] == run[-1][1] \
                and lib_re.search(frames[k + len(run)][2]):
            run.append(frames[k + len(run)])
        nxt = k + len(run)
        ends_trace = nxt >= len(frames) or frames[nxt][0] != run[-1][1]
        if len(run) >= 2:
            # Python prints the raising frame last; keep it. Go/Node print it first.
            hide = run[:-1] if ends_trace and innermost_last else run
            out += lines[pos:hide[0][0]]
            out.append(f"{' ' * (len(head) - len(head.lstrip()))}[… {len(hide)} library frames hidden …]")
            pos = hide[-1][1]
        k = nxt
    out += lines[pos:]
    return out


# ---------------------------------------------------------------------------
# specific filters


def f_git_status(lines, opts):
    if not any(ln.startswith(("On branch", "HEAD detached", "Changes", "Untracked", "nothing to commit")) for ln in lines):
        return lines  # already short format
    out, section, groups = [], None, OrderedDict()
    labels = {"Changes to be committed": "staged", "Changes not staged for commit": "unstaged",
              "Untracked files": "untracked", "Unmerged paths": "conflicts"}
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("(use ") or s.startswith("(commit or discard") or s.startswith("no changes added"):
            continue
        if s.rstrip(":") in labels:
            section = labels[s.rstrip(":")]
            continue
        if ln.startswith(("\t", "        ")) and section:
            m = re.match(r"(new file|modified|deleted|renamed|typechange|both modified|both added|deleted by \w+):\s+(.*)", s)
            item = f"{m.group(1).split()[0][0].upper() if m.group(1) != 'renamed' else 'R'} {m.group(2)}" if m else s
            groups.setdefault(section, []).append(item)
            continue
        out.append(s)
    for sec, items in groups.items():
        shown = items[:40] + ([f"… +{len(items) - 40} more"] if len(items) > 40 else [])
        out.append(f"{sec} ({len(items)}): " + ", ".join(shown))
    return out


def f_git_log(lines, opts):
    """One line per commit (sha, date, author, subject). Whatever follows the message (--stat,
    --name-only, --name-status and --numstat file lines, or the patch for -p) is kept as is."""
    if not opts["git_log_compact"] or not lines or not lines[0].startswith("commit "):
        return lines
    out, cur = [], None
    for ln in lines:
        if ln.startswith("commit "):
            if cur:
                out.append(cur)
            cur = {"sha": ln.split()[1][:9], "author": "", "date": "", "msg": None, "extra": "", "files": [],
                   "patch": False}
        elif cur is None:
            continue
        elif cur["patch"] or ln.startswith("diff --git "):
            cur["patch"] = True
            cur["files"].append(ln)
        elif ln.startswith("Author:") and cur["msg"] is None:
            cur["author"] = re.sub(r"\s*<.*>", "", ln[7:].strip())
        elif ln.startswith("Date:") and cur["msg"] is None:
            cur["date"] = ln[5:].strip()
        elif ln.startswith("Merge:") and cur["msg"] is None:
            cur["extra"] = " (merge)"
        elif ln.startswith("    "):
            if cur["msg"] is None and ln.strip():
                cur["msg"] = ln.strip()
        elif re.match(r"^\s*\d+ files? changed", ln):
            cur["extra"] += " | " + ln.strip()
        elif ln.strip():
            cur["files"].append(ln)
    if cur:
        out.append(cur)
    res = []
    for c in out:
        res.append(f"{c['sha']} {_short_date(c['date'])} {c['author']}: {c['msg'] or ''}{c['extra']}")
        res.extend(c["files"])
    return res


def _short_date(d: str) -> str:
    m = re.match(r"\w{3} (\w{3}) (\d+) [\d:]+ (\d{4})", d)
    return f"{m.group(3)}-{m.group(1)}-{int(m.group(2)):02d}" if m else d


def f_git_diff(lines, opts):
    lock_re = langs.lockfile_re(opts["languages"])
    gen_re = langs.generated_re(opts["languages"])
    out, skipping, added, removed, name, why = [], False, 0, 0, "", ""

    def flush():
        if skipping:
            out.append(f"[{name}: {why} diff, +{added} -{removed} lines omitted]")

    for ln in lines:
        if ln.startswith("diff --git"):
            flush()
            name = ln.split(" b/")[-1]
            why = "lock file" if lock_re.search(name) else "generated file" if gen_re and gen_re.search(name) else ""
            skipping = bool(why)
            added = removed = 0
            out.append(ln)
            continue
        if skipping:
            added += ln.startswith("+") and not ln.startswith("+++")
            removed += ln.startswith("-") and not ln.startswith("---")
            continue
        if ln.startswith("index ") or ln.startswith("similarity index"):
            continue
        out.append(ln)
    flush()
    ctx = opts["diff_context"]
    return trim_diff_context(out, ctx) if ctx is not None and ctx >= 0 else out


def trim_diff_context(lines, ctx: int):
    """Keep only `ctx` unchanged lines around each change inside hunks."""
    out, hunk = [], []

    def flush():
        if not hunk:
            return
        changed = [i for i, ln in enumerate(hunk) if ln[:1] in "+-"]
        keep = set()
        for i in changed:
            keep.update(range(i - ctx, i + ctx + 1))
        gap = 0
        for i, ln in enumerate(hunk):
            if i in keep or ln[:1] not in " " or ln.startswith("\\"):
                if gap:
                    out.append(f" ⋯ {gap} unchanged")
                    gap = 0
                out.append(ln)
            else:
                gap += 1
        if gap:
            out.append(f" ⋯ {gap} unchanged")
        hunk.clear()

    in_hunk = False
    for ln in lines:
        if ln.startswith("@@"):
            flush()
            out.append(ln)
            in_hunk = True
        elif in_hunk and (ln[:1] in " +-\\" or ln == "") and not ln.startswith(("diff --git", "--- ", "+++ ")):
            hunk.append(ln if ln else " ")
        else:
            flush()
            in_hunk = ln.startswith("@@")
            out.append(ln)
    flush()
    return out


GIT_NOISE = re.compile(r"^(remote: )?(Enumerating|Counting|Compressing|Writing|Receiving|Resolving|Total \d|"
                       r"Delta compression|Unpacking|Updating files|Filtering content)")


def f_git_net(lines, opts):
    return [ln for ln in lines if not GIT_NOISE.match(ln)]


PASSING = re.compile(
    r"(\bPASS(ED)?\b(?!.*\bFAIL)|^\s*[✓✔√]|^\s*ok\s|^--- PASS|^=== (RUN|PAUSE|CONT|NAME)|\.\.\. ok$|^\s*test \S+ \.\.\. ok"
    r"|^\?\s+\S+\s+\[no test files\]|^PASS\s|\bpassed\b.*\d+ms$|^\s*\.+\s*\[\s*\d+%\]$)")
FAILED = re.compile(r"\b(FAILED|FAIL|failed|failures?|ERROR|panicked|panic:)\b")


TEST_BOILER = re.compile(
    r"^(platform \w+ -- Python|rootdir:|configfile:|plugins:|cachedir:|collected \d+ items?|"
    r"=+ (test session starts|short test summary info) =+$|(_ )+_?$|\s*⎯{5,}|\s*RUN\s+v\d|\s+Start at\s|\s+Duration\s)")


def f_test(lines, opts):
    if not opts["test_hide_passing"]:
        return lines
    kept = [ln for ln in lines if not PASSING.search(ln) and not (BUILD_NOISE.match(ln) and not IMPORTANT.search(ln))]
    if opts["test_boilerplate"]:
        kept = [ln for ln in kept if not TEST_BOILER.match(ln)]
    dropped = len(lines) - len(kept)
    failed = any(FAILED.search(ln) for ln in kept)
    if not failed and len(kept) > 40:
        # green run: the summary at the bottom is what matters
        kept = [f"… {len(kept) - 25} lines of passing-run output omitted …"] + kept[-25:]
    if dropped:
        kept.append(f"[kompact: {dropped} passing-test lines hidden]")
    return kept


BUILD_NOISE = re.compile(
    r"^\s*(Downloading|Downloaded|Collecting|Requirement already satisfied|Using cached|Obtaining|Fetching|Fetched|"
    r"Compiling|Checking|Fresh|Installing collected|Preparing metadata|Building wheel|Created wheel|Stored in directory|"
    r"Resolving|Resolved|Prepared|Audited|Get:\d|Hit:\d|Ign:\d|Reading (package|state)|Building dependency tree|"
    r"Unpacking|Selecting previously|Setting up|Processing triggers|\[INFO\] Download|Progress \(\d|"
    r"go: (downloading|finding|extracting)|"
    r"#\d+ (sha256|extracting|resolve|transferring|DONE|CACHED|\[internal\])|npm (http|timing|sill|verb))", re.I)
PKG_LINE = re.compile(r"^\s*([+\-~]) ([\w.\-\[\]]+)[=@ ]=?\s*v?[\w.+\-]+$")  # uv / pnpm "+ pkg==1.2" lines


def f_build(lines, opts):
    out, warned, pkgs = [], OrderedDict(), {"+": [], "-": [], "~": []}
    for ln in lines:
        if BUILD_NOISE.match(ln) and not IMPORTANT.search(ln):
            continue
        m = re.match(r"(npm WARN deprecated|warning:? deprecated|DEPRECATION:)\s*(\S+)", ln, re.I)
        if m:
            warned[m.group(2)] = 1
            continue
        m = PKG_LINE.match(ln)
        if m:
            pkgs[m.group(1)].append(m.group(2))
            continue
        out.append(ln)
    for sign, label in (("+", "added"), ("-", "removed"), ("~", "changed")):
        if pkgs[sign]:
            names = pkgs[sign]
            out.append(f"[{len(names)} packages {label}: {', '.join(names[:10])}{' …' if len(names) > 10 else ''}]")
    if warned:
        out.append(f"[{len(warned)} deprecation warnings: {', '.join(list(warned)[:8])}{' …' if len(warned) > 8 else ''}]")
    return out


def f_listing(lines, opts):
    if len(lines) <= 60:
        return lines
    by_dir = OrderedDict()
    if sum(ln.endswith(":") for ln in lines) >= 2:  # `ls -R`: "dir:" headers followed by names
        cur = "."
        for ln in lines:
            if ln.endswith(":"):
                cur = ln[:-1]
                by_dir.setdefault(cur, [])
            elif ln.strip():
                by_dir.setdefault(cur, []).extend(ln.split())
        lines = [f for fs in by_dir.values() for f in fs]
    else:
        for ln in lines:
            d, _, f = ln.strip().rpartition("/")
            by_dir.setdefault(d or ".", []).append(f)
    out = [f"[{len(lines)} paths in {len(by_dir)} directories]"]
    for d, files in by_dir.items():
        shown = ", ".join(files[:8]) + (f", … +{len(files) - 8}" if len(files) > 8 else "")
        out.append(f"{d}/ ({len(files)}): {shown}")
    return out


def f_grep(lines, opts):
    limit = opts["grep_per_file"]
    per_file, out, hidden = {}, [], {}
    for ln in lines:
        m = re.match(r"^([^:\s][^:]*):(\d+[:-])?", ln)
        f = m.group(1) if m else None
        if f:
            per_file[f] = per_file.get(f, 0) + 1
            if per_file[f] > limit:
                hidden[f] = hidden.get(f, 0) + 1
                continue
        out.append(ln)
    for f, n in hidden.items():
        out.append(f"[{f}: +{n} more matches]")
    return truncate_long(out, 220)


FILTERS = {"git_status": f_git_status, "git_log": f_git_log, "git_diff": f_git_diff, "git_net": f_git_net,
           "test": f_test, "build": f_build, "listing": f_listing, "grep": f_grep}

# ---------------------------------------------------------------------------


def compress(cmd: str, output: str, exit_code: int = 0, stash_id=None, opts=None, max_lines=None) -> str:
    """Compress a command's combined output. Pure function; safe on any input."""
    o = dict(DEFAULT_OPTS)
    o.update({k: v for k, v in (opts or {}).items() if k in DEFAULT_OPTS})
    if max_lines:
        o["bash_max_lines"] = max_lines
    kind = classify(cmd)
    lines = clean(output)
    m = o["bash_max_lines"]
    if kind == "view":  # Claude asked to see this file: keep it verbatim, only cap huge ones
        m *= 2
        return "\n".join(cap(lines, m, head=m // 2, tail=m // 3, stash_id=stash_id))
    if kind in FILTERS and not _piped(cmd):
        lines = FILTERS[kind](lines, o)
    if o["trim_stack_frames"] and kind != "git_diff":
        lines = trim_frames(lines, langs.library_frame_re(o["languages"]))
    lines = drop_progress(lines)
    lines = collapse_repeats(lines, shapes={"build": "all", "generic": "logs", "test": "logs"}.get(kind, "none"))
    lines = truncate_long(lines, o["max_line_chars"])
    lines = cap(lines, m, head=m // 2, tail=m // 3, stash_id=stash_id)
    return "\n".join(lines)


def _piped(cmd: str) -> bool:
    """Output already shaped by the user's own pipeline/format flags."""
    return bool(re.search(r"(?<!\|)\|(?!\|)", cmd)) or "--format" in cmd or "--pretty" in cmd or "--porcelain" in cmd \
        or "--json" in cmd


# ---------------------------------------------------------------------------
# commands the shell prefix may buffer: finite and noisy (tests, builds, linters,
# installs). Never servers, watchers or anything interactive: buffering those would
# hide their output until they exit.

LINTERS = {"tsc", "vue-tsc", "svelte-check", "eslint", "oxlint", "biome", "prettier", "stylelint", "ruff", "mypy",
           "pyright", "basedpyright", "flake8", "pylint", "black", "isort", "bandit", "golangci-lint", "staticcheck",
           "revive", "shellcheck", "hadolint", "rubocop", "markdownlint"}
FINITE_SCRIPT = re.compile(r"^(build|lint|typecheck|type-check|types|check|test|tsc|compile|ci|validate|verify|e2e|"
                           r"format:check|fmt:check)(:[\w:-]+)?$")
INSTALL_WORDS = {"install", "i", "ci", "add", "sync", "update", "upgrade", "lock", "remove", "uninstall", "audit",
                 "outdated", "dedupe", "rebuild", "prune"}
LONG_RUNNING = re.compile(r"(^|\s)(--watch\w*|-w|--ui|--follow|--serve|--open)(\s|=|$)")
SAFE_STEPS = {"echo", "printf", "ls", "pwd", "mkdir", "rm", "cp", "mv", "touch", "cat", "which", "true", "false", "git",
              "rmdir", "ln", "chmod", "date", "wc"}


def _wrappable_words(w) -> bool:
    if not w:
        return True
    p, rest = w[0], w[1:]
    sub = rest[0] if rest else ""
    if any(a in ("watch", "dev", "serve", "start", "open", "run-server", "runserver", "up") for a in rest[:2]):
        return False
    if p in ("pytest", "py.test", "jest", "vitest", "mocha", "ava", "tap", "rspec", "phpunit", "ctest", "tox", "nox",
             "playwright", "cypress", "gotestsum", "unittest") or p in LINTERS:
        return True
    if p == "go":
        return sub in ("test", "build", "vet", "generate", "install", "mod")
    if p == "cargo":
        return sub in ("test", "build", "check", "clippy", "fetch", "doc", "fmt", "nextest")
    if p in ("npm", "pnpm", "yarn", "bun"):
        if sub in INSTALL_WORDS or (p == "yarn" and not sub) or sub == "test":
            return True
        if sub in ("run", "run-script"):
            return len(rest) > 1 and bool(FINITE_SCRIPT.match(rest[1]))
        return p != "npm" and bool(FINITE_SCRIPT.match(sub))
    if p in ("pip", "pip3", "poetry", "pdm", "uv", "conda", "bundle", "composer"):
        return sub in INSTALL_WORDS or (sub == "pip" and len(rest) > 1 and rest[1] in INSTALL_WORDS)
    if p in ("make", "ninja", "cmake"):
        return not any(a in ("run", "serve", "dev", "watch", "start") for a in rest)
    if p in ("mvn", "mvnw", "gradle", "gradlew", "./mvnw", "./gradlew"):
        return not any(a in ("run", "bootRun", "spring-boot:run", "jetty:run", "exec:java", "--continuous", "-t")
                       for a in rest)
    if p == "docker":
        return sub == "build" or (sub in ("compose", "buildx") and "build" in rest[:2])
    if p in ("next", "vite", "nuxt", "astro", "remix", "expo", "turbo", "nx"):
        return "build" in rest[:3] or any(FINITE_SCRIPT.match(a.split(":")[-1]) for a in rest[1:3] if sub == "run")
    if p in ("webpack", "rollup", "esbuild", "tsup", "parcel"):
        return sub != "serve"
    return False


def wrappable(cmd: str) -> bool:
    """True when every step of `cmd` is a finite, noisy command (or a trivial setup
    step), so running it to completion before Claude sees the output is safe."""
    if not cmd.strip() or "\n" in cmd.strip() or _piped(cmd) or LONG_RUNNING.search(cmd) \
            or re.search(r"(?<![&>|])&(?![&>])", cmd) or re.search(r"(^|\s)(nohup|setsid|disown|exec)\s", cmd):
        return False
    noisy = False
    for seg in re.split(r"&&|\|\||;", cmd):
        try:
            words = shlex.split(seg)
        except ValueError:
            return False
        if not words or words[0] in SETUP_WORDS:
            continue
        w = argv0(seg)
        if w and os.path.basename(w[0]) in SAFE_STEPS:
            continue
        if not _wrappable_words(w):
            return False
        noisy = True
    return noisy
