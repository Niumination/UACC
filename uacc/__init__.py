"""
UACC — Universal AI Computer Control
Let any LLM control a computer with pixel-precise UI interactions.

When running inside an agent-hosted environment (e.g. Hermes) that injects
its own venv into sys.path, incompatible binary wheels (pydantic_core,
PIL._imaging, numpy C-extensions) can collide with UACC's own dependencies.

This module strips the host agent's site-packages from sys.path so that
UACC's pip-installed dependencies resolve correctly.
"""

__version__ = "1.1.0"

import sys as _sys

# Host-agent venv filtering disabled — UACC is intentionally installed
# in the Hermes venv. If binary wheel conflicts arise, handle them per-package.
# _sys.path = [p for p in _sys.path if not ("hermes" in p.lower() and "site-packages" in p.lower())]

# Enable Windows Per-Monitor DPI awareness so screenshot dimensions match cursor coordinate systems 1:1
if _sys.platform == "win32":
    try:
        import ctypes as _ctypes
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        _ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            _ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from uacc.config import config  # noqa: F401

