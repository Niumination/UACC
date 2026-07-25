"""
UACC Platform Abstraction Factory — auto-detects host OS and returns appropriate driver.
"""

from __future__ import annotations

import sys
from typing import Optional
from uacc.core.platform.base import BasePlatformDriver
from uacc.core.platform.windows import WindowsDriver
from uacc.core.platform.macos import MacOSDriver
from uacc.core.platform.linux import LinuxDriver

_driver_instance: Optional[BasePlatformDriver] = None


def get_platform_driver() -> BasePlatformDriver:
    """Return the platform-specific OS driver singleton."""
    global _driver_instance
    if _driver_instance is None:
        if sys.platform == "win32":
            _driver_instance = WindowsDriver()
        elif sys.platform == "darwin":
            _driver_instance = MacOSDriver()
        else:
            _driver_instance = LinuxDriver()
    return _driver_instance
