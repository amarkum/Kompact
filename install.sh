#!/bin/sh
# Kompactor installer (macOS / Linux), run from a clone:
#   git clone https://github.com/amarkum/kompactor.git && ./kompactor/install.sh
# Without a clone, use PyPI instead: pipx install kompactor && kompactor setup
# Copies Kompactor to ~/.kompactor/app (no pip needed), adds a `kompactor` command,
# enables it for Claude Code (CLI + VS Code extension) and opens the dashboard.
set -e
DEST="${KOMPACTOR_APP:-$HOME/.kompactor/app}"
BIN="${KOMPACTOR_BIN:-$HOME/.local/bin}"

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$(command -v "$c")"; break
  fi
done
[ -n "$PY" ] || { echo "Kompactor needs Python 3.9 or newer (python3)." >&2; exit 1; }

# Installs the copy this script sits in.
SRC=""
case "$0" in
  *install.sh) d="$(cd "$(dirname "$0")" && pwd)"; [ -f "$d/kompactor/_launch.py" ] && SRC="$d" ;;
esac
[ -n "$SRC" ] || { echo "Run ./install.sh from a clone of Kompactor, or install from PyPI: pipx install kompactor" >&2; exit 1; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "Installing Kompactor from $SRC…"
mkdir -p "$TMP/src" && cp -R "$SRC/." "$TMP/src/" && rm -rf "$TMP/src/.git"
[ "$(cd "$DEST" 2>/dev/null && pwd)" = "$SRC" ] && { echo "Run install.sh from a clone outside $DEST." >&2; exit 1; }
rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
mv "$TMP"/*/ "$DEST"

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
