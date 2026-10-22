"""Shell prefix (kompactor-shell) and oversized-output handling.

Claude Code skips PostToolUse when a command fails and saves outputs over ~30K
characters to a file; these tests pin down how Kompactor still compacts both."""

import io
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kompactor import filters, hooks, installer, shellwrap, tokens  # noqa: E402
installer.PATH_DIRS = ()  # never link `kompactor` into real PATH folders from tests

PASSING = "".join(f"tests/test_mod.py::test_case_{i} PASSED{' ' * 30}[{i // 5:3d}%]\n" for i in range(500))
FAILURE = ("=================================== FAILURES ===================================\n"
           "___________________________ test_async_view ___________________________\n"
           "E   RuntimeError: Install Flask with the 'async' extra\n"
           "tests/test_helpers.py:42: RuntimeError\n"
           "=========================== short test summary info ============================\n"
           "FAILED tests/test_helpers.py::test_async_view - RuntimeError: Install Flask\n"
           "================== 1 failed, 500 passed in 3.21s ==================\n")


def claude_string(cmd: str, cwd_file: str) -> str:
    """The string Claude Code passes to CLAUDE_CODE_SHELL_PREFIX (Claude Code 2.1)."""
    q = "'" + cmd.replace("'", "'\"'\"'") + "'"
    return (f"source /nonexistent/snapshot-bash-1.sh 2>/dev/null || true && {{ shopt -u extglob || setopt "
            f"NO_EXTENDED_GLOB; }} >/dev/null 2>&1 || true && eval {q} < /dev/null && pwd -P >| {cwd_file}")


class CommandParsingTests(unittest.TestCase):
    def test_user_command_roundtrips_quotes(self):
        for cmd in ["pytest -k 'a and not b' -q", "sh -c 'seq 1 12; exit 3'", 'go test -run "Test(A|B)" ./...',
                    "echo \"it's\" && npm test"]:
            self.assertEqual(shellwrap.user_command(claude_string(cmd, "/tmp/x")), cmd)
        self.assertEqual(shellwrap.user_command("ls -la"), "")  # unknown format: leave it alone

    def test_wrappable(self):
        yes = ["pytest tests -v", ".venv/bin/pytest -q", "go test ./... 2>&1", "cd app && npm test", "npx tsc --noEmit",
               "npm run build", "pnpm lint", "uv run pytest -x", "python -m mypy src", "cargo clippy", "make",
               "docker build -t x .", "go vet ./... && go test ./...", "npm ci", "vitest", "./gradlew test"]
        no = ["npm start", "npm run dev", "go run ./cmd/server", "pytest | tail -5", "jest --watch", "tsc -w",
              "docker compose up", "vite", "make run", "cargo run", "ls -la", "git status", "cat x.py", "npm test &",
              "npm run build && npm start", "python app.py", "yarn dev", "uvicorn app:app", "cypress open",
              "playwright test --ui", "echo hi"]
        self.assertEqual([c for c in yes if not filters.wrappable(c)], [])
        self.assertEqual([c for c in no if filters.wrappable(c)], [])


class ShellPrefixTests(unittest.TestCase):
    """Run the real POSIX shim exactly as Claude Code would."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.home = self.dir / "kompactor-home"
        self.home.mkdir()
        self.shim = self.dir / "kompactor-shell"
        self.shim.write_text(installer.SHELL_PREFIX.format(py=shlex.quote(sys.executable), script=shlex.quote(str(ROOT / "kompactor" / "_launch.py"))))
        self.shim.chmod(0o755)
        bindir = self.dir / "bin"
        bindir.mkdir()
        (self.dir / "out.txt").write_text(PASSING + FAILURE)
        fake = bindir / "pytest"  # prints a long passing run, then a failure; exits 1
        fake.write_text(f"#!/bin/sh\ncat '{self.dir / 'out.txt'}'\necho 'warning on stderr' >&2\nexit 1\n")
        fake.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", KOMPACTOR_HOME=str(self.home),
                        CLAUDE_CODE_SESSION_ID="shell-test")

    def run_shim(self, cmd, **env):
        return subprocess.run([str(self.shim), claude_string(cmd, str(self.dir / "cwd"))], capture_output=True,
                              text=True, env={**self.env, **env}, cwd=self.dir, timeout=60)

    def test_failing_tests_are_compacted_and_keep_exit_code(self):
        r = self.run_shim("pytest tests -v")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAILED tests/test_helpers.py::test_async_view", r.stdout)
        self.assertIn("E   RuntimeError: Install Flask with the 'async' extra", r.stdout)
        self.assertIn("warning on stderr", r.stdout)  # stderr is merged, as Claude Code does
        self.assertNotIn("test_case_7 PASSED", r.stdout)
        self.assertIn("[kompactor: ", r.stdout)
        self.assertLess(tokens.count(r.stdout), tokens.count(PASSING) // 20)
        # the ledger counts only what Claude Code would really have shown (~10K chars of a failed run)
        db = sqlite3.connect(self.home / "kompactor.db")
        self.addCleanup(db.close)
        raw, kept, session = db.execute("SELECT raw_tokens, kept_tokens, session FROM events").fetchone()
        self.assertEqual(session, "shell-test")
        self.assertLess(raw, tokens.count(PASSING + FAILURE) // 2)
        self.assertGreater(raw, kept)
        sid = int(r.stdout.rsplit(" show ", 1)[1].split("]")[0])
        stash = db.execute("SELECT output FROM stash WHERE id=?", (sid,)).fetchone()[0]
        self.assertIn("test_case_7 PASSED", stash)

    def test_other_commands_run_untouched(self):
        r = self.run_shim("printf 'a\\nb\\n'; echo err >&2; exit 7")
        self.assertEqual((r.returncode, r.stdout, r.stderr), (7, "a\nb\n", "err\n"))
        r = self.run_shim("pytest -q | tail -2")  # already shaped by a pipe
        self.assertEqual(r.stdout, "FAILED tests/test_helpers.py::test_async_view - RuntimeError: Install Flask\n"
                                   "================== 1 failed, 500 passed in 3.21s ==================\n")
        self.assertEqual((self.dir / "cwd").read_text().strip(), str(self.dir.resolve()))  # cwd tracking intact

    def test_switches_and_fallbacks(self):
        for env in ({"KOMPACTOR_RAW": "1"}, {"KOMPACTOR_BASH_WRAP": "0"}, {"KOMPACTOR_BASH": "0"}):
            r = self.run_shim("pytest", **env)
            self.assertEqual(r.returncode, 1)
            self.assertIn("test_case_7 PASSED", r.stdout, env)
        # Kompactor gone (plugin removed): the shim still runs every command
        self.shim.write_text(installer.SHELL_PREFIX.format(py=shlex.quote(sys.executable), script=shlex.quote(str(self.dir / "missing.py"))))
        r = self.run_shim("pytest")
        self.assertEqual(r.returncode, 1)
        self.assertIn("test_case_7 PASSED", r.stdout)

    def test_inline_raw_and_odd_install_paths(self):
        r = self.run_shim("KOMPACTOR_RAW=1 pytest")  # the documented per-command opt-out
        self.assertIn("test_case_7 PASSED", r.stdout)
        odd = self.dir / 'we"ird $HOME dir'  # quotes, spaces and $ in the install path
        odd.mkdir()
        (odd / "kompactor").symlink_to(ROOT / "kompactor")
        self.shim.write_text(installer.SHELL_PREFIX.format(py=shlex.quote(sys.executable),
                                                           script=shlex.quote(str(odd / "kompactor" / "_launch.py"))))
        r = self.run_shim("pytest")
        self.assertEqual(r.returncode, 1)
        self.assertIn("[kompactor: ", r.stdout)
        self.assertNotIn("test_case_7 PASSED", r.stdout)

    def test_never_compact_is_respected(self):
        cfg_file = self.home / "config.json"
        cfg_file.write_text(json.dumps({"preset": 3, "overrides": {"never_compact": ["pytest"]}}))
        r = self.run_shim("pytest")
        self.assertIn("test_case_7 PASSED", r.stdout)


def run_hook(name, event):
    sys.stdin = io.StringIO(json.dumps(event))
    buf = io.StringIO()
    with redirect_stdout(buf):
        hooks.run(name)
    sys.stdin = sys.__stdin__
    out = buf.getvalue()
    return json.loads(out)["hookSpecificOutput"] if out else None


class PersistedOutputTests(unittest.TestCase):
    """Outputs over ~30K chars: Claude Code gives hooks only the head and shows Claude a 2 KB preview."""

    def event(self, cmd, text):
        path = Path(tempfile.mkdtemp(), "tool-result.txt")
        path.write_text(text)
        return {"session_id": "persist", "tool_input": {"command": cmd},
                "tool_response": {"stdout": text[:30000], "stderr": "", "interrupted": False, "isImage": False,
                                  "noOutputExpected": False, "persistedOutputPath": str(path),
                                  "persistedOutputSize": len(text)}}

    def test_whole_output_is_compacted_and_preview_dropped(self):
        res = run_hook("post-bash", self.event("go test -v ./...", PASSING + FAILURE))["updatedToolOutput"]
        self.assertNotIn("persistedOutputPath", res)  # otherwise Claude Code shows its preview instead
        self.assertIn("FAILED tests/test_helpers.py::test_async_view", res["stdout"])  # only in the saved file
        self.assertLess(len(res["stdout"]), hooks.PERSIST_LIMIT + 200)

    def test_huge_incompressible_output_fits(self):
        text = "".join(f"row {i} " + "x" * 200 + "\n" for i in range(5000))
        res = run_hook("post-bash", self.event("python dump.py", text))["updatedToolOutput"]
        self.assertLess(len(res["stdout"]), hooks.PERSIST_LIMIT + 200)
        self.assertIn("row 0 ", res["stdout"])
        self.assertIn("row 4999 ", res["stdout"])

    def test_file_views_keep_claude_codes_preview(self):
        self.assertIsNone(run_hook("post-bash", self.event("cat big.log", "line\n" * 40000)))


class PlainRuleTests(unittest.TestCase):
    """"Don't pipe through tail" pays off only when failing commands are compacted: measured +33% tokens
    without the shell prefix, -9% with it."""

    def test_plain_rule_only_with_active_prefix(self):
        cfg = {"bash": True, "bash_plain": True, "bash_wrap": True, "style": "lite", "code_style": "lean"}
        prefix = Path(tempfile.mkdtemp(), "kompactor-shell")
        prefix.write_text("#!/bin/sh\n")
        old = os.environ.pop(installer.PREFIX_ENV, None)
        try:
            self.assertNotIn("Run tests, builds and linters plainly", hooks._rules(cfg))
            os.environ[installer.PREFIX_ENV] = str(prefix)
            self.assertIn("Run tests, builds and linters plainly", hooks._rules(cfg))
            self.assertNotIn("Run tests, builds and linters plainly", hooks._rules({**cfg, "bash_wrap": False}))
            os.environ[installer.PREFIX_ENV] = "/opt/audit/log.sh"  # someone else's prefix
            self.assertNotIn("Run tests, builds and linters plainly", hooks._rules(cfg))
        finally:
            os.environ.pop(installer.PREFIX_ENV, None)
            if old is not None:
                os.environ[installer.PREFIX_ENV] = old


class InstallerPrefixTests(unittest.TestCase):
    def test_upgrade_from_kompact_replaces_old_entries_only(self):
        home = tempfile.mkdtemp()
        old = os.environ.get("HOME")
        os.environ["HOME"] = home
        try:
            p = Path(home, ".claude", "settings.json")
            p.parent.mkdir()
            legacy = '"/usr/bin/python3" "/opt/Kompact/kompact/_launch.py"'
            other = {"hooks": [{"type": "command", "command": "kompact proxy --hook"}]}  # an unrelated tool
            p.write_text(json.dumps({
                "statusLine": {"type": "command", "command": f"{legacy} statusline"},
                "env": {installer.PREFIX_ENV: f"{home}/.kompact/bin/kompact-shell"},
                "hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [
                    {"type": "command", "command": f"{legacy} hook post-bash"}]}, other]}}))
            skill = Path(home, ".claude", "skills", "kompact", "SKILL.md")
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: kompact\n---\nKompact token saver.\n")
            installer.install()
            d = json.loads(p.read_text())
            cmds = [h["command"] for e in d["hooks"]["PostToolUse"] for h in e["hooks"]]
            self.assertNotIn(f"{legacy} hook post-bash", cmds)
            self.assertIn("kompact proxy --hook", cmds)  # someone else's hook is kept
            self.assertEqual(sum("hook post-bash" in c for c in cmds), 1)
            self.assertIn("kompactor", d["statusLine"]["command"])
            self.assertTrue(d["env"][installer.PREFIX_ENV].endswith("kompactor-shell"))
            self.assertFalse(skill.exists())
            self.assertTrue(Path(home, ".claude", "skills", "kompactor", "SKILL.md").exists())
        finally:
            os.environ["HOME"] = old

    def test_session_start_keeps_the_launcher_current(self):
        home = tempfile.mkdtemp()
        old = os.environ.get("HOME")
        os.environ["HOME"] = home
        try:
            shim = installer.write_shim(only_if_changed=True)
            self.assertTrue(os.access(shim, os.X_OK))
            self.assertEqual(installer.cli_name() if not shutil.which("kompactor") else "~/.kompactor/bin/kompactor",
                             "~/.kompactor/bin/kompactor")
            before = shim.stat().st_mtime_ns
            installer.write_shim(only_if_changed=True)  # unchanged: not rewritten
            self.assertEqual(shim.stat().st_mtime_ns, before)
            shim.write_text("#!/bin/sh\nexec /old/python /old/kompactor/_launch.py \"$@\"\n")  # stale copy
            installer.write_shim(only_if_changed=True)
            self.assertIn(str(ROOT / "kompactor" / "_launch.py"), shim.read_text())
        finally:
            os.environ["HOME"] = old

    def test_prefix_set_kept_foreign_and_removed(self):
        home = tempfile.mkdtemp()
        old = os.environ.get("HOME")
        os.environ["HOME"] = home
        try:
            p = Path(home, ".claude", "settings.json")
            p.parent.mkdir()
            p.write_text(json.dumps({"env": {"FOO": "1"}}))
            installer.install()
            d = json.loads(p.read_text())
            prefix = d["env"][installer.PREFIX_ENV]
            self.assertTrue(prefix.endswith("kompactor-shell"))
            self.assertTrue(os.access(prefix, os.X_OK))
            self.assertEqual(installer.status()["shell_prefix"], "kompactor")
            installer.install(uninstall=True)
            self.assertEqual(json.loads(p.read_text())["env"], {"FOO": "1"})
            p.write_text(json.dumps({"env": {installer.PREFIX_ENV: "/opt/audit/log.sh"}}))
            installer.install()
            self.assertEqual(json.loads(p.read_text())["env"][installer.PREFIX_ENV], "/opt/audit/log.sh")
            self.assertEqual(installer.status()["shell_prefix"], "other")
            installer.install(uninstall=True)
            self.assertEqual(json.loads(p.read_text())["env"][installer.PREFIX_ENV], "/opt/audit/log.sh")
        finally:
            os.environ["HOME"] = old


if __name__ == "__main__":
    unittest.main()
