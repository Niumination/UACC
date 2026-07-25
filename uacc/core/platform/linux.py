"""
Linux Platform Driver — xdotool + wmctrl + AT-SPI2 (dasbus).

Window management uses wmctrl (listing, focus) and xdotool (active window,
geometry, PID). Accessibility tree uses AT-SPI2 via dasbus (D-Bus).
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from uacc.core.platform.base import BasePlatformDriver, WindowInfo

logger = logging.getLogger(__name__)


def _run_cmd(cmd: List[str]) -> str:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        return res.stdout.strip()
    except Exception as exc:
        logger.warning("Linux CLI command failed (%s): %s", cmd, exc)
        return ""


class LinuxDriver(BasePlatformDriver):
    """Linux implementation using xdotool, wmctrl, and AT-SPI2 (dasbus)."""

    def get_ui_tree(self, max_depth: int = 10) -> List[Any]:
        from uacc.core.accessibility import get_ui_tree as _get_tree
        return _get_tree(max_depth=max_depth)

    def list_windows(self) -> List[WindowInfo]:
        raw = _run_cmd(["wmctrl", "-l", "-p", "-G"])
        results: List[WindowInfo] = []
        if not raw:
            return results

        for line in raw.split("\n"):
            parts = line.split(None, 7)
            if len(parts) < 8:
                continue
            wid = parts[0]
            pid = int(parts[2]) if parts[2].isdigit() else 0
            x = int(parts[3])
            y = int(parts[4])
            w = int(parts[5])
            h = int(parts[6])
            title = parts[7]

            process_name = title.split()[0] if title else "app"
            if pid > 0:
                try:
                    import psutil
                    proc = psutil.Process(pid)
                    process_name = proc.name()
                except Exception:
                    pass

            results.append(WindowInfo(
                hwnd_or_id=wid,
                title=title,
                process_name=process_name,
                process_id=pid,
                bounds=(x, y, x + w, y + h),
            ))
        return results

    def get_active_window(self) -> Optional[WindowInfo]:
        wid = _run_cmd(["xdotool", "getactivewindow"])
        if not wid:
            return None

        title = _run_cmd(["xdotool", "getwindowname", wid])
        geom_raw = _run_cmd(["xdotool", "getwindowgeometry", "--shell", wid])

        x = y = w = h = 0
        if geom_raw:
            for kv in geom_raw.split("\n"):
                if "=" not in kv:
                    continue
                k, v = kv.split("=", 1)
                if k == "X": x = int(v)
                elif k == "Y": y = int(v)
                elif k == "WIDTH": w = int(v)
                elif k == "HEIGHT": h = int(v)

        pid = 0
        pid_raw = _run_cmd(["xdotool", "getactivewindow", "getwindowpid"])
        if pid_raw and pid_raw.isdigit():
            pid = int(pid_raw)

        process_name = "active_app"
        if pid > 0:
            try:
                import psutil
                proc = psutil.Process(pid)
                process_name = proc.name()
            except Exception:
                pass

        return WindowInfo(
            hwnd_or_id=wid,
            title=title or "Active Window",
            process_name=process_name,
            process_id=pid,
            bounds=(x, y, x + w, y + h),
            is_active=True,
        )

    def focus_window(self, title_substring: str) -> Dict[str, Any]:
        output = _run_cmd(["wmctrl", "-a", title_substring])
        success = not output or "error" not in output.lower()
        return {
            "success": success,
            "message": f"Focused {title_substring}" if success else f"Failed to focus: {output}",
        }

    def launch_app(self, name_or_path: str, arguments: str = "", wait_ms: int = 2000) -> Dict[str, Any]:
        try:
            cmd = [name_or_path]
            if arguments:
                cmd.extend(arguments.split())
            subprocess.Popen(cmd)
            return {"success": True, "app": name_or_path}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
