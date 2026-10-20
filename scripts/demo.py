"""Fill an isolated Kompact home with realistic demo sessions, to try the dashboard.

    KOMPACT_HOME=/tmp/kompact-demo python scripts/demo.py
    KOMPACT_HOME=/tmp/kompact-demo python -m kompact ui

Runs the real hooks on sample Python / Go / React outputs in three throwaway
projects; nothing touches your real ~/.kompact or ~/.claude.
"""

import io
import json
import os
import random
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

if not os.environ.get("KOMPACT_HOME"):
    sys.exit("Set KOMPACT_HOME to a scratch directory first (keeps demo data out of your real stats).")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kompact import hooks, samples  # noqa: E402

random.seed(7)
root = Path(tempfile.mkdtemp(prefix="kompact-demo-")) / "code"
projects = {
    "shop-api": ({"pyproject.toml": "[project]\nname='shop-api'\n"}, ["pytest", "gitlog", "gitdiff"]),
    "checkout-svc": ({"go.mod": "module example.com/checkout\n"}, ["gotest", "gitlog"]),
    "storefront": ({"package.json": json.dumps({"dependencies": {"react": "^18.3.0"}}), "tsconfig.json": "{}"},
                   ["vitest", "build", "gitdiff"]),
}
for name, (files, _) in projects.items():
    for f, body in files.items():
        (root / name).mkdir(parents=True, exist_ok=True)
        (root / name / f).write_text(body)
by_id = {s["id"]: s for s in samples.SAMPLES}


def hook(name, event):
    sys.stdin = io.StringIO(json.dumps(event))
    with redirect_stdout(io.StringIO()):
        hooks.run(name)
    sys.stdin = sys.__stdin__


def vary(text):
    """Make repeated samples differ a little so runs aren't identical."""
    lines = text.splitlines()
    extra = random.randint(0, len(lines) // 2)
    return "\n".join(lines + random.sample(lines, min(extra, len(lines))))


transcript = Path(os.environ["KOMPACT_HOME"]) / "demo-transcript.jsonl"
for n, (name, (_, kinds)) in enumerate(list(projects.items()) * 2):
    cwd = str(root / name)
    session, context = f"demo-{n}", random.randint(14000, 22000)
    for _turn in range(random.randint(5, 9)):
        for _ in range(random.choice([0, 1, 1, 2])):
            s = by_id[random.choice(kinds)]
            hook("post-bash", {"session_id": session, "cwd": cwd, "tool_input": {"command": s["cmd"]},
                               "tool_response": {"stdout": vary(s["text"]), "stderr": "", "interrupted": False,
                                                 "isImage": False}})
        context += random.randint(1200, 5200)
        transcript.write_text(json.dumps({"type": "assistant", "message": {"usage": {
            "input_tokens": 4, "cache_read_input_tokens": context, "cache_creation_input_tokens": 800}}}) + "\n")
        hook("stop", {"session_id": session, "cwd": cwd, "transcript_path": str(transcript)})
print(f"Demo data written to {os.environ['KOMPACT_HOME']}. Now run: python -m kompact ui")
