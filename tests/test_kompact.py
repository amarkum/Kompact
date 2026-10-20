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
os.environ["KOMPACT_HOME"] = os.path.join(TMP, "home")

from kompact import estimate, filters, hooks, outline, store, tokens  # noqa: E402


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
        self.assertEqual(filters.classify("cd x && git log -n 3"), "generic")  # first command decides
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
        raw = "\x1b[32mok\x1b[0m\n" + "Downloading 10%\rDownloading 100%\n" + "same line\n" * 50 + "done"
        out = filters.compress("some-tool", raw)
        self.assertNotIn("\x1b", out)
        self.assertIn("same line  [x50]", out)
        self.assertNotIn("Downloading", out)

    def test_errors_survive_truncation(self):
        lines = [f"{chr(97 + i % 26) * 3}{chr(97 + i // 26 % 26)} entry" for i in range(1000)]
        lines[500] = "ERROR: the important thing broke"
        out = filters.compress("custom", "\n".join(lines), 1, stash_id=7)
        self.assertIn("ERROR: the important thing broke", out)
        self.assertIn("kompact show 7", out)

    def test_lockfile_diff_collapsed(self):
        raw = "diff --git a/package-lock.json b/package-lock.json\nindex 1..2\n--- a/x\n+++ b/x\n" + "+x\n" * 300 + \
              "diff --git a/src/a.ts b/src/a.ts\n--- a/src/a.ts\n+++ b/src/a.ts\n+real change\n"
        out = filters.compress("git diff", raw)
        self.assertIn("package-lock.json: generated/lock file diff, +300", out)
        self.assertIn("+real change", out)

    def test_grep_caps_per_file(self):
        raw = "\n".join(f"src/a.py:{i}:match {i}" for i in range(40)) + "\nsrc/b.py:1:other"
        out = filters.compress("grep -rn match", raw)
        self.assertIn("[src/a.py: +30 more matches]", out)
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
        Path(self.big).write_text("\n".join(f"def f{i}(x):\n    return x + {i}\n" for i in range(300)))
        self.small = os.path.join(self.dir, "small.py")
        Path(self.small).write_text("def f(x):\n    return x\n" * 40)

    def test_post_bash_compacts(self):
        ev = {"session_id": "t", "tool_input": {"command": "git log"},
              "tool_response": {"stdout": GIT_LOG, "stderr": "", "interrupted": False, "isImage": False}}
        res = run_hook("post-bash", ev)["updatedToolOutput"]
        self.assertEqual(set(res), {"stdout", "stderr", "interrupted", "isImage"})
        self.assertIn("Commit message number 3", res["stdout"])
        sid = int(res["stdout"].rsplit("kompact show ", 1)[1].rstrip("]"))
        self.assertEqual(store.get_stash(sid)[1], GIT_LOG)

    def test_post_bash_leaves_small_output(self):
        ev = {"tool_input": {"command": "ls"}, "tool_response": {"stdout": "a\nb", "stderr": ""}}
        self.assertIsNone(run_hook("post-bash", ev))

    def test_read_outline_then_allow(self):
        ev = {"session_id": "r1", "tool_input": {"file_path": self.big}}
        first = run_hook("pre-read", ev)
        self.assertEqual(first["permissionDecision"], "deny")
        self.assertIn("def f12(x):  [L37-38]", first["permissionDecisionReason"])
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
        self.assertIn("Token discipline", out["additionalContext"])

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


if __name__ == "__main__":
    unittest.main()
