"""Set Kompactor's version everywhere it lives, for a release.

    python scripts/bump_version.py 0.4.1

Teammates' plugins update only when .claude-plugin/plugin.json's version changes, so bump it whenever you
want everyone to get what's on the default branch. Also updates the Python package and the VS Code extension;
rebuild the .vsix afterwards with scripts/build-vsix.sh.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(version: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        sys.exit("version must look like 1.2.3")
    for rel, pattern, repl in (("pyproject.toml", r'^version = "[^"]+"', f'version = "{version}"'),
                               ("kompactor/__init__.py", r'^__version__ = "[^"]+"', f'__version__ = "{version}"')):
        p = ROOT / rel
        text, n = re.subn(pattern, repl, p.read_text(), count=1, flags=re.M)
        if not n:
            sys.exit(f"no version found in {rel}")
        p.write_text(text)
    for rel in (".claude-plugin/plugin.json", "vscode/package.json"):
        p = ROOT / rel
        d = json.loads(p.read_text())
        d["version"] = version
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    print(f"version {version}: pyproject.toml, kompactor/__init__.py, plugin.json, vscode/package.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
