"""Command-output compressors.

Each filter takes the (ANSI-stripped) output lines and returns fewer lines that
carry the same information for an agent. Errors, failures and summaries are
always preserved; progress bars, passing tests, download chatter and repeated
lines are not.
"""

import os
import re
import shlex
from collections import OrderedDict

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*(\x07|\x1b\\)|\x1b[=>]")
IMPORTANT = re.compile(r"error|fail|fatal|exception|traceback|panic|denied|not found|cannot|unable|warning: |assert", re.I)
MAX_LINE = 300

# ---------------------------------------------------------------------------
# command classification


WRAPPERS = {"sudo", "time", "nice", "env", "npx", "bunx", "pnpx", "command"}
RUN_PREFIXES = (("uv", "run"), ("poetry", "run"), ("pipenv", "run"), ("python", "-m"), ("python3", "-m"),
                ("bundle", "exec"), ("npm", "exec"), ("pnpm", "exec"), ("yarn", "exec"))


def argv0(cmd: str):
    """Return the meaningful words of the first command in a shell string."""
    first = re.split(r"\|\||&&|;|\|", cmd, maxsplit=1)[0]
    try:
        words = shlex.split(first)
    except ValueError:
        words = first.split()
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
    if p in ("pytest", "jest", "vitest", "mocha", "ava", "tap", "rspec", "phpunit", "ctest", "tox", "nox"):
        return "test"
    if p in ("go", "cargo", "dotnet", "mix", "deno", "bun", "swift") and sub == "test":
        return "test"
    if p in ("npm", "pnpm", "yarn") and (sub == "test" or (sub == "run" and len(w) > 2 and "test" in w[2])):
        return "test"
    if p in ("make", "gradle", "gradlew", "./gradlew", "mvn", "mvnw") and any("test" in x for x in w[1:]):
        return "test"
    if p in ("npm", "pnpm", "yarn", "pip", "pip3", "uv", "poetry", "cargo", "go", "mvn", "gradle", "gradlew",
             "docker", "apt", "apt-get", "brew", "bundle", "composer", "make", "cmake", "tsc", "bun", "conda"):
        return "build"
    if p in ("find", "fd", "tree") or (p == "ls" and any(a.startswith("-") and "R" in a for a in w[1:])):
        return "listing"
    if p in ("grep", "egrep", "rg", "ag", "ack"):
        return "grep"
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


PROGRESS = re.compile(r"(\d{1,3}(\.\d+)?%|[█▓▒░#=>\-]{8,}|\d+(\.\d+)?\s?[kMG]i?B/s|[⠁-⣿])")


def drop_progress(lines):
    return [ln for ln in lines if not (PROGRESS.search(ln) and not IMPORTANT.search(ln) and len(ln) < 200)]


def _shape(ln: str) -> str:
    return re.sub(r"0x[0-9a-f]+|\d+(\.\d+)?", "#", ln)


def collapse_repeats(lines, min_run: int = 4, shapes: bool = True):
    """Collapse runs of identical lines ("[x50]"), and - for log-like output only -
    runs of lines that differ just in numbers ("… 120 similar lines …")."""
    out, i = [], 0
    while i < len(lines):
        j = i + 1
        exact = True
        while j < len(lines) and (lines[j] == lines[i] or (shapes and _shape(lines[j]) == _shape(lines[i]))):
            exact &= lines[j] == lines[i]
            j += 1
        run = j - i
        if run >= min_run and lines[i].strip():
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
    return lines[:head] + [note] + keep + ([f"… (end of omitted section) …"] if keep else []) + lines[-tail:]


# ---------------------------------------------------------------------------
# specific filters


def f_git_status(lines, _):
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


def f_git_log(lines, _):
    if not lines or not lines[0].startswith("commit "):
        return lines
    out, cur = [], None
    for ln in lines:
        if ln.startswith("commit "):
            if cur:
                out.append(cur)
            cur = {"sha": ln.split()[1][:9], "author": "", "date": "", "msg": None, "extra": ""}
        elif cur is None:
            continue
        elif ln.startswith("Author:"):
            cur["author"] = re.sub(r"\s*<.*>", "", ln[7:].strip())
        elif ln.startswith("Date:"):
            cur["date"] = ln[5:].strip()
        elif ln.startswith("Merge:"):
            cur["extra"] = " (merge)"
        elif ln.startswith("    ") and cur["msg"] is None and ln.strip():
            cur["msg"] = ln.strip()
        elif re.match(r"^\s*\S.*\|\s+\d+", ln) or re.match(r"^\s*\d+ files? changed", ln):
            cur["extra"] += " | " + ln.strip() if "changed" in ln else ""
    if cur:
        out.append(cur)
    return [f"{c['sha']} {_short_date(c['date'])} {c['author']}: {c['msg'] or ''}{c['extra']}" for c in out]


def _short_date(d: str) -> str:
    m = re.match(r"\w{3} (\w{3}) (\d+) [\d:]+ (\d{4})", d)
    return f"{m.group(3)}-{m.group(1)}-{int(m.group(2)):02d}" if m else d


LOCKFILES = re.compile(r"(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Cargo\.lock|poetry\.lock|go\.sum|Gemfile\.lock|composer\.lock|uv\.lock|\.min\.(js|css)|\.map)$")


def f_git_diff(lines, _):
    out, skipping, added, removed, name = [], False, 0, 0, ""

    def flush():
        if skipping:
            out.append(f"[{name}: generated/lock file diff, +{added} -{removed} lines omitted]")

    for ln in lines:
        if ln.startswith("diff --git"):
            flush()
            name = ln.split(" b/")[-1]
            skipping = bool(LOCKFILES.search(name))
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
    return out


GIT_NOISE = re.compile(r"^(remote: )?(Enumerating|Counting|Compressing|Writing|Receiving|Resolving|Total \d|Delta compression|Unpacking|Updating files|Filtering content)")


def f_git_net(lines, _):
    return [ln for ln in lines if not GIT_NOISE.match(ln)]


PASSING = re.compile(
    r"(\bPASS(ED)?\b(?!.*\bFAIL)|^\s*[✓✔√]|^\s*ok\s|^--- PASS|^=== (RUN|PAUSE|CONT)|\.\.\. ok$|^\s*test \S+ \.\.\. ok"
    r"|^\s+✓|^PASS\s|\bpassed\b.*\d+ms$|^\s*\.+\s*\[\s*\d+%\]$)")


def f_test(lines, code):
    kept = [ln for ln in lines if not PASSING.search(ln)]
    dropped = len(lines) - len(kept)
    failed = code != 0 or any(re.search(r"\b(FAILED|FAIL|failed|failures?|ERROR|panicked)\b", ln) for ln in kept)
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
    r"#\d+ (sha256|extracting|resolve|transferring|DONE|CACHED|\[internal\])|npm (http|timing|sill|verb))", re.I)


def f_build(lines, _):
    out, warned = [], OrderedDict()
    for ln in lines:
        if BUILD_NOISE.match(ln) and not IMPORTANT.search(ln):
            continue
        m = re.match(r"(npm WARN deprecated|warning:? deprecated|DEPRECATION:)\s*(\S+)", ln, re.I)
        if m:
            warned[m.group(2)] = 1
            continue
        out.append(ln)
    if warned:
        out.append(f"[{len(warned)} deprecation warnings: {', '.join(list(warned)[:8])}{' …' if len(warned) > 8 else ''}]")
    return out


def f_listing(lines, _):
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


def f_grep(lines, _):
    per_file, out, hidden = {}, [], {}
    for ln in lines:
        m = re.match(r"^([^:\s][^:]*):(\d+[:-])?", ln)
        f = m.group(1) if m else None
        if f:
            per_file[f] = per_file.get(f, 0) + 1
            if per_file[f] > 10:
                hidden[f] = hidden.get(f, 0) + 1
                continue
        out.append(ln)
    for f, n in hidden.items():
        out.append(f"[{f}: +{n} more matches]")
    return truncate_long(out, 220)


FILTERS = {"git_status": f_git_status, "git_log": f_git_log, "git_diff": f_git_diff, "git_net": f_git_net,
           "test": f_test, "build": f_build, "listing": f_listing, "grep": f_grep}

# ---------------------------------------------------------------------------


def compress(cmd: str, output: str, exit_code: int = 0, stash_id=None, max_lines: int = 200) -> str:
    """Compress a command's combined output. Pure function; safe on any input."""
    kind = classify(cmd)
    lines = clean(output)
    if kind in FILTERS and not _piped(cmd):
        lines = FILTERS[kind](lines, exit_code)
    lines = drop_progress(lines)
    lines = collapse_repeats(lines, shapes=kind in ("generic", "build"))
    lines = truncate_long(lines)
    lines = cap(lines, max_lines, head=max_lines // 2, tail=max_lines // 3, stash_id=stash_id)
    return "\n".join(lines)


def _piped(cmd: str) -> bool:
    """Output already shaped by the user's own pipeline/format flags."""
    return bool(re.search(r"(?<!\|)\|(?!\|)", cmd)) or "--format" in cmd or "--pretty" in cmd or "--porcelain" in cmd \
        or "--json" in cmd
