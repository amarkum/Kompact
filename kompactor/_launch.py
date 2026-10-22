"""Path-independent entry point: `python /path/to/kompactor/_launch.py ...`.

Hooks call Kompactor through this file so they work the same whether Kompactor was
pip-installed, cloned, or bundled inside the VS Code extension."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if len(sys.argv) == 4 and sys.argv[1] == "shell":
    # Shell prefix (kompactor-shell): if Kompactor can't even load, run the command untouched.
    _shell, _full = sys.argv[2], sys.argv[3]
    try:
        from kompactor import shellwrap
    except BaseException:
        os.execvp(_shell, [_shell, "-c", _full])
    sys.exit(shellwrap.main([_shell, _full]))

from kompactor.cli import main  # noqa: E402

sys.exit(main())
