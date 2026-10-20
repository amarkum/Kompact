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

echo "Downloading Kompact ($REPO@$REF)…"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$REF" | tar -xz -C "$TMP"
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
