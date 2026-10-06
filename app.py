"""CVForge Streamlit Cloud entrypoint.

This root entrypoint is intentionally tiny so Streamlit Community Cloud can be
configured to a single stable file while the actual UI remains under
streamlit_app/app.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent / "streamlit_app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from app import *  # noqa: F401,F403,E402
