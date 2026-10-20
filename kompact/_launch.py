"""Path-independent entry point: `python /path/to/kompact/_launch.py ...`.

Hooks call Kompact through this file so they work the same whether Kompact was
pip-installed, cloned, or bundled inside the VS Code extension."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kompact.cli import main  # noqa: E402

sys.exit(main())
