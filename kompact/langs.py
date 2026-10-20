"""Language profiles and project auto-detection.

A profile tells Kompact which files are source (outline-first reads), which
are generated (never worth reading in full), which stack frames are library
noise, and which lock files to collapse in diffs.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

PROFILES = {
    "python": {
        "label": "Python",
        "markers": ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile", "poetry.lock", "uv.lock"],
        "ext": [".py", ".pyi"],
        "generated": [r"_pb2(_grpc)?\.pyi?$", r"(^|/)migrations/\d+_\w+\.py$"],
        "library_frames": [r"site-packages/", r"dist-packages/", r"/lib/python\d", r"<frozen ", r"\.venv/"],
        "lockfiles": ["poetry.lock", "uv.lock", "Pipfile.lock", "pdm.lock"],
    },
    "go": {
        "label": "Go",
        "markers": ["go.mod", "go.work"],
        "ext": [".go"],
        "generated": [r"\.pb\.go$", r"_gen\.go$", r"(^|/)zz_generated[^/]*\.go$", r"_string\.go$", r"(^|/)mock_[^/]+\.go$"],
        "library_frames": [r"/usr/(local/)?go/src/", r"(^|\s)runtime/", r"/go/pkg/mod/", r"GOROOT", r"/goroot/"],
        "lockfiles": ["go.sum"],
    },
    "typescript": {
        "label": "TypeScript / JavaScript",
        "markers": ["tsconfig.json", "package.json"],
        "ext": [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"],
        "generated": [r"\.d\.ts$", r"\.min\.(js|css)$", r"(^|/)(dist|build|\.next|out|coverage)/", r"\.generated\.\w+$",
                      r"(^|/)__generated__/", r"\.map$"],
        "library_frames": [r"node_modules/", r"node:internal", r"\(internal/", r"webpack/bootstrap", r"<anonymous>"],
        "lockfiles": ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "npm-shrinkwrap.json"],
    },
    "react": {
        "label": "React",
        "markers": [],  # detected from package.json dependencies
        "ext": [".tsx", ".jsx"],
        "generated": [r"(^|/)\.next/", r"(^|/)storybook-static/"],
        "library_frames": [r"react-dom", r"scheduler/", r"next/dist/"],
        "lockfiles": [],
    },
}


@lru_cache(maxsize=64)
def detect(root: str):
    """Languages used by the project at `root`, most specific first."""
    if not root:
        return []
    r = Path(root)
    found = []
    for name, prof in PROFILES.items():
        if any((r / m).exists() for m in prof["markers"]):
            found.append(name)
    pkg = r / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {}), **data.get("peerDependencies", {})}
            if any(d in deps for d in ("react", "next", "react-native", "preact")):
                found.append("react")
        except (OSError, ValueError):
            pass
    if not found:  # no markers: sample the top two levels for source files
        counts = {}
        for p in list(r.glob("*")) + list(r.glob("*/*")):
            for name, prof in PROFILES.items():
                if p.suffix in prof["ext"]:
                    counts[name] = counts.get(name, 0) + 1
        found = [n for n, _ in sorted(counts.items(), key=lambda x: -x[1])[:2]]
    return found


def merged(languages, key: str):
    """Union of a profile field across languages (all profiles if none detected)."""
    names = languages or list(PROFILES)
    out = []
    for n in names:
        for v in PROFILES.get(n, {}).get(key, []):
            if v not in out:
                out.append(v)
    return out


def library_frame_re(languages):
    pats = merged(languages, "library_frames")
    return re.compile("|".join(pats)) if pats else None


def generated_re(languages):
    pats = merged(languages, "generated")
    return re.compile("|".join(pats)) if pats else None


def lockfile_re(languages):
    names = merged(list(PROFILES), "lockfiles")  # lock files are unambiguous; always collapse them all
    return re.compile(r"(^|/)(" + "|".join(re.escape(n) for n in names) + r")$|\.min\.(js|css)$|\.map$")
