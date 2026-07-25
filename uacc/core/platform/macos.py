"""
macOS Platform Driver — AppleScript + AXUIElement (pyobjc Quartz).

Window management uses AppleScript for reliable bounds/PID.
Accessibility tree uses the macOS Accessibility API via pyobjc.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from uacc.core.platform.base import BasePlatformDriver, WindowInfo

logger = logging.getLogger(__name__)


def _run_applescript(script: str) -> str:
    """Execute AppleScript via osascript CLI."""
    try:
        res = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return res.stdout.strip()
    except Exception as exc:
        logger.warning("AppleScript execution failed: %s", exc)
        return ""


def _parse_bounds(raw: str) -> Tuple[int, int, int, int]:
    """Parse AppleScript bounds tuple like ``12, 34, 800, 600``."""
    try:
        parts = [int(p.strip()) for p in raw.replace(", ", ",").split(",")]
        if len(parts) == 4:
            return (parts[0], parts[1], parts[2], parts[3])
    except Exception:
        pass
    return (0, 0, 1920, 1080)


_RECORD_DELIM = "|||"


class MacOSDriver(BasePlatformDriver):
    """macOS implementation using AppleScript (windows) and AXUIElement (UI tree)."""

    def get_ui_tree(self, max_depth: int = 10) -> List[Any]:
        from uacc.core.accessibility import get_ui_tree as _get_tree
        return _get_tree(max_depth=max_depth)

    def list_windows(self) -> List[WindowInfo]:
        script = """
        set output to ""
        tell application "System Events"
            repeat with p in (every application process whose visible is true)
                set pName to name of p
                try
                    set pId to unix id of p
                on error
                    set pId to 0
                end try
                repeat with w in (every window of p)
                    set wTitle to title of w
                    if wTitle is missing value then set wTitle to ""
                    try
                        set {x, y} to position of w
                        set {wW, wH} to size of w
                        set b to (x as text) & "," & (y as text) & "," & ((x + wW) as text) & "," & ((y + wH) as text)
                    on error
                        set b to "0,0,1920,1080"
                    end try
                    set output to output & pName & "|||" & wTitle & "|||" & b & "|||" & pId & linefeed
                end repeat
            end repeat
        end tell
        return output
        """
        raw = _run_applescript(script)
        results: List[WindowInfo] = []
        if not raw:
            return results

        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(_RECORD_DELIM)
            if len(parts) >= 3:
                pname = parts[0]
                title = parts[1]
                bounds = _parse_bounds(parts[2])
                pid = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
                idx = len(results)
                results.append(WindowInfo(
                    hwnd_or_id=pid or (idx + 1),
                    title=title or pname,
                    process_name=pname,
                    process_id=pid,
                    bounds=bounds,
                    is_active=(idx == 0),
                ))
        return results

    def get_active_window(self) -> Optional[WindowInfo]:
        script = """
        tell application "System Events"
            set activeApp to first application process whose frontmost is true
            set pName to name of activeApp
            try
                set pId to unix id of activeApp
            on error
                set pId to 0
            end try
            try
                set wTitle to title of window 1 of activeApp
                if wTitle is missing value then set wTitle to pName
            on error
                set wTitle to pName
            end try
            try
                set {x, y} to position of window 1 of activeApp
                set {wW, wH} to size of window 1 of activeApp
                set b to (x as text) & "," & (y as text) & "," & ((x + wW) as text) & "," & ((y + wH) as text)
            on error
                set b to "0,0,1920,1080"
            end try
            return pName & "|||" & wTitle & "|||" & b & "|||" & pId
        end tell
        """
        raw = _run_applescript(script)
        if not raw:
            return None
        parts = raw.split("|||")
        pname = parts[0]
        title = parts[1] if len(parts) > 1 else pname
        bounds = _parse_bounds(parts[2]) if len(parts) > 2 else (0, 0, 1920, 1080)
        pid = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        return WindowInfo(
            hwnd_or_id=pid,
            title=title,
            process_name=pname,
            process_id=pid,
            bounds=bounds,
            is_active=True,
        )

    def focus_window(self, title_substring: str) -> Dict[str, Any]:
        script = f"""
        tell application "System Events"
            repeat with p in (every application process whose visible is true)
                if (name of p) contains "{title_substring}" then
                    set frontmost of p to true
                    return "success"
                end if
                repeat with w in (every window of p)
                    try
                        if (title of w) contains "{title_substring}" then
                            set frontmost of p to true
                            return "success"
                        end if
                    end try
                end repeat
            end repeat
            return "not found"
        end tell
        """
        res = _run_applescript(script)
        success = "success" in res and "not found" not in res
        return {
            "success": success,
            "message": f"Focused {title_substring}" if success else f"Window not found: {title_substring}",
        }

    def launch_app(self, name_or_path: str, arguments: str = "", wait_ms: int = 2000) -> Dict[str, Any]:
        try:
            subprocess.Popen(["open", "-a", name_or_path])
            return {"success": True, "app": name_or_path}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
