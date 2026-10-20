#!/bin/sh
# Kompact one-line installer (macOS / Linux):
#   curl -fsSL https://raw.githubusercontent.com/amarkum/Kompact/main/install.sh | sh
# Downloads Kompact to ~/.kompact/app (no pip needed), adds a `kompact` command,
# enables it for Claude Code (CLI + VS Code extension) and opens the dashboard.
set -e
REPO="${KOMPACT_REPO:-amarkum/Kompact}"
REF="${KOMPACT_REF:-main}"
DEST="${KOMPACT_APP:-$HOME/.kompact/app}"
BIN="${KOMPACT_BIN:-$HOME/.local/bin}"

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$(command -v "$c")"; break
  fi
done
[ -n "$PY" ] || { echo "Kompact needs Python 3.9 or newer (python3)." >&2; exit 1; }

# Run from a checkout (`git clone … && ./install.sh`)? Install that copy; otherwise download.
SRC=""
case "$0" in
  *install.sh) d="$(cd "$(dirname "$0")" && pwd)"; [ -f "$d/kompact/_launch.py" ] && SRC="$d" ;;
esac
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if [ -n "$SRC" ]; then
  echo "Installing Kompact from $SRC…"
  mkdir -p "$TMP/src" && cp -R "$SRC/." "$TMP/src/" && rm -rf "$TMP/src/.git"
else
  echo "Downloading Kompact ($REPO@$REF)…"
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

mkdir -p "$BIN"
cat > "$BIN/kompact" <<SHIM
#!/bin/sh
exec "$PY" "$DEST/kompact/_launch.py" "\$@"
SHIM
chmod +x "$BIN/kompact"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "Note: add $BIN to your PATH to use the \`kompact\` command." ;; esac

if [ "${KOMPACT_NO_UI:-}" = "1" ]; then
  "$PY" "$DEST/kompact/_launch.py" setup --no-ui
else
  "$PY" "$DEST/kompact/_launch.py" setup
fi
