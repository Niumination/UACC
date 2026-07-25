"""
Base Platform Driver Interface.

Defines abstract interface for OS-level accessibility, window management,
and input control across Windows, macOS, and Linux.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class WindowInfo:
    """Information about an application window."""
    hwnd_or_id: Any
    title: str
    process_name: str
    process_id: int
    bounds: Tuple[int, int, int, int]  # (left, top, right, bottom)
    is_active: bool = False
    is_minimized: bool = False
    is_maximized: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.hwnd_or_id,
            "title": self.title,
            "process_name": self.process_name,
            "pid": self.process_id,
            "bounds": {
                "left": self.bounds[0],
                "top": self.bounds[1],
                "right": self.bounds[2],
                "bottom": self.bounds[3],
            },
            "is_active": self.is_active,
            "is_minimized": self.is_minimized,
            "is_maximized": self.is_maximized,
        }


class BasePlatformDriver(ABC):
    """Abstract base class for platform-specific OS interactions."""

    @abstractmethod
    def get_ui_tree(self, max_depth: int = 10) -> List[Any]:
        """Extract structured UI elements from accessibility API."""
        pass

    @abstractmethod
    def list_windows(self) -> List[WindowInfo]:
        """List all top-level application windows."""
        pass

    @abstractmethod
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get the currently focused active window."""
        pass

    @abstractmethod
    def focus_window(self, title_substring: str) -> Dict[str, Any]:
        """Focus a window by title substring."""
        pass

    @abstractmethod
    def launch_app(self, name_or_path: str, arguments: str = "", wait_ms: int = 2000) -> Dict[str, Any]:
        """Launch an application process."""
        pass
