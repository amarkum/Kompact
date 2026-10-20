#!/usr/bin/env bash
# Build the VS Code extension (.vsix) with the Python package bundled inside,
# so VS Code users install one file and need nothing else but Python 3.9+.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf vscode/python
mkdir -p vscode/python/kompact dist
cp kompact/*.py kompact/ui.html vscode/python/kompact/
cp LICENSE vscode/LICENSE
cd vscode
npx --yes @vscode/vsce@3 package --no-dependencies --out ../dist/
