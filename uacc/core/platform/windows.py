"""
Windows Platform Driver — pywinauto + Win32 UI Automation implementation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uacc.core.platform.base import BasePlatformDriver, WindowInfo

logger = logging.getLogger(__name__)


class WindowsDriver(BasePlatformDriver):
    """Windows implementation using pywinauto and Win32 APIs."""

    def get_ui_tree(self, max_depth: int = 10) -> List[Any]:
        from uacc.core.accessibility import get_ui_tree as _get_tree
        return _get_tree(max_depth=max_depth)

    def list_windows(self) -> List[WindowInfo]:
        from uacc.core.window_manager import list_windows as _list_win
        wins = _list_win()
        result = []
        for w in wins:
            result.append(WindowInfo(
                hwnd_or_id=w.process_id or id(w),
                title=w.title,
                process_name=w.process_name,
                process_id=w.process_id,
                bounds=w.bounds,
                is_active=w.is_focused,
                is_minimized=w.is_minimized,
                is_maximized=w.is_maximized,
            ))
        return result

    def get_active_window(self) -> Optional[WindowInfo]:
        from uacc.core.window_manager import get_active_window as _get_act
        w = _get_act()
        if not w:
            return None
        return WindowInfo(
            hwnd_or_id=w.hwnd,
            title=w.title,
            process_name=w.process_name,
            process_id=w.process_id,
            bounds=w.bounds,
            is_active=True,
            is_minimized=w.is_minimized,
            is_maximized=w.is_maximized,
        )

    def focus_window(self, title_substring: str) -> Dict[str, Any]:
        from uacc.core.window_manager import focus_window as _focus
        return _focus(title_substring)

    def launch_app(self, name_or_path: str, arguments: str = "", wait_ms: int = 2000) -> Dict[str, Any]:
        from uacc.core.window_manager import launch_application as _launch
        return _launch(name_or_path, arguments=arguments, wait_ms=wait_ms)
