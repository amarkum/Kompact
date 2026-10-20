"""Benchmark Kompact's Bash filters on real command output.

    python bench/bench.py <repo-dir> [cmd ...]

Runs each command in the repo, then reports tokens before/after compression.
With no commands, uses a default set of everyday agent commands.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kompact import filters, tokens  # noqa: E402

DEFAULT = [
    "git log -n 40",
    "git log --stat -n 15",
    "git show HEAD~2",
    "git status",
    "find . -type f -not -path './.git/*'",
    "ls -R",
    "grep -rn 'def \\|function ' --include=*.py --include=*.ts .",
]


def main():
    repo, cmds = sys.argv[1], sys.argv[2:] or DEFAULT
    total_r = total_k = 0
    print(f"{'command':<52}{'before':>8}{'after':>8}{'saved':>8}")
    for cmd in cmds:
        p = subprocess.run(cmd, shell=True, cwd=repo, capture_output=True, text=True, errors="replace")
        raw = p.stdout + p.stderr
        out = filters.compress(cmd, raw, p.returncode, stash_id=1)
        r, k = tokens.count(raw), tokens.count(out)
        if r < 150:  # the hook leaves small outputs alone
            k = r
        total_r, total_k = total_r + r, total_k + k
        print(f"{cmd[:50]:<52}{r:>8}{k:>8}{100 * (r - k) / max(r, 1):>7.0f}%")
    print(f"{'TOTAL':<52}{total_r:>8}{total_k:>8}{100 * (total_r - total_k) / max(total_r, 1):>7.0f}%")


if __name__ == "__main__":
    main()
