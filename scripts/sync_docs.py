"""Copy the in-app guide to docs/usage.html with paths that work from the repo.

    python scripts/sync_docs.py          # write docs/usage.html
    python scripts/sync_docs.py --check  # exit 1 if it is out of date
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def render() -> str:
    html = (ROOT / "kompact/static/usage.html").read_text()
    return html.replace('url("fonts/', 'url("../kompact/static/fonts/').replace('href="logo-mark.svg"',
                                                                              'href="../kompact/static/logo-mark.svg"')


if __name__ == "__main__":
    target = ROOT / "docs/usage.html"
    if "--check" in sys.argv:
        sys.exit(0 if target.exists() and target.read_text() == render() else 1)
    target.write_text(render())
    print(f"wrote {target}")
