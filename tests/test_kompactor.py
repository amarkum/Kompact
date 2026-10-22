import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path

TMP = tempfile.mkdtemp()
os.environ["KOMPACTOR_HOME"] = os.path.join(TMP, "home")

from kompactor import config, estimate, filters, hooks, installer, langs, outline, server, store, tokens  # noqa: E402
installer.PATH_DIRS = ()  # never link `kompactor` into real PATH folders from tests
installer.EDITORS = ()  # never install or remove the real VS Code / Cursor extension from tests


def run_hook(name, event):
    sys.stdin = io.StringIO(json.dumps(event))
    buf = io.StringIO()
    with redirect_stdout(buf):
        hooks.run(name)
    sys.stdin = sys.__stdin__
    out = buf.getvalue()
    return json.loads(out)["hookSpecificOutput"] if out else None


GIT_LOG = "".join(
    f"commit {i:040x}\nAuthor: Dev Person <dev@example.com>\nDate:   Mon Oct 5 12:00:0{i % 10} 2026 +0000\n\n"
    f"    Commit message number {i}\n\n    Longer body text that explains the change in detail.\n\n" for i in range(30))


class FilterTests(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(filters.classify("git status"), "git_status")
        self.assertEqual(filters.classify("cd x && git log -n 3"), "git_log")  # setup steps are skipped
        self.assertEqual(filters.classify("cd x || exit 1; export CI=1; go test ./..."), "test")
        self.assertEqual(filters.classify("echo hi && pytest"), "generic")  # a real first command decides
        self.assertEqual(filters.classify("FOO=1 npx jest --ci"), "test")
        self.assertEqual(filters.classify("uv run pytest -q"), "test")
        self.assertEqual(filters.classify("npm run test:unit"), "test")
        self.assertEqual(filters.classify("rg foo"), "grep")
        self.assertEqual(filters.classify("npm install"), "build")

    def test_git_log_compacts_and_keeps_subjects(self):
        out = filters.compress("git log", GIT_LOG)
        self.assertEqual(len(out.splitlines()), 30)
        self.assertIn("Commit message number 7", out)
        self.assertLess(tokens.count(out), tokens.count(GIT_LOG) * 0.5)

    def test_git_log_keeps_stat_files_and_patches(self):
        stat = "".join(f"commit {i:040x}\nAuthor: Dev <d@x.io>\nDate:   Mon Oct 5 12:00:00 2026 +0000\n\n"
                       f"    Change {i}\n\n    Body line.\n\n src/app_{i % 3}.py | 4 ++--\n docs/x.md      | 1 +\n"
                       f" 2 files changed, 3 insertions(+), 2 deletions(-)\n\n" for i in range(12))
        out = filters.compress("git log -n 12 --stat", stat)
        self.assertEqual(out.count(" src/app_0.py | 4 ++--"), 4)  # per-file lines are what --stat asked for
        self.assertNotIn("Body line.", out)
        self.assertIn("Change 5 | 2 files changed", out)
        patch = ("commit " + "a" * 40 + "\nAuthor: Dev <d@x.io>\nDate:   Mon Oct 5 12:00:00 2026 +0000\n\n    Fix\n\n"
                 "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1,2 +1,2 @@\n def f():\n"
                 "-    return 1\n+    return 2\n         nested = True\n")
        out = filters.compress("git log -p -n 1", patch)
        self.assertIn("         nested = True", out)  # indented context inside a patch is not message text
        self.assertIn("+    return 2", out)

    def test_output_claude_shaped_is_never_cut_short(self):
        names = "".join(f"@@{i:07x}\nsrc/flask/mod_{i % 9}.py\nsrc/flask/app.py\n\n" for i in range(40))  # 160 lines
        for opts in (config.PRESETS[5], config.PRESETS[3]):
            self.assertEqual(filters.compress("git log -n 40 --format=@@%h --name-only -- src", names, opts=opts),
                             names.rstrip("\n"))
            piped = "".join(f"{i:4d} src/f{i}.py\n" for i in range(150))
            self.assertEqual(filters.compress("git log --name-only | sort | uniq -c", piped, opts=opts), piped.rstrip("\n"))

    def test_git_log_custom_format_untouched(self):
        raw = "abc123 one\ndef456 two"
        self.assertEqual(filters.compress("git log --format=%h", raw), raw)

    def test_git_status(self):
        raw = textwrap.dedent("""\
            On branch main
            Changes not staged for commit:
              (use "git add <file>..." to update what will be committed)
            \tmodified:   a.py
            \tdeleted:    b.py

            Untracked files:
              (use "git add <file>..." to include in what will be committed)
            \tc.py
            """)
        out = filters.compress("git status", raw)
        self.assertIn("unstaged (2): M a.py, D b.py", out)
        self.assertIn("untracked (1): c.py", out)
        self.assertNotIn("use \"git add", out)

    def test_failing_tests_keep_failures(self):
        raw = "\n".join([f"tests/test_x.py::test_{i} PASSED [{i}%]" for i in range(80)]
                        + ["tests/test_x.py::test_bad FAILED", "E   assert 1 == 2", "=== 1 failed, 80 passed ==="])
        out = filters.compress("pytest -v", raw, 1)
        self.assertIn("test_bad FAILED", out)
        self.assertIn("assert 1 == 2", out)
        self.assertNotIn("test_3 PASSED", out)
        self.assertIn("80 passing-test lines hidden", out)

    def test_failure_detected_without_exit_code(self):
        raw = "\n".join(["x" * 10 + str(i) for i in range(60)] + ["FAILED tests/a.py::t - boom", "1 failed"])
        self.assertIn("FAILED tests/a.py::t", filters.compress("pytest", raw, 0))

    def test_ansi_progress_and_repeats(self):
        raw = "\x1b[32mok\x1b[0m\n" + "Downloading ━━━━ 10%\rDownloading ━━━━━━━━ 100% 3.2 MB/s\n" + "same line\n" * 50 + "done"
        out = filters.compress("some-tool", raw)
        self.assertNotIn("\x1b", out)
        self.assertIn("same line  [x50]", out)
        self.assertNotIn("Downloading", out)

    def test_data_with_percentages_is_kept(self):
        grep = "\n".join(f"src/s{i}.css:{i}:  width: {i}%;" for i in range(30))
        self.assertEqual(filters.compress("grep -rn width src", grep).count("width:"), 30)
        log = "\n".join(f"abc{i:04d} speed up parser by {i}%" for i in range(30))
        self.assertEqual(filters.compress("git log --oneline", log), log)
        cov = "Name    Stmts   Miss  Cover\n" + "\n".join(f"src/m{i}.py   120   {i}   {99 - i}%" for i in range(20))
        self.assertIn("src/m7.py   120   7   92%", filters.compress("pytest --cov", cov))
        pods = "\n".join(f"api-{i}   1/1   Running   0   {i}m" for i in range(30))
        self.assertEqual(filters.compress("kubectl get pods", pods), pods)

    def test_real_progress_is_dropped(self):
        raw = "\n".join(["Collecting flask", "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 3.0 MB/s eta 0:00:00",
                         "  % Total    % Received", "100  1234  100  1234    0     0  12345      0 --:--:-- --:--:-- --:--:-- 12345",
                         "45% building 120/300 modules", "Successfully installed flask-3.1"])
        out = filters.compress("some-installer", raw)
        self.assertNotIn("MB/s", out)
        self.assertNotIn("--:--:--", out)
        self.assertNotIn("45% building", out)
        self.assertIn("Successfully installed flask-3.1", out)

    def test_view_commands_stay_verbatim(self):
        src = "\n".join(["x = '" + "a" * 900 + "'"] + [f"line {i}" for i in range(50)] * 2)
        self.assertEqual(filters.compress("cat big.py", src), src)
        self.assertIn("kompactor show 3", filters.compress("cat huge.log", "\n".join(f"l{i}" for i in range(2000)), stash_id=3))

    def test_log_lines_collapse_but_tables_do_not(self):
        logs = "\n".join(f"2026-10-20 12:00:{i:02d} INFO heartbeat ok seq={i}" for i in range(40))
        self.assertIn("similar lines", filters.compress("docker logs api", logs))

    def test_errors_survive_truncation(self):
        lines = [f"{chr(97 + i % 26) * 3}{chr(97 + i // 26 % 26)} entry" for i in range(1000)]
        lines[500] = "ERROR: the important thing broke"
        out = filters.compress("custom", "\n".join(lines), 1, stash_id=7)
        self.assertIn("ERROR: the important thing broke", out)
        self.assertIn("kompactor show 7", out)

    def test_lockfile_diff_collapsed(self):
        raw = "diff --git a/package-lock.json b/package-lock.json\nindex 1..2\n--- a/x\n+++ b/x\n" + "+x\n" * 300 + \
              "diff --git a/src/a.ts b/src/a.ts\n--- a/src/a.ts\n+++ b/src/a.ts\n+real change\n"
        out = filters.compress("git diff", raw)
        self.assertIn("package-lock.json: lock file diff, +300", out)
        self.assertIn("+real change", out)

    def test_grep_caps_per_file(self):
        raw = "\n".join(f"src/a.py:{i}:match {i}" for i in range(40)) + "\nsrc/b.py:1:other"
        out = filters.compress("grep -rn match", raw)
        self.assertIn("[src/a.py: +28 more matches]", out)
        self.assertIn("src/b.py:1:other", out)


PY_SRC = textwrap.dedent('''\
    import os

    LIMIT = 10


    class Store:
        """Holds things."""

        def get(self, key):
            return key

        @property
        def size(self):
            return 0


    def helper(a, b):
        return a + b
    ''')

TS_SRC = textwrap.dedent('''\
    import {type Foo, bar} from './x';

    export interface Options {
    \ttimeout: number;
    }

    export class Client {
    \tasync #send(url: string): Promise<void> {
    \t\tif (url) {
    \t\t\treturn;
    \t\t}
    \t}

    \tget(url: string): string {
    \t\treturn url;
    \t}
    }

    export const create = (options: Options) => new Client();
    ''')


class ListingTests(unittest.TestCase):
    def test_ls_recursive(self):
        raw = "src:\nmain.py\nutil\n\nsrc/util:\n" + "\n".join(f"mod{i}.py" for i in range(70))
        out = filters.compress("ls -R src", raw)
        self.assertIn("src/util/ (70): mod0.py", out)
        self.assertIn("src/ (2): main.py, util", out)


class OutlineTests(unittest.TestCase):
    def test_python(self):
        items = outline.outline("x.py", PY_SRC)
        sigs = [s for _, _, _, s in items]
        self.assertIn("LIMIT = 10", sigs)
        self.assertTrue(any(s.startswith("class Store:") and "Holds things" in s for s in sigs))
        self.assertIn("@property def size(self):", sigs)
        self.assertEqual([it for it in items if it[3].startswith("def helper")][0][:2], (17, 18))

    def test_typescript(self):
        sigs = {s: (a, b, d) for a, b, d, s in outline.outline("x.ts", TS_SRC)}
        self.assertNotIn("type Foo", " ".join(sigs))
        self.assertEqual(sigs["export class Client"], (7, 17, 0))
        self.assertEqual(sigs["async #send(url: string): Promise<void>"], (8, 12, 1))
        self.assertIn("get(url: string): string", sigs)

    def test_find_symbol(self):
        d = tempfile.mkdtemp()
        Path(d, "a.py").write_text(PY_SRC)
        Path(d, "b.ts").write_text(TS_SRC)
        hits = outline.find_symbol("Store.get", d, ["a.py", "b.ts"])
        self.assertEqual(len(hits), 1)
        self.assertIn("return key", hits[0][3])
        hits = outline.find_symbol("get", d, ["a.py", "b.ts"])
        self.assertEqual({h[0] for h in hits}, {"a.py", "b.ts"})

    def test_repo_map_budget(self):
        d = tempfile.mkdtemp()
        for i in range(30):
            Path(d, f"m{i}.py").write_text(PY_SRC.replace("Store", f"Store{i}"))
        out = outline.repo_map(d, budget_tokens=300)
        self.assertLess(tokens.count(out), 450)
        self.assertIn("lower-ranked files omitted", out)


class HookTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.big = os.path.join(self.dir, "big.py")
        body = "".join(f"    y = x * {j}\n" for j in range(8))
        Path(self.big).write_text("\n".join(f"def f{i}(x):\n{body}    return y + {i}\n" for i in range(60)))
        self.small = os.path.join(self.dir, "small.py")
        Path(self.small).write_text("def f(x):\n    return x\n" * 40)

    def test_post_bash_compacts(self):
        ev = {"session_id": "t", "tool_input": {"command": "git log"},
              "tool_response": {"stdout": GIT_LOG, "stderr": "", "interrupted": False, "isImage": False}}
        res = run_hook("post-bash", ev)["updatedToolOutput"]
        self.assertEqual(set(res), {"stdout", "stderr", "interrupted", "isImage"})
        self.assertIn("Commit message number 3", res["stdout"])
        sid = int(res["stdout"].rsplit(" show ", 1)[1].rstrip("]"))
        self.assertEqual(store.get_stash(sid)[1], GIT_LOG)

    def test_post_bash_leaves_small_output(self):
        ev = {"tool_input": {"command": "ls"}, "tool_response": {"stdout": "a\nb", "stderr": ""}}
        self.assertIsNone(run_hook("post-bash", ev))

    def test_read_outline_then_allow(self):
        ev = {"session_id": "r1", "tool_input": {"file_path": self.big}}
        first = run_hook("pre-read", ev)
        self.assertEqual(first["permissionDecision"], "deny")
        self.assertIn("def f2(x):  [L23-32]", first["permissionDecisionReason"])
        self.assertIsNone(run_hook("pre-read", ev))  # retry gets the whole file

    def test_partial_read_never_blocked(self):
        ev = {"session_id": "r2", "tool_input": {"file_path": self.big, "offset": 10, "limit": 20}}
        self.assertIsNone(run_hook("pre-read", ev))

    def test_dedupe_once_then_allow_and_reset_on_change(self):
        ev = {"session_id": "r3", "tool_input": {"file_path": self.small}}
        self.assertIsNone(run_hook("pre-read", ev))
        self.assertEqual(run_hook("pre-read", ev)["permissionDecision"], "deny")
        self.assertIsNone(run_hook("pre-read", ev))
        Path(self.small).write_text("changed\n" * 200)
        self.assertIsNone(run_hook("pre-read", ev))

    def test_compaction_resets_reads(self):
        ev = {"session_id": "r4", "tool_input": {"file_path": self.small}}
        run_hook("pre-read", ev)
        run_hook("pre-compact", {"session_id": "r4"})
        self.assertIsNone(run_hook("pre-read", ev))

    def test_session_start_injects_rules(self):
        out = run_hook("session-start", {"session_id": "s", "source": "startup"})
        self.assertIn("[kompactor]", out["additionalContext"])
        self.assertIn("Lead with the answer", out["additionalContext"])

    def test_bad_input_fails_open(self):
        sys.stdin = io.StringIO("not json")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(hooks.run("post-bash"), 0)
        sys.stdin = sys.__stdin__
        self.assertEqual(buf.getvalue(), "")


class EstimateTests(unittest.TestCase):
    def test_replay_transcript(self):
        root = Path(tempfile.mkdtemp())
        proj = root / "proj"
        proj.mkdir()
        rows, usage = [], {"input_tokens": 10, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 5000,
                           "output_tokens": 200}
        rows.append({"type": "assistant", "message": {"id": "m1", "usage": usage, "content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "git log"}}]}})
        rows.append({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": GIT_LOG}]}})
        for i in range(2, 6):
            rows.append({"type": "assistant", "message": {"id": f"m{i}", "usage": usage, "content": []}})
        (proj / "s.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
        s = estimate.run(root)
        self.assertEqual(s["sessions"], 1)
        self.assertEqual(s["calls"], 5)
        self.assertGreater(s["saved_tool"], 0)
        # ingested at call index 1, so re-sent on 4 calls
        self.assertEqual(s["saved_billed"], s["saved_tool"] * 4)


PY_TRACE = """Traceback (most recent call last):
  File "/app/main.py", line 10, in <module>
    run()
  File "/app/.venv/lib/python3.12/site-packages/click/core.py", line 1157, in __call__
    return self.main(*args, **kwargs)
  File "/app/.venv/lib/python3.12/site-packages/click/core.py", line 1078, in main
    rv = self.invoke(ctx)
  File "/app/.venv/lib/python3.12/site-packages/click/core.py", line 783, in invoke
    return __callback(*args, **kwargs)
  File "/app/cli.py", line 22, in run
    load(path)
  File "/usr/lib/python3.12/json/__init__.py", line 293, in load
    return loads(fp.read())
  File "/usr/lib/python3.12/json/decoder.py", line 355, in raw_decode
    raise JSONDecodeError("Expecting value", s, err.value) from None
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)"""


class PresetAndLanguageTests(unittest.TestCase):
    def setUp(self):
        if config.path().exists():
            config.path().unlink()

    def test_presets_have_every_knob(self):
        for p in config.PRESETS.values():
            self.assertEqual(set(config.KNOBS) - set(p), set())
        self.assertEqual(set(config.KNOB_INFO), set(config.KNOBS))

    def test_overrides_and_project_preset(self):
        d = tempfile.mkdtemp()
        Path(d, "go.mod").write_text("module x")
        data = config.read_file()
        data["preset"] = 2
        data["overrides"] = {"bash_max_lines": 77}
        data["projects"][str(Path(d).resolve())] = {"preset": 5, "overrides": {}}
        config.write_file(data)
        g = config.load(tempfile.mkdtemp())
        self.assertEqual((g["preset"], g["bash_max_lines"], g["style"], g["code_style"]), (2, 77, "lite", "normal"))
        sub = Path(d, "pkg")
        sub.mkdir()
        p = config.load(str(sub))
        self.assertEqual((p["preset"], p["style"], p["languages"]), (5, "ultra", ["go"]))
        self.assertEqual(p["bash_max_lines"], 77)  # global override still applies

    def test_team_file_sits_between_your_global_and_project_settings(self):
        d = tempfile.mkdtemp()
        Path(d, "pyproject.toml").write_text("")
        Path(d, config.TEAM_FILE).write_text(json.dumps({"preset": 4, "overrides": {"never_compact": "terraform plan"}}))
        data = config.read_file()
        data["preset"], data["overrides"] = 2, {}
        data["projects"].pop(str(Path(d).resolve()), None)
        config.write_file(data)
        c = config.load(d)
        self.assertEqual((c["preset"], c["never_compact"]), (4, ["terraform plan"]))  # team beats your global level
        data["projects"][str(Path(d).resolve())] = {"preset": 1, "overrides": {}}
        config.write_file(data)
        self.assertEqual(config.load(d)["preset"], 1)  # your own choice for the project wins
        Path(d, config.TEAM_FILE).write_text("{not json")
        data["projects"].pop(str(Path(d).resolve()))
        config.write_file(data)
        self.assertEqual(config.load(d)["preset"], 2)  # a broken team file is ignored

    def test_detect_react(self):
        d = tempfile.mkdtemp()
        Path(d, "package.json").write_text('{"dependencies": {"react": "^18"}}')
        Path(d, "tsconfig.json").write_text("{}")
        self.assertEqual(langs.detect(d), ["typescript", "react"])

    def test_python_library_frames(self):
        out = filters.trim_frames(PY_TRACE.splitlines(), langs.library_frame_re(["python"]))
        text = "\n".join(out)
        self.assertIn("[… 3 library frames hidden …]", text)
        self.assertIn('File "/app/cli.py", line 22', text)
        self.assertIn("raw_decode", text)  # the frame that raised stays
        self.assertIn("JSONDecodeError: Expecting value", text)

    def test_go_and_node_frames(self):
        from kompactor import samples
        cfg = dict(config.PRESETS[3], languages=[])
        go = filters.compress("go test ./...", samples.SAMPLES[1]["text"], 1, opts=cfg)
        self.assertIn("cart.go:58", go)
        self.assertIn("library frames hidden", go)
        self.assertNotIn("go: downloading", go)
        vt = filters.compress("npx vitest run", samples.SAMPLES[2]["text"], 1, opts=cfg)
        self.assertIn("useCart.test.ts:27:32", vt)
        self.assertNotIn("node_modules/chai", vt)

    def test_diff_context(self):
        raw = "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1,9 +1,9 @@\n" + "".join(f" l{i}\n" for i in range(8)) + "-old\n+new\n l9"
        out = filters.compress("git diff", raw, opts={"diff_context": 1})
        self.assertIn(" ⋯ 7 unchanged", out)
        self.assertIn(" l7\n-old\n+new\n l9", out)

    def test_presets_monotonic_on_samples(self):
        sav = server.preset_savings()
        self.assertTrue(sav[1] <= sav[2] <= sav[3] <= sav[4] <= sav[5])
        self.assertLess(sav[1], sav[3])
        self.assertGreater(sav[3], 60)
        # Max quality never hides test results
        rows = {r["id"]: r for r in server.preview({k: config.PRESETS[1][k] for k in config.KNOBS}, [])}
        self.assertIn("test_endpoint_1 PASSED", rows["pytest"]["after"])


class DocsTests(unittest.TestCase):
    def test_versions_agree(self):
        root = Path(__file__).resolve().parent.parent
        import re as _re
        from kompactor import __version__
        py = _re.search(r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(), _re.M).group(1)
        plugin = json.loads((root / ".claude-plugin/plugin.json").read_text())["version"]
        vsix = json.loads((root / "vscode/package.json").read_text())["version"]
        self.assertEqual({__version__, py, plugin, vsix}, {__version__})  # scripts/bump_version.py keeps them in step
        for doc in ("README.md", "kompactor/static/usage.html"):
            self.assertIn(f"kompactor-{__version__}.vsix", (root / doc).read_text(), doc)

    def test_plugin_skill_matches_installer(self):
        root = Path(__file__).resolve().parent.parent
        self.assertEqual((root / "skills/kompactor/SKILL.md").read_text(), installer.SKILL.format(**installer.PLUGIN_SKILL))

    def test_no_arrow_glyphs_in_ui(self):
        root = Path(__file__).resolve().parent.parent
        for f in ("kompactor/ui.html", "kompactor/static/usage.html", "kompactor/hooks.py", "kompactor/cli.py"):
            text = (root / f).read_text()
            for glyph in ("→", "▶", "◀", "▸", "⚡"):
                self.assertNotIn(glyph, text, f"{glyph} in {f}")


class TurnAndSetupTests(unittest.TestCase):
    def test_stop_summarises_turn(self):
        ev = {"session_id": "turn1", "tool_input": {"command": "git log"}, "cwd": TMP,
              "tool_response": {"stdout": GIT_LOG, "stderr": "", "interrupted": False, "isImage": False}}
        run_hook("post-bash", ev)
        from kompactor import cli
        # Claude Code tells the status line how big the context is; Kompactor records that number
        sys.stdin = io.StringIO(json.dumps({"session_id": "turn1", "workspace": {"current_dir": TMP},
                                            "context_window": {"total_input_tokens": 21000}}))
        with redirect_stdout(io.StringIO()):
            cli.main(["statusline"])
        # ...and never reads the session transcript, even when the event names one
        transcript = Path(TMP, "t.jsonl")
        transcript.write_text(json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": 99999}}}) + "\n")
        sys.stdin = io.StringIO(json.dumps({"session_id": "turn1", "transcript_path": str(transcript), "cwd": TMP}))
        buf = io.StringIO()
        with redirect_stdout(buf):
            hooks.run("stop")
        sys.stdin = sys.__stdin__
        msg = json.loads(buf.getvalue())["systemMessage"]
        self.assertRegex(msg, r"Kompactor: −[\d.]+k? tokens this turn \([\d.]+k? › [\d.]+k?")
        self.assertIn("context ≈", msg)
        live = store.read_live()
        self.assertEqual(live["session"], "turn1")
        sys.stdin = io.StringIO(json.dumps({"session_id": "turn1", "workspace": {"current_dir": TMP}}))
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(["statusline"])
        sys.stdin = sys.__stdin__
        self.assertRegex(buf.getvalue(), r"Kompactor −[\d.]+k? · ctx −\d+% · last turn −[\d.]+k? · Balanced")
        self.assertEqual(live["session_totals"]["context"], 21000)
        # next turn with nothing compacted stays silent
        sys.stdin = io.StringIO(json.dumps({"session_id": "turn1", "cwd": TMP}))
        buf = io.StringIO()
        with redirect_stdout(buf):
            hooks.run("stop")
        sys.stdin = sys.__stdin__
        self.assertEqual(buf.getvalue(), "")

    def test_installer_roundtrip_keeps_other_hooks(self):
        home = tempfile.mkdtemp()
        old = os.environ.get("HOME")
        os.environ["HOME"] = home
        try:
            p = Path(home, ".claude", "settings.json")
            p.parent.mkdir()
            p.write_text(json.dumps({"model": "x", "statusLine": {"type": "command", "command": "mine"},
                                     "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "notify"}]}]}}))
            installer.install()
            d = json.loads(p.read_text())
            self.assertEqual(len(d["hooks"]["Stop"]), 2)
            skill = Path(home, ".claude", "skills", "kompactor", "SKILL.md")
            self.assertIn("config preset", skill.read_text())
            self.assertEqual(d["statusLine"]["command"], "mine")  # never replaced
            self.assertTrue(installer.status()["hooks_installed"])
            installer.install(uninstall=True)
            d = json.loads(p.read_text())
            self.assertEqual(d["hooks"], {"Stop": [{"hooks": [{"type": "command", "command": "notify"}]}]})
            self.assertTrue(p.with_suffix(".json.kompactor-backup").exists())
            self.assertFalse(skill.exists())
            # with the plugin enabled, only the status line is managed
            d["enabledPlugins"] = {"amarkum@kompactor": True}
            d.pop("statusLine")
            p.write_text(json.dumps(d))
            installer.install()
            d = json.loads(p.read_text())
            self.assertEqual(len(d["hooks"]["Stop"]), 1)
            self.assertIn("statusline", d["statusLine"]["command"])
            self.assertFalse(skill.exists())
        finally:
            os.environ["HOME"] = old

    def test_server_requires_token(self):
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        try:
            st = json.load(urllib.request.urlopen(base + "/api/state"))
            self.assertIn("presets", st)
            body = json.dumps({"preset": 4}).encode()
            req = urllib.request.Request(base + "/api/config", body, {"Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(req)
            req.add_header("X-Kompactor-Token", server.TOKEN)
            self.assertTrue(json.load(urllib.request.urlopen(req))["ok"])
            self.assertEqual(config.read_file()["preset"], 4)
        finally:
            httpd.shutdown()
            httpd.server_close()
            config.path().unlink()


class SourceTests(unittest.TestCase):
    """The dashboard shows teammates install commands for the public repo, or a fork named by KOMPACTOR_REPO."""

    def test_parse_source(self):
        self.assertEqual(installer.parse_source("https://someone@github.com/acme/kompactor.git"),
                         {"repo": "acme/kompactor", "clone": "https://github.com/acme/kompactor.git",
                          "marketplace": "acme/kompactor", "dir": "kompactor"})
        self.assertEqual(installer.parse_source("git@github.com:acme/kompactor.git")["marketplace"], "acme/kompactor")
        ssh = "ssh://git@gitlab.acme.dev/tools/kompactor.git"
        self.assertEqual(installer.parse_source(ssh)["clone"], ssh)
        self.assertEqual(installer.parse_source(""), {})

    def test_command_linked_onto_path_when_missing(self):
        from unittest import mock
        tmp = Path(tempfile.mkdtemp())
        on_path, off_path, shim = tmp / "bin", tmp / "elsewhere", tmp / "shim"
        on_path.mkdir(); off_path.mkdir()
        with mock.patch.object(installer, "shim_dir", return_value=shim):
            # only a writable folder that is already on PATH gets the link
            link = installer.link_on_path(path=str(on_path), dirs=(str(off_path), str(on_path)))
            self.assertEqual(link, str(on_path / "kompactor"))
            self.assertEqual(os.readlink(link), str(shim / "kompactor"))
            self.assertEqual(installer.link_on_path(path=str(on_path), dirs=(str(on_path),)), "")  # already there
            installer.unlink_from_path(dirs=(str(on_path),))
            self.assertFalse(Path(link).is_symlink())
            (on_path / "kompactor").write_text("someone else's")  # never replaced
            self.assertEqual(installer.link_on_path(path=str(on_path), dirs=(str(on_path),)), "")
            installer.unlink_from_path(dirs=(str(on_path),))
            self.assertTrue((on_path / "kompactor").exists())

    @unittest.skipIf(os.name == "nt", "uses a POSIX shell script as the fake editor")
    def test_editor_extension_added_once_and_removed(self):
        from unittest import mock
        from kompactor import __version__
        tmp = Path(tempfile.mkdtemp())
        ext, log, cli, vsix = tmp / "extensions", tmp / "log", tmp / "code", tmp / "k.vsix"
        ext.mkdir(); vsix.write_text("x")
        cli.write_text(f"""#!/bin/sh
echo "$@" >> '{log}'
[ "$1" = --install-extension ] && mkdir -p '{ext}/kompactor.kompactor-{__version__}'
[ "$1" = --uninstall-extension ] && rm -rf '{ext}'/kompactor.kompactor-*
exit 0
""")
        cli.chmod(0o755)
        fake = (("VS Code", "no-such-editor-command", str(cli), str(tmp)),)
        with mock.patch.object(installer, "EDITORS", fake), mock.patch.object(installer, "bundled_vsix", return_value=vsix):
            self.assertEqual(installer.install_editor_extension(), ["VS Code"])
            self.assertEqual(installer.install_editor_extension(), [])          # this version is already there
            self.assertEqual(installer.uninstall_editor_extension(), ["VS Code"])
            self.assertEqual(installer.uninstall_editor_extension(), [])        # nothing left to remove
        self.assertEqual(log.read_text().split("\n")[:2],
                         [f"--install-extension {vsix} --force", "--uninstall-extension kompactor.kompactor"])

    def test_source_defaults_to_the_public_repo(self):
        self.assertEqual(installer.source("")["marketplace"], "amarkum/kompactor")
        self.assertEqual(installer.source("acme/kompactor")["clone"], "https://github.com/acme/kompactor.git")  # a fork
        self.assertNotIn("someone@", json.dumps(installer.source("https://someone@git.acme.dev/tools/kompactor.git")))


if __name__ == "__main__":
    unittest.main()
