"""
Chrome DevTools Protocol (CDP) Bridge — connect to Chrome/Edge for DOM-level precision.

When the active window is a Chromium-based browser, this module connects via
the CDP debug protocol to merge DOM awareness with OS-level control.

Pipeline:
  1. Discover debug endpoint (http://localhost:PORT/json)
  2. Connect via WebSocket to the active page
  3. Execute CDP commands (Runtime.evaluate, DOM queries, etc.)
  4. Map DOM element coordinates to screen coordinates

Requires the browser to be launched with --remote-debugging-port=PORT
or a Chromium flag like --remote-allow-origins=*.
"""

from __future__ import annotations

import json
import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

# Default CDP ports to probe (Chrome, Edge, Brave)
DEFAULT_PORTS = [9222, 9223, 9229]


@dataclass
class CDPPage:
    """A browser tab/page discovered via CDP."""
    id: str
    title: str
    url: str
    ws_url: str
    type: str = "page"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "type": self.type,
        }


@dataclass
class DOMElement:
    """A DOM element with its properties and screen position."""
    tag: str
    text: str
    selector: str
    attributes: Dict[str, str] = field(default_factory=dict)
    bounds: Optional[Tuple[float, float, float, float]] = None  # (x, y, width, height)
    center: Optional[Tuple[int, int]] = None
    visible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "tag": self.tag,
            "text": self.text[:200] if self.text else "",
            "selector": self.selector,
        }
        if self.attributes:
            d["attributes"] = self.attributes
        if self.bounds:
            d["bounds"] = {
                "x": round(self.bounds[0]),
                "y": round(self.bounds[1]),
                "width": round(self.bounds[2]),
                "height": round(self.bounds[3]),
            }
        if self.center:
            d["center"] = {"x": self.center[0], "y": self.center[1]}
        d["visible"] = self.visible
        return d


class CDPBridge:
    """Manages CDP connections to Chromium-based browsers."""

    def __init__(self, port: int | None = None, timeout: float = 3.0):
        self._port: int | None = port
        self._timeout = timeout
        self._ws = None
        self._msg_id = 0
        self._active_page: CDPPage | None = None

    @property
    def connected(self) -> bool:
        return self._ws is not None

    def discover_port(self) -> int | None:
        """Probe common CDP ports to find an active debug session."""
        if self._port:
            if self._is_port_open(self._port):
                return self._port
            return None

        for port in DEFAULT_PORTS:
            if self._is_port_open(port):
                self._port = port
                logger.info("CDP debug port discovered: %d", port)
                return port
        return None

    def _is_port_open(self, port: int) -> bool:
        """Quick TCP check if a port is listening."""
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (OSError, ConnectionRefusedError):
            return False

    def list_pages(self) -> List[CDPPage]:
        """List all open browser pages/tabs via the HTTP debug API."""
        port = self.discover_port()
        if port is None:
            return []

        try:
            resp = urlopen(f"http://127.0.0.1:{port}/json", timeout=self._timeout)
            data = json.loads(resp.read().decode())
            pages = []
            for item in data:
                if item.get("type") != "page":
                    continue
                pages.append(CDPPage(
                    id=item.get("id", ""),
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    ws_url=item.get("webSocketDebuggerUrl", ""),
                    type=item.get("type", "page"),
                ))
            return pages
        except (URLError, Exception) as exc:
            logger.warning("Failed to list CDP pages: %s", exc)
            return []

    def connect(self, page_id: str = "") -> bool:
        """Connect to a specific page via WebSocket, or the first available page."""
        try:
            import websocket
        except ImportError:
            logger.error("websocket-client not installed. Run: pip install websocket-client")
            return False

        pages = self.list_pages()
        if not pages:
            return False

        target = None
        if page_id:
            target = next((p for p in pages if p.id == page_id), None)
        if not target:
            target = pages[0]

        if not target.ws_url:
            logger.error("No WebSocket URL for page: %s", target.title)
            return False

        try:
            self._ws = websocket.create_connection(
                target.ws_url,
                timeout=self._timeout,
            )
            self._active_page = target
            self._msg_id = 0
            logger.info("CDP connected to: %s (%s)", target.title, target.url)
            return True
        except Exception as exc:
            logger.error("CDP WebSocket connection failed: %s", exc)
            self._ws = None
            return False

    def disconnect(self):
        """Close the WebSocket connection."""
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
            self._active_page = None

    def send_command(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Send a CDP command and return the result."""
        if not self._ws:
            raise ConnectionError("Not connected to CDP. Call connect() first.")

        self._msg_id += 1
        msg = {
            "id": self._msg_id,
            "method": method,
            "params": params or {},
        }

        self._ws.send(json.dumps(msg))

        # Wait for response with matching ID
        deadline = time.time() + self._timeout
        while time.time() < deadline:
            raw = self._ws.recv()
            resp = json.loads(raw)
            if resp.get("id") == self._msg_id:
                if "error" in resp:
                    raise RuntimeError(f"CDP error: {resp['error'].get('message', resp['error'])}")
                return resp.get("result", {})
        raise TimeoutError(f"CDP command timed out: {method}")

    def evaluate_js(self, expression: str, return_by_value: bool = True) -> Any:
        """Execute JavaScript in the page and return the result."""
        result = self.send_command("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": True,
        })

        if "exceptionDetails" in result:
            exc = result["exceptionDetails"]
            text = exc.get("text", "")
            ex_obj = exc.get("exception", {})
            desc = ex_obj.get("description", text)
            raise RuntimeError(f"JavaScript error: {desc}")

        value = result.get("result", {}).get("value")
        return value

    def query_selector(self, selector: str) -> Optional[DOMElement]:
        """Find a single DOM element by CSS selector and return its info + screen position."""
        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return null;
            const rect = el.getBoundingClientRect();
            const attrs = {{}};
            for (const a of el.attributes || []) {{
                attrs[a.name] = a.value;
            }}
            return {{
                tag: el.tagName.toLowerCase(),
                text: (el.innerText || el.value || el.textContent || '').substring(0, 200),
                selector: {json.dumps(selector)},
                attributes: attrs,
                bounds: {{ x: rect.x, y: rect.y, width: rect.width, height: rect.height }},
                visible: rect.width > 0 && rect.height > 0 && el.offsetParent !== null,
            }};
        }})()
        """
        data = self.evaluate_js(js)
        if not data:
            return None

        bounds = data.get("bounds", {})
        bx, by = bounds.get("x", 0), bounds.get("y", 0)
        bw, bh = bounds.get("width", 0), bounds.get("height", 0)

        # Convert viewport coords to screen coords (need window position offset)
        screen_offset = self._get_browser_viewport_offset()
        sx = int(bx + screen_offset[0])
        sy = int(by + screen_offset[1])

        return DOMElement(
            tag=data.get("tag", ""),
            text=data.get("text", ""),
            selector=data.get("selector", selector),
            attributes=data.get("attributes", {}),
            bounds=(bx, by, bw, bh),
            center=(sx + int(bw / 2), sy + int(bh / 2)),
            visible=data.get("visible", True),
        )

    def query_selector_all(self, selector: str, limit: int = 50) -> List[DOMElement]:
        """Find all DOM elements matching a CSS selector."""
        js = f"""
        (() => {{
            const els = document.querySelectorAll({json.dumps(selector)});
            const results = [];
            const limit = {limit};
            for (let i = 0; i < Math.min(els.length, limit); i++) {{
                const el = els[i];
                const rect = el.getBoundingClientRect();
                const attrs = {{}};
                for (const a of el.attributes || []) {{
                    attrs[a.name] = a.value;
                }}
                results.push({{
                    tag: el.tagName.toLowerCase(),
                    text: (el.innerText || el.value || el.textContent || '').substring(0, 200),
                    selector: {json.dumps(selector)} + ':nth-of-type(' + (i+1) + ')',
                    attributes: attrs,
                    bounds: {{ x: rect.x, y: rect.y, width: rect.width, height: rect.height }},
                    visible: rect.width > 0 && rect.height > 0 && el.offsetParent !== null,
                }});
            }}
            return results;
        }})()
        """
        data = self.evaluate_js(js) or []
        screen_offset = self._get_browser_viewport_offset()

        elements = []
        for item in data:
            bounds = item.get("bounds", {})
            bx, by = bounds.get("x", 0), bounds.get("y", 0)
            bw, bh = bounds.get("width", 0), bounds.get("height", 0)
            sx = int(bx + screen_offset[0])
            sy = int(by + screen_offset[1])

            elements.append(DOMElement(
                tag=item.get("tag", ""),
                text=item.get("text", ""),
                selector=item.get("selector", ""),
                attributes=item.get("attributes", {}),
                bounds=(bx, by, bw, bh),
                center=(sx + int(bw / 2), sy + int(bh / 2)),
                visible=item.get("visible", True),
            ))
        return elements

    def get_page_info(self) -> Dict[str, Any]:
        """Get comprehensive info about the current page."""
        js = """
        (() => {
            const forms = document.querySelectorAll('form');
            const links = document.querySelectorAll('a[href]');
            const inputs = document.querySelectorAll('input, textarea, select');
            const buttons = document.querySelectorAll('button, [role="button"], input[type="submit"]');
            const images = document.querySelectorAll('img');

            return {
                url: window.location.href,
                title: document.title,
                domain: window.location.hostname,
                protocol: window.location.protocol,
                readyState: document.readyState,
                doctype: document.doctype ? document.doctype.name : null,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight,
                    scrollX: window.scrollX,
                    scrollY: window.scrollY,
                    scrollHeight: document.documentElement.scrollHeight,
                },
                counts: {
                    forms: forms.length,
                    links: links.length,
                    inputs: inputs.length,
                    buttons: buttons.length,
                    images: images.length,
                    total_elements: document.querySelectorAll('*').length,
                },
                meta: {
                    description: document.querySelector('meta[name="description"]')?.content || '',
                    charset: document.characterSet,
                    language: document.documentElement.lang || '',
                },
            };
        })()
        """
        return self.evaluate_js(js) or {}

    def click_element(self, selector: str) -> bool:
        """Click a DOM element by CSS selector via JavaScript."""
        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return false;
            el.click();
            return true;
        }})()
        """
        return self.evaluate_js(js) or False

    def type_in_element(self, selector: str, text: str, clear_first: bool = False) -> bool:
        """Type text into a DOM element (input/textarea)."""
        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return false;
            el.focus();
            if ({json.dumps(clear_first)}) {{
                el.value = '';
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
            el.value += {json.dumps(text)};
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        }})()
        """
        return self.evaluate_js(js) or False

    def get_element_text(self, selector: str) -> str:
        """Get the text content of a DOM element."""
        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return '';
            return el.innerText || el.value || el.textContent || '';
        }})()
        """
        return self.evaluate_js(js) or ""

    def get_element_attribute(self, selector: str, attribute: str) -> str:
        """Get a specific attribute of a DOM element."""
        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return null;
            return el.getAttribute({json.dumps(attribute)});
        }})()
        """
        return self.evaluate_js(js) or ""

    def wait_for_selector(
        self,
        selector: str,
        timeout_ms: int = 10000,
        poll_interval_ms: int = 250,
    ) -> Optional[DOMElement]:
        """Poll until a CSS selector matches an element in the DOM."""
        deadline = time.time() + timeout_ms / 1000
        while time.time() < deadline:
            el = self.query_selector(selector)
            if el:
                return el
            time.sleep(poll_interval_ms / 1000)
        return None

    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate the current page to a new URL."""
        result = self.send_command("Page.navigate", {"url": url})
        return result

    def _get_browser_viewport_offset(self) -> Tuple[int, int]:
        """Estimate the browser viewport's screen position.

        Uses JavaScript to get the screen position of the browser window,
        then accounts for chrome (toolbars, tabs, etc).
        """
        try:
            js = """
            (() => {
                return {
                    screenX: window.screenX || window.screenLeft || 0,
                    screenY: window.screenY || window.screenTop || 0,
                    outerWidth: window.outerWidth,
                    outerHeight: window.outerHeight,
                    innerWidth: window.innerWidth,
                    innerHeight: window.innerHeight,
                };
            })()
            """
            data = self.evaluate_js(js) or {}
            sx = data.get("screenX", 0)
            sy = data.get("screenY", 0)
            outer_h = data.get("outerHeight", 0)
            inner_h = data.get("innerHeight", 0)

            # Chrome height = outerHeight - innerHeight (tabs, address bar, etc.)
            chrome_height = max(0, outer_h - inner_h)
            outer_w = data.get("outerWidth", 0)
            inner_w = data.get("innerWidth", 0)
            chrome_width = max(0, (outer_w - inner_w) // 2)

            return (sx + chrome_width, sy + chrome_height)
        except Exception:
            return (0, 0)


# ── Singleton ────────────────────────────────────────────────

_bridge: CDPBridge | None = None


def get_cdp_bridge(port: int | None = None) -> CDPBridge:
    """Get or create the global CDP bridge singleton."""
    global _bridge
    if _bridge is None:
        _bridge = CDPBridge(port=port)
    return _bridge


def auto_connect() -> CDPBridge:
    """Auto-discover and connect to the active browser tab."""
    bridge = get_cdp_bridge()
    if not bridge.connected:
        bridge.connect()
    return bridge
