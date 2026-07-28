"""
VLM Engine — Vision Language Model integration for screen understanding.

Provides:
1. ``analyze_screenshot(image, prompt)`` — structured description of UI layout
2. ``detect_elements(image)`` — list of detected UI elements with pixel bounds
3. ``locate_element(image, target)`` — bounding box for a specific element

Supports three backends:
- OpenAI Vision (GPT-4o, GPT-4.1)
- Anthropic Vision (Claude 3.5 Sonnet / Opus 4)
- Local vision models via Ollama (Qwen3-VL, Holo3, LLaVA)

Each backend is tried in order of preference; the first configured provider wins.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class VLMElement:
    """A single UI element detected by the VLM."""

    text: str
    bounds: Tuple[int, int, int, int]
    center: Tuple[int, int]
    element_type: str
    confidence: float = 0.5
    source: str = "vlm"


@dataclass
class VLMAnalysis:
    """Structured understanding of a screenshot."""

    summary: str
    layout_description: str
    elements: List[VLMElement] = field(default_factory=list)
    interactive_count: int = 0
    detected_app: str = ""
    detected_text: List[str] = field(default_factory=list)


class _VLMProvider(Enum):
    NONE = "none"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


DETECT_PROMPT = """Analyze this screenshot and list every visible UI element.

For each element return: text label (if any), element type, and its bounding box
as percentage coordinates of the image width and height.

Valid element types: button, text_input, label, icon, checkbox, radio,
menu_item, link, tab, slider, dropdown, combobox, list_item

Output ONLY valid JSON — no markdown, no explanation:
{
  "elements": [
    {
      "text": "Submit",
      "type": "button",
      "bounds_percent": {"left": 0.5, "top": 0.6, "right": 0.65, "bottom": 0.66},
      "interactive": true
    }
  ],
  "layout": "brief layout description",
  "interactive_count": 5
}"""

ANALYZE_PROMPT = """Analyze this screenshot and provide a structured understanding.

Output ONLY valid JSON with these fields:
- summary: one-sentence description of the view
- layout: how the screen is organised (e.g. "sidebar + main content + toolbar")
- app_name: detected application or website name
- interactive_elements: list of {{label, type, position_description}}
- dialogs: any dialogs, modals or popups visible
- text_content: all visible text grouped by screen region"""

LOCATE_PROMPT = """Given the target "{target}", locate it precisely on this screenshot.
Return the bounding box as percentage coordinates of image width and height.

Output ONLY valid JSON:
{"found": true, "bounds_percent": {"left":0.3,"top":0.4,"right":0.5,"bottom":0.45}, "element_type":"button", "confidence":0.9}

If not found: {"found": false, "reason": "explanation"}"""

# ── VLM response cache ─────────────────────────────────────
_VLM_CACHE: dict = {}
_VLM_CACHE_TTL: float = 30.0  # seconds


def _image_hash(image: Image.Image) -> str:
    """Perceptual-ish hash: resize to 32×32, hash the bytes."""
    small = image.resize((32, 32), Image.Resampling.LANCZOS).convert("L")
    return hashlib.md5(small.tobytes()).hexdigest()


class VLMEngine:
    """Vision Language Model for screen understanding.

    Lazily detects the best available provider on first use.
    """

    def __init__(self) -> None:
        self._provider = _VLMProvider.NONE
        self._model = ""
        self._client: Any = None
        self._initialized = False

    # ── lifecycle ─────────────────────────────────────────────

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        self._pick_provider()
        self._initialized = True

    def _pick_provider(self) -> None:
        from uacc.config import config as cfg

        vlm = cfg.vlm
        prefer = (vlm.provider or "auto").strip().lower()

        def _try_openai() -> bool:
            key = vlm.openai_api_key or cfg.llm.openai_api_key
            if not key:
                return False
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=key, base_url=vlm.openai_base_url or cfg.llm.openai_base_url)
                self._model = vlm.openai_model or "gpt-4o"
                self._provider = _VLMProvider.OPENAI
                logger.info("VLM ← OpenAI (%s)", self._model)
                return True
            except ImportError:
                logger.debug("openai package not installed")
            return False

        def _try_anthropic() -> bool:
            key = vlm.anthropic_api_key or cfg.llm.anthropic_api_key
            if not key:
                return False
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=key)
                self._model = vlm.anthropic_model or "claude-sonnet-4-20250514"
                self._provider = _VLMProvider.ANTHROPIC
                logger.info("VLM ← Anthropic (%s)", self._model)
                return True
            except ImportError:
                logger.debug("anthropic package not installed")
            return False

        def _try_local() -> bool:
            model = vlm.local_model or cfg.llm.local_model
            if not model:
                return False
            try:
                from openai import OpenAI
                base_url = vlm.local_base_url or "http://localhost:11434/v1"
                self._client = OpenAI(api_key="not-needed", base_url=base_url)
                self._model = model
                self._provider = _VLMProvider.LOCAL
                logger.info("VLM ← Local (%s at %s)", self._model, base_url)
                return True
            except ImportError:
                logger.debug("openai package not installed for local VLM")
            return False

        # Try in preference order
        for attempt in [_try_openai, _try_anthropic, _try_local]:
            if prefer in ("auto", attempt.__name__[5:]):
                if attempt():
                    return

        logger.info("No VLM provider configured — VLM features unavailable")

    def is_available(self) -> bool:
        self._ensure_init()
        return self._provider != _VLMProvider.NONE

    # ── image encoding ────────────────────────────────────────

    @staticmethod
    def _encode_image(image: Image.Image) -> str:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    # ── raw LLM call ──────────────────────────────────────────

    def _call_vlm(self, image: Image.Image, system: str, user: str) -> str | None:
        self._ensure_init()
        if not self.is_available():
            return None

        b64 = self._encode_image(image)

        if self._provider == _VLMProvider.OPENAI:
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": [
                            {"type": "text", "text": user},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}},
                        ]},
                    ],
                    temperature=0.1,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )
                return resp.choices[0].message.content
            except Exception as exc:
                logger.warning("OpenAI VLM call failed: %s", exc)
                return None

        if self._provider == _VLMProvider.ANTHROPIC:
            try:
                resp = self._client.messages.create(
                    model=self._model,
                    system=system,
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": user},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    ]}],
                    temperature=0.1,
                    max_tokens=2000,
                )
                return resp.content[0].text
            except Exception as exc:
                logger.warning("Anthropic VLM call failed: %s", exc)
                return None

        if self._provider == _VLMProvider.LOCAL:
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": [
                            {"type": "text", "text": user},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ]},
                    ],
                    temperature=0.1,
                    max_tokens=2000,
                )
                return resp.choices[0].message.content
            except Exception as exc:
                logger.warning("Local VLM call failed: %s", exc)
                return None

        return None

    # ── JSON extraction ───────────────────────────────────────

    @staticmethod
    def _parse_json(text: str | None) -> dict | None:
        if not text:
            return None
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0] if "\n" in cleaned else cleaned[:-3]
        cleaned = cleaned.removeprefix("json").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("VLM JSON parse failed (length=%d)", len(cleaned))
            return None

    # ── public API ────────────────────────────────────────────

    def analyze_screenshot(self, image: Image.Image, context: str = "") -> VLMAnalysis | None:
        """Return a structured description of what's on screen."""
        prompt = ANALYZE_PROMPT
        if context:
            prompt += f"\n\nContext: {context}"
        raw = self._call_vlm(image, "You are a UI analysis assistant.", prompt)
        data = self._parse_json(raw)
        if not data:
            return None
        return VLMAnalysis(
            summary=data.get("summary", ""),
            layout_description=data.get("layout", ""),
            interactive_count=data.get("interactive_count", 0),
            detected_app=data.get("app_name", ""),
            detected_text=[e.get("label", "") for e in data.get("interactive_elements", []) if e.get("label")],
        )

    def detect_elements(self, image: Image.Image) -> List[VLMElement]:
        """Detect all visible UI elements with pixel bounding boxes."""
        if not self.is_available():
            return []
        img_w, img_h = image.size
        raw = self._call_vlm(image, "You are a UI element detector.", DETECT_PROMPT)
        data = self._parse_json(raw)
        if not data:
            return []

        elements: List[VLMElement] = []
        for el in data.get("elements", []):
            bp = el.get("bounds_percent", {})
            left = int(bp.get("left", 0) * img_w)
            top = int(bp.get("top", 0) * img_h)
            right = int(bp.get("right", 1) * img_w)
            bottom = int(bp.get("bottom", 1) * img_h)
            text = el.get("text", "")
            el_type = el.get("type", "unknown")
            elements.append(VLMElement(
                text=text,
                bounds=(left, top, right, bottom),
                center=((left + right) // 2, (top + bottom) // 2),
                element_type=el_type,
                confidence=0.7,
                source="vlm",
            ))
        return elements

    def locate_element(self, image: Image.Image, target: str) -> VLMElement | None:
        """Find a specific element by text / description and return its bounds.

        Results are cached with a 30-second TTL so repeated queries on
        the same screen avoid redundant API calls.
        """
        global _VLM_CACHE
        if not self.is_available():
            return None

        cache_key = (_image_hash(image), target)
        entry = _VLM_CACHE.get(cache_key)
        if entry is not None:
            age = time.monotonic() - entry["ts"]
            if age < _VLM_CACHE_TTL:
                logger.debug("VLM locate cache hit (%.1f s old)", age)
                return entry["result"]
            del _VLM_CACHE[cache_key]

        img_w, img_h = image.size
        prompt = LOCATE_PROMPT.format(target=target)
        raw = self._call_vlm(image, "You are a UI element locator.", prompt)
        data = self._parse_json(raw)
        if not data or not data.get("found"):
            _VLM_CACHE[cache_key] = {"result": None, "ts": time.monotonic()}
            return None

        bp = data.get("bounds_percent", {})
        left = int(bp.get("left", 0) * img_w)
        top = int(bp.get("top", 0) * img_h)
        right = int(bp.get("right", 1) * img_w)
        bottom = int(bp.get("bottom", 1) * img_h)
        result = VLMElement(
            text=target,
            bounds=(left, top, right, bottom),
            center=((left + right) // 2, (top + bottom) // 2),
            element_type=data.get("element_type", "unknown"),
            confidence=data.get("confidence", 0.5),
            source="vlm",
        )
        _VLM_CACHE[cache_key] = {"result": result, "ts": time.monotonic()}
        # Evict if cache exceeds limit
        if len(_VLM_CACHE) > 128:
            oldest = min(_VLM_CACHE, key=lambda k: _VLM_CACHE[k]["ts"])
            del _VLM_CACHE[oldest]
        return result


# Global singleton for import convenience
_engine: VLMEngine | None = None


def get_vlm_engine() -> VLMEngine:
    global _engine
    if _engine is None:
        _engine = VLMEngine()
    return _engine
