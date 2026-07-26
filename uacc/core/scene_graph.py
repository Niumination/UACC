from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

REGION_LABELS = {
    "header": {"max_y_ratio": 0.12},
    "sidebar_left": {"max_x_ratio": 0.18},
    "sidebar_right": {"min_x_ratio": 0.82},
    "taskbar": {"min_y_ratio": 0.92},
}

MAX_ELEMENTS_PER_REGION = 15


def build_scene_graph(
    screen_width: int,
    screen_height: int,
    elements: List[Dict[str, Any]],
    active_window: Optional[Dict[str, Any]] = None,
    ocr_results: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build a compact textual scene graph from screen elements.

    Groups elements into spatial regions (header, sidebar, main, taskbar)
    and renders them as an indented text tree. Designed for vision-less LLMs
    to understand screen layout.

    Args:
        screen_width: Screen width in pixels.
        screen_height: Screen height in pixels.
        elements: List of element dicts with 'type', 'text', 'bounds', 'center', 'clickable'.
        active_window: Optional dict with window info.
        ocr_results: Optional list of OCR text detections.

    Returns:
        Multi-line string scene graph.
    """
    lines: List[str] = []

    title = "Desktop"
    if active_window:
        title = active_window.get("title", "") or active_window.get("name", "") or "Desktop"
    lines.append(f"SCENE: {screen_width}x{screen_height} | {title}")
    lines.append("")

    regions = _classify_elements(elements, screen_width, screen_height)

    for region_name, region_elements in regions.items():
        if not region_elements:
            continue
        label = region_name.replace("_", " ").title()
        bounds = _region_bounds(region_name, screen_width, screen_height)
        lines.append(f"── {label} (x:{bounds[0]}-{bounds[1]}, y:{bounds[2]}-{bounds[3]}) ──")
        for el in region_elements[:MAX_ELEMENTS_PER_REGION]:
            prefix = "  "
            el_type = el.get("type", "?")
            el_text = el.get("text", "") or el.get("name", "") or ""
            cx, cy = el.get("center", (0, 0))
            if isinstance(cx, dict):
                cx = cx.get("x", 0)
                cy = cy.get("y", 0)
            clickable = el.get("clickable", False) or el.get("interactive", False)
            editable = el.get("editable", False)
            selected = el.get("selected", False)

            flags = ""
            if clickable:
                flags += " [clickable]"
            if editable:
                flags += " [editable]"
            if selected:
                flags += " [selected]"

            text_preview = (el_text[:60] + "...") if len(el_text) > 60 else el_text
            if text_preview:
                lines.append(f'{prefix}· {el_type:12} "{text_preview}" at ({cx:>4}, {cy:>4}){flags}')
            else:
                lines.append(f"  · {el_type:12} at ({cx:>4}, {cy:>4}){flags}")
        if len(region_elements) > MAX_ELEMENTS_PER_REGION:
            lines.append(f"  · ... and {len(region_elements) - MAX_ELEMENTS_PER_REGION} more")
        lines.append("")

    if ocr_results:
        visible_texts = [r for r in ocr_results if isinstance(r, dict) and r.get("text")]
        if visible_texts:
            lines.append("── Visible Text (OCR) ──")
            for r in visible_texts[:20]:
                t = r["text"][:80]
                cx, cy = r.get("center", (0, 0))
                if isinstance(cx, dict):
                    cx = cx.get("x", 0)
                    cy = cy.get("y", 0)
                lines.append(f'  "{t}" at ({cx}, {cy})')
            if len(visible_texts) > 20:
                lines.append(f"  ... and {len(visible_texts) - 20} more text regions")
            lines.append("")

    result = "\n".join(lines)
    return result


def _classify_elements(
    elements: List[Dict[str, Any]],
    screen_w: int,
    screen_h: int,
) -> Dict[str, List[Dict[str, Any]]]:
    """Sort elements into spatial regions based on their bounds."""
    regions: Dict[str, List[Dict[str, Any]]] = {
        "header": [],
        "sidebar_left": [],
        "sidebar_right": [],
        "taskbar": [],
        "main": [],
        "modal": [],
        "unknown": [],
    }

    for el in elements:
        bounds = el.get("bounds", {})
        if isinstance(bounds, dict):
            left = bounds.get("left", 0) or bounds.get("x", 0)
            top = bounds.get("top", 0) or bounds.get("y", 0)
            right = bounds.get("right", left + 100)
            bottom = bounds.get("bottom", top + 100)
        elif isinstance(bounds, (list, tuple)):
            left, top = bounds[0], bounds[1]
            right = bounds[2] if len(bounds) > 2 else left + 100
            bottom = bounds[3] if len(bounds) > 3 else top + 100
        else:
            left, top, right, bottom = 0, 0, 100, 100

        cx = (left + right) // 2
        cy = (top + bottom) // 2

        el_type = (el.get("type") or "").lower()
        el_text = (el.get("text") or el.get("name") or "").lower()

        full_screen = left <= 0 and top <= 0 and right >= screen_w - 5 and bottom >= screen_h - 5
        if full_screen:
            continue

        modal = (left > screen_w * 0.1 and right < screen_w * 0.9 and
                 top > screen_h * 0.1 and bottom < screen_h * 0.9 and
                 (bottom - top) < screen_h * 0.8 and (right - left) < screen_w * 0.8)
        if modal and "dialog" in el_type:
            regions["modal"].append(el)
            continue

        if cy < screen_h * 0.10:
            regions["header"].append(el)
        elif cy > screen_h * 0.90:
            regions["taskbar"].append(el)
        elif cx < screen_w * 0.15:
            regions["sidebar_left"].append(el)
        elif cx > screen_w * 0.82:
            regions["sidebar_right"].append(el)
        else:
            regions["main"].append(el)

    for key in regions:
        regions[key].sort(key=lambda e: (e.get("bounds", {}).get("top", 0) if isinstance(e.get("bounds"), dict) else (e.get("bounds", (0,))[1] if isinstance(e.get("bounds"), (list, tuple)) else 0),
                                          e.get("bounds", {}).get("left", 0) if isinstance(e.get("bounds"), dict) else (e.get("bounds", (0,))[0] if isinstance(e.get("bounds"), (list, tuple)) else 0)))

    return regions


def _region_bounds(region: str, screen_w: int, screen_h: int) -> Tuple[int, int, int, int]:
    """Get bounding box of a screen region."""
    if region == "header":
        return (0, screen_w, 0, int(screen_h * 0.10))
    elif region == "taskbar":
        return (0, screen_w, int(screen_h * 0.90), screen_h)
    elif region == "sidebar_left":
        return (0, int(screen_w * 0.15), int(screen_h * 0.10), int(screen_h * 0.90))
    elif region == "sidebar_right":
        return (int(screen_w * 0.82), screen_w, int(screen_h * 0.10), int(screen_h * 0.90))
    elif region == "modal":
        return (0, screen_w, 0, screen_h)
    else:
        return (int(screen_w * 0.15), int(screen_w * 0.82), int(screen_h * 0.10), int(screen_h * 0.90))
