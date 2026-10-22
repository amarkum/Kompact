#!/usr/bin/env bash
# Build the VS Code extension (.vsix) with the Python package bundled inside,
# so VS Code users install one file and need nothing else but Python 3.9+.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf vscode/python
mkdir -p vscode/python/kompactor dist
cp kompactor/*.py kompactor/ui.html vscode/python/kompactor/
cp -r kompactor/static vscode/python/kompactor/   # fonts, logo and the usage guide the dashboard serves
cp LICENSE vscode/LICENSE
rm -f dist/kompactor-*.vsix   # dist/ holds the current release only; older ones stay in git history
cd vscode
npx --yes @vscode/vsce@3 package --no-dependencies --allow-missing-repository --out ../dist/
