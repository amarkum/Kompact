"""Compaction on real repositories: run real commands, measure what Claude would read, check failures survive.

    python bench/real_repos.py bench/real_repos.json <work-dir> [--out evidence/real-repos]

Each case names a repository (a public git URL at a fixed commit, or a local repo copied from HEAD with
`git archive`, so nothing is changed in it), the commands an agent would run there, and optionally a file to
plant that makes a test or build fail with a known message. For every command it records:

- baseline: what Claude Code would show Claude without Kompactor (all of it up to 30,000 characters; past
  that, a 2 KB preview for a success, or the first and last ~5,000 characters for a failure),
- kept: what Kompactor's shell prefix would show at levels 1, 3 and 5,
- whether each expected failure line reaches Claude with and without Kompactor.

Private repositories are reported by description and numbers only; no output from them is written.
"""

import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kompactor import config, filters, shellwrap, tokens  # noqa: E402

LEVELS = (1, 3, 5)


def baseline_view(raw: str, code: int) -> str:
    """The text Claude Code itself would put in front of Claude."""
    if code != 0 and len(raw) > shellwrap.ERROR_LIMIT:
        half = shellwrap.ERROR_LIMIT // 2
        return raw[:half] + "\n…\n" + raw[-half:]
    if code == 0 and len(raw) > shellwrap.SHOWN_LIMIT:
        return raw[:shellwrap.PREVIEW_CHARS] + "\n[output saved to a file]"
    return raw


def kompactor_view(cmd: str, raw: str, code: int, level: int, langs) -> str:
    """What the shell prefix would hand Claude at `level` (the original output when it isn't worth compacting)."""
    opts = {k: config.PRESETS[level][k] for k in config.KNOBS}
    opts["languages"] = langs
    if tokens.count(raw) < opts["bash_min_tokens"]:
        return baseline_view(raw, code)
    out = filters.compress(cmd, raw, code, stash_id=1, opts=opts)
    if tokens.count(out) > tokens.count(raw) * 0.9 and len(raw) <= (shellwrap.ERROR_LIMIT if code else shellwrap.SHOWN_LIMIT):
        return raw
    return out


def prepare(case: dict, work: str) -> str:
    dest = os.path.join(work, case["name"])
    shutil.rmtree(dest, ignore_errors=True)
    if case.get("url"):
        subprocess.run(["git", "init", "-q", dest], check=True)
        subprocess.run(["git", "-C", dest, "fetch", "-q", "--depth", "1", case["url"], case["commit"]], check=True)
        subprocess.run(["git", "-C", dest, "checkout", "-q", "FETCH_HEAD"], check=True)
    else:
        src = os.path.expanduser(case["local"])
        os.makedirs(dest)
        sub = case.get("subdir", "")
        archive = subprocess.run(["git", "-C", src, "archive", "HEAD", *( [sub] if sub else [])], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", dest], input=archive.stdout, check=True)
        for link in case.get("link", []):  # dependencies installed in the original (node_modules, .venv)
            os.symlink(os.path.join(src, sub, link), os.path.join(dest, sub, link))
    return os.path.join(dest, case.get("subdir", ""))


def run(cmd: str, cwd: str, timeout: int):
    t = time.time()
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=timeout,
                           env={**os.environ, "CI": "1", "NO_COLOR": "1", "FORCE_COLOR": "0"})
        return p.stdout + (p.stderr if p.stderr else ""), p.returncode, time.time() - t
    except subprocess.TimeoutExpired as e:
        return (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""), 124, timeout


def main():
    spec_path, work = sys.argv[1], sys.argv[2]
    out_dir = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "evidence/real-repos"
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    spec = json.load(open(spec_path))
    os.makedirs(work, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    results_path = os.path.join(out_dir, "results.json")
    results = json.load(open(results_path)) if only and os.path.exists(results_path) else []
    results = [r for r in results if not only or r["case"] not in only]
    for case in spec["cases"]:
        if only and case["name"] not in only:
            continue
        print(f"== {case['name']}", flush=True)
        try:
            cwd = prepare(case, work)
        except subprocess.CalledProcessError as e:
            print(f"   skipped: could not prepare ({e})", flush=True)
            continue
        for step in case["commands"]:
            planted = None
            if step.get("plant"):
                planted = os.path.join(cwd, step["plant"]["path"])
                os.makedirs(os.path.dirname(planted), exist_ok=True)
                mode = "a" if step["plant"].get("append") else "w"
                with open(planted, mode) as f:
                    f.write(step["plant"]["text"])
            run_cwd = os.path.expanduser(case["local"]) if step.get("in_original") else cwd
            raw, code, secs = run(step["cmd"], run_cwd, step.get("timeout", 900))
            if planted and step["plant"].get("remove", True) and not step["plant"].get("append"):
                os.remove(planted)
            langs = case.get("languages", [])
            base = baseline_view(raw, code)
            row = {"case": case["name"], "lang": case["lang"], "private": bool(case.get("private")),
                   "label": step["label"], "cmd": step["cmd"], "exit": code, "seconds": round(secs, 1),
                   "raw_chars": len(raw), "raw_tokens": tokens.count(raw), "baseline_tokens": tokens.count(base),
                   "preview": code == 0 and len(raw) > shellwrap.SHOWN_LIMIT,
                   "expect": len(step.get("expect", [])),
                   "baseline_keeps": sum(e in base for e in step.get("expect", []))}
            for lvl in LEVELS:
                view = kompactor_view(step["cmd"], raw, code, lvl, langs)
                row[f"l{lvl}_tokens"] = tokens.count(view)
                row[f"l{lvl}_keeps"] = sum(e in view for e in step.get("expect", []))
                if lvl == 3 and not case.get("private") and step.get("example"):
                    row["example"] = {"baseline": base[-6000:], "kompactor": view}
            results.append(row)
            print(f"   {step['label']:<34} exit {code:<3} {row['baseline_tokens']:>7} › {row['l3_tokens']:>6} tokens"
                  + (f"  failure lines {row['baseline_keeps']}/{row['expect']} › {row['l3_keeps']}/{row['expect']}"
                     if row["expect"] else ""), flush=True)
        json.dump(results, open(results_path, "w"), indent=1)
        if case.get("cleanup", True):
            shutil.rmtree(os.path.join(work, case["name"]), ignore_errors=True)


def _k(n: int) -> str:
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def _pct(a: int, b: int) -> str:
    return f"{100 * (b - a) / a:+.0f}%" if a else "—"


def report(spec_path: str, out_dir: str) -> str:
    """REPORT.md from results.json: totals, every command, failure survival, and public before/after examples."""
    spec = {c["name"]: c for c in json.load(open(spec_path))["cases"]}
    rows = json.load(open(os.path.join(out_dir, "results.json")))
    base = sum(r["baseline_tokens"] for r in rows)
    read = sum(r["raw_tokens"] if r.get("preview") else r["baseline_tokens"] for r in rows)
    previews = [r for r in rows if r.get("preview")]
    lv = {lvl: sum(r[f"l{lvl}_tokens"] for r in rows) for lvl in LEVELS}
    fails = [r for r in rows if r["expect"]]
    need = sum(r["expect"] for r in fails)
    kept_base = sum(r["baseline_keeps"] for r in fails)
    kept = {lvl: sum(r[f"l{lvl}_keeps"] for r in fails) for lvl in LEVELS}
    lines = [
        "# Compaction on real repositories", "",
        f"Real commands run in {len(spec)} real repositories ({', '.join(sorted({c['lang'] for c in spec.values()}))}), "
        f"{len(rows)} outputs in all, measured with `bench/real_repos.py` on {time.strftime('%Y-%m-%d')}. "
        "No Claude session is involved: this measures what Kompactor's shell prefix and hooks would hand Claude "
        "for each output, against what Claude Code itself would show without Kompactor.", "",
        f"**Across all {len(rows)} outputs, if Claude reads the {len(previews)} outputs Claude Code saves to a file: "
        f"{_k(read)} › {_k(lv[3])} tokens at level 3 (Balanced), {_pct(read, lv[3])}; level 1 {_pct(read, lv[1])}, "
        f"level 5 {_pct(read, lv[5])}.**", "",
        f"Counting only Claude Code's 2 KB preview of those {len(previews)} saved outputs instead: {_k(base)} › {_k(lv[3])}, "
        f"{_pct(base, lv[3])}. The preview is cheaper but holds none of the results (no test summary, no diff body, no "
        "matches past the first lines), so an agent that needs them reads the file. Kompactor hands Claude the "
        "compacted whole output instead. Both figures are given because which one applies depends on the task.", "",
        f"**Failure lines that reached Claude, over {len(fails)} runs with a planted failure: "
        f"{kept_base}/{need} without Kompactor, {kept[1]}/{need} · {kept[3]}/{need} · {kept[5]}/{need} at levels 1 · 3 · 5.**", "",
        "## Repositories", "",
        "| Repository | Language | What it is |", "|---|---|---|"]
    for c in spec.values():
        where = "private, described only" if c.get("private") else f"[{c['url'].split('github.com/')[-1]}]({c['url']}) @ `{c['commit'][:10]}`" \
            if c.get("url") else "this repository"
        lines.append(f"| {c['name']} ({where}) | {c['lang']} | {c['about']} |")
    lines += ["", "## Every command", "",
              "Tokens Claude would read. *Without* is Claude Code alone: the whole output up to 30,000 characters; "
              "past that, a 2 KB preview for a command that succeeded, or the first and last ~5,000 characters for one "
              "that failed. Levels 1, 3 and 5 are Kompactor's Max quality, Balanced and Max savings.", "",
              "*Preview* marks an output Claude Code would save to a file; Δ is then against reading it in full.", "",
              "| Repository | Command | Exit | Raw output | Without | Level 1 | Level 3 | Level 5 | Δ at level 3 |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        ref = r["raw_tokens"] if r.get("preview") else r["baseline_tokens"]
        lines.append(f"| {r['case']} | `{r['label']}` | {r['exit']} | {_k(r['raw_tokens'])} | "
                     f"{_k(r['baseline_tokens'])}{' (preview)' if r.get('preview') else ''} | "
                     f"{_k(r['l1_tokens'])} | {_k(r['l3_tokens'])} | {_k(r['l5_tokens'])} | {_pct(ref, r['l3_tokens'])} |")
    lines += ["", "## Do failures survive?", "",
              "Each planted failure has known lines (its message and file) that Claude needs to fix it. "
              "Counted: how many of them are in what Claude would read.", "",
              "| Repository | Run | Raw output | Without Kompactor | Level 1 | Level 3 | Level 5 |", "|---|---|---:|---|---|---|---|"]
    for r in fails:
        lines.append(f"| {r['case']} | `{r['label']}` | {_k(r['raw_tokens'])} | {r['baseline_keeps']}/{r['expect']} | "
                     f"{r['l1_keeps']}/{r['expect']} | {r['l3_keeps']}/{r['expect']} | {r['l5_keeps']}/{r['expect']} |")
    examples = [r for r in rows if r.get("example")]
    if examples:
        lines += ["", "## Examples (public repositories, level 3)", ""]
        for r in examples:
            lines += [f"### {r['case']}: `{r['label']}`", "",
                      f"Without Kompactor Claude reads {_k(r['baseline_tokens'])} tokens; with it, {_k(r['l3_tokens'])}. "
                      "What Kompactor hands Claude:", "", "```", r["example"]["kompactor"].rstrip(), "```", ""]
    lines += ["## Reproduce", "", "```bash",
              "python bench/real_repos.py bench/real_repos.json /tmp/kompactor-real-repos --out evidence/real-repos",
              "python bench/real_repos.py --report bench/real_repos.json evidence/real-repos", "```", "",
              "Cases marked private need their own repository; edit `bench/real_repos.json` to point at yours. "
              "Planted files are written to a copy (`git archive` of HEAD) or a fresh clone, never to the original."]
    text = "\n".join(lines) + "\n"
    open(os.path.join(out_dir, "REPORT.md"), "w").write(text)
    return text


if __name__ == "__main__":
    if sys.argv[1:2] == ["--report"]:
        print(report(sys.argv[2], sys.argv[3]))
    else:
        main()
