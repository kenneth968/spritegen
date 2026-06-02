"""Desktop application entry point for spritegen.

Launches the PySide6 GUI application.

Usage:
    python -m spritegen.desktop
    or
    python src/spritegen/desktop.py
"""

import sys
from pathlib import Path

_root = Path(__file__).parent.parent.parent
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


def main() -> None:
    from spritegen.ui.main_window import main as run_app

    run_app()

if __name__ == "__main__":
    main()
