#!/bin/sh
# Kompactor installer (macOS / Linux). From a clone of your team's repo:
#   ./install.sh
# Or without a clone (set the repo; a token is needed while the repo is private):
#   KOMPACTOR_REPO=your-org/kompactor GITHUB_TOKEN=... sh install.sh
# Copies Kompactor to ~/.kompactor/app (no pip needed), adds a `kompactor` command,
# enables it for Claude Code (CLI + VS Code extension) and opens the dashboard.
set -e
REPO="${KOMPACTOR_REPO:-}"
REF="${KOMPACTOR_REF:-main}"
DEST="${KOMPACTOR_APP:-$HOME/.kompactor/app}"
BIN="${KOMPACTOR_BIN:-$HOME/.local/bin}"

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$(command -v "$c")"; break
  fi
done
[ -n "$PY" ] || { echo "Kompactor needs Python 3.9 or newer (python3)." >&2; exit 1; }

# Run from a checkout (`git clone … && ./install.sh`)? Install that copy; otherwise download.
SRC=""
case "$0" in
  *install.sh) d="$(cd "$(dirname "$0")" && pwd)"; [ -f "$d/kompactor/_launch.py" ] && SRC="$d" ;;
esac
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ORIGIN=""
if [ -n "$SRC" ]; then
  ORIGIN="$(git -C "$SRC" remote get-url origin 2>/dev/null || true)"
  echo "Installing Kompactor from $SRC…"
  mkdir -p "$TMP/src" && cp -R "$SRC/." "$TMP/src/" && rm -rf "$TMP/src/.git"
else
  [ -n "$REPO" ] || { echo "Run ./install.sh from a clone of your Kompactor repo, or set KOMPACTOR_REPO=your-org/kompactor." >&2; exit 1; }
  ORIGIN="https://github.com/$REPO"
  echo "Downloading Kompactor ($REPO@$REF)…"
  if [ -n "${GITHUB_TOKEN:-}" ]; then  # private repo: use the API with a token
    curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" "https://api.github.com/repos/$REPO/tarball/$REF" | tar -xz -C "$TMP"
  else
    curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$REF" | tar -xz -C "$TMP"
  fi
fi
[ "$(cd "$DEST" 2>/dev/null && pwd)" = "$SRC" ] && { echo "Run install.sh from a clone outside $DEST." >&2; exit 1; }
rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
mv "$TMP"/*/ "$DEST"
# so the dashboard can show teammates the exact install commands for your repo (credentials stripped)
[ -n "$ORIGIN" ] && printf '%s\n' "$ORIGIN" | sed -E 's#^(https?://)[^/@]*@#\1#' > "$DEST/.kompactor-source"

mkdir -p "$BIN"
cat > "$BIN/kompactor" <<SHIM
#!/bin/sh
exec "$PY" "$DEST/kompactor/_launch.py" "\$@"
SHIM
chmod +x "$BIN/kompactor"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "Note: add $BIN to your PATH to use the \`kompactor\` command." ;; esac

if [ "${KOMPACTOR_NO_UI:-}" = "1" ]; then
  "$PY" "$DEST/kompactor/_launch.py" setup --no-ui
else
  "$PY" "$DEST/kompactor/_launch.py" setup
fi
