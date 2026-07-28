"""
OCR Engine — extract visible text and positions from a screenshot.

Fast path (default): pytesseract — instant load, ~200ms per call.
Heavy path (opt-in):  EasyOCR — GPU-accelerated, ~500-5000ms per call.

Set ``UACC_OCR_HEAVY=true`` to use EasyOCR (more accurate, slower).
Set ``UACC_OCR_GPU=false`` to force CPU even when CUDA is available.

The engine is loaded once and reused across calls for speed.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

# Suppress torch's noisy pin_memory warning when no GPU is present
os.environ.setdefault("TORCH_CPP_LOG_LEVEL", "ERROR")

logger = logging.getLogger(__name__)

# Lazy-loaded OCR reader
_reader: Optional[object] = None
_gpu_cache: Optional[bool] = None  # lazy cache for GPU availability


@dataclass
class OCRResult:
    """A single text detection from OCR."""

    text: str
    bounds: Tuple[int, int, int, int]  # (left, top, right, bottom)
    center: Tuple[int, int]
    confidence: float

    @property
    def width(self) -> int:
        return self.bounds[2] - self.bounds[0]

    @property
    def height(self) -> int:
        return self.bounds[3] - self.bounds[1]


def _gpu_available() -> bool:
    """Check if CUDA is actually available — result is cached after first call."""
    global _gpu_cache
    if _gpu_cache is not None:
        return _gpu_cache
    try:
        import torch
        _gpu_cache = torch.cuda.is_available()
    except Exception:
        _gpu_cache = False
    return _gpu_cache


_PIL_FALLBACK = False


def _get_reader() -> object:
    """Lazily initialise an OCR reader — fast path by default.

    Resolution order:
    1. ``UACC_OCR_HEAVY=true`` → EasyOCR (PyTorch-based, GPU-accelerated, accurate but slow)
    2. Default → pytesseract (instant load, fast CPU inference)
       If pytesseract is not installed, falls back to EasyOCR, then None.

    Returns ``None`` when no OCR engine is available (callers handle gracefully).
    """
    global _reader, _PIL_FALLBACK
    if _reader is not None:
        return _reader
    if _PIL_FALLBACK:
        return None

    use_heavy = os.environ.get("UACC_OCR_HEAVY", "").strip().lower() == "true"

    if not use_heavy:
        try:
            import pytesseract  # noqa: F401
            _reader = "pytesseract"
            logger.info("OCR ← pytesseract (fast mode)")
            return _reader
        except ImportError:
            logger.info("pytesseract not installed — trying EasyOCR")

    try:
        import easyocr

        env_override = os.environ.get("UACC_OCR_GPU", "").strip().lower()
        if env_override == "false":
            use_gpu = False
        elif env_override == "true":
            use_gpu = True
        else:
            use_gpu = _gpu_available()

        _reader = easyocr.Reader(
            ["en"],
            gpu=use_gpu,
            verbose=False,
        )
        logger.info("OCR ← EasyOCR (heavy mode, gpu=%s)", use_gpu)
    except ImportError:
        logger.warning("No OCR engine available — install pytesseract for fast OCR: pip install pytesseract")
        _PIL_FALLBACK = True

    return _reader  # type: ignore[return-value]


def extract_text(
    image: Image.Image,
    confidence_threshold: float = 0.3,
    merge_close: bool = True,
    merge_distance: int = 10,
    max_dimension: int = 1280,
    mode: str = "balanced",
) -> List[OCRResult]:
    """Run OCR on a PIL Image and return detected text with positions.

    Args:
        image: Input screenshot (PIL Image, RGB).
        confidence_threshold: Minimum confidence to keep a detection.
        merge_close: If True, merge detections that are spatially close.
        merge_distance: Pixel distance threshold for merging.
        max_dimension: Max width/height for OCR inference downscaling (speeds up CPU OCR).
        mode: Preprocessing mode — "balanced", "web" (higher contrast, upscaled for web text),
              "terminal" (light-on-dark), or "fast" (lower resolution for speed).

    Returns:
        List of OCRResult sorted top-to-bottom, left-to-right.
    """
    reader = _get_reader()

    orig_w, orig_h = image.size
    scale = 1.0

    # Apply mode-specific preprocessing
    processed = image
    if mode == "web":
        web_size = max_dimension * 2
        if max(orig_w, orig_h) > web_size:
            scale = web_size / float(max(orig_w, orig_h))
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            processed = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
        else:
            scale = 1.0
        processed = processed.convert("L")
        processed = processed.point(lambda x: 0 if x < 160 else 255)
        processed = processed.convert("RGB")
    elif mode == "terminal":
        if max(orig_w, orig_h) > max_dimension:
            scale = max_dimension / float(max(orig_w, orig_h))
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            processed = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
        else:
            scale = 1.0
        processed = processed.convert("L")
        processed = processed.point(lambda x: 255 if x < 100 else 0)
        processed = processed.convert("RGB")
    elif mode == "fast":
        fast_dim = 800
        if max(orig_w, orig_h) > fast_dim:
            scale = fast_dim / float(max(orig_w, orig_h))
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            processed = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
        else:
            scale = 1.0
    else:
        if max(orig_w, orig_h) > max_dimension:
            scale = max_dimension / float(max(orig_w, orig_h))
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            processed = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
        else:
            scale = 1.0

    results: List[OCRResult] = []
    inv_scale = 1.0 / scale if scale != 1.0 else 1.0

    if reader == "pytesseract":
        try:
            import pytesseract
            ocr_data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
            for i in range(len(ocr_data["text"])):
                text = (ocr_data["text"][i] or "").strip()
                conf = float(ocr_data["conf"][i]) / 100.0 if ocr_data["conf"][i] != "-1" else 0.0
                if not text or conf < confidence_threshold:
                    continue
                left, top = ocr_data["left"][i], ocr_data["top"][i]
                w, h = ocr_data["width"][i], ocr_data["height"][i]
                right, bottom = left + w, top + h
                results.append(OCRResult(
                    text=text,
                    bounds=(int(left * inv_scale), int(top * inv_scale),
                            int(right * inv_scale), int(bottom * inv_scale)),
                    center=(int((left + right) * inv_scale // 2), int((top + bottom) * inv_scale // 2)),
                    confidence=round(conf, 3),
                ))
        except ImportError:
            logger.error("pytesseract not available — returning empty OCR results")
            return results
    elif reader is None:
        logger.warning("No OCR engine available — returning empty results")
        return results
    else:
        img_array = np.array(processed)

        # EasyOCR returns: list of (bbox, text, confidence)
        raw_results = reader.readtext(img_array)  # type: ignore[union-attr]

        for bbox, text, conf in raw_results:
            if conf < confidence_threshold:
                continue

            text = text.strip()
            if not text:
                continue

            # Convert 4-corner bbox to (left, top, right, bottom) and rescale coordinates
            xs = [p[0] * inv_scale for p in bbox]
            ys = [p[1] * inv_scale for p in bbox]
            left, top = int(min(xs)), int(min(ys))
            right, bottom = int(max(xs)), int(max(ys))
            cx = (left + right) // 2
            cy = (top + bottom) // 2

            results.append(
                OCRResult(
                    text=text,
                bounds=(left, top, right, bottom),
                center=(cx, cy),
                confidence=round(conf, 3),
            )
        )

    # Sort: top-to-bottom, then left-to-right
    results.sort(key=lambda r: (r.bounds[1], r.bounds[0]))

    if merge_close:
        results = _merge_nearby(results, merge_distance)

    logger.info("OCR found %d text regions (scale=%.2f)", len(results), scale)
    return results


def _merge_nearby(results: List[OCRResult], distance: int) -> List[OCRResult]:
    """Merge OCR results that are on the same line and close together."""
    if not results:
        return results

    merged: List[OCRResult] = []
    used = set()

    for i, r1 in enumerate(results):
        if i in used:
            continue
        group_text = r1.text
        group_bounds = list(r1.bounds)
        group_conf = [r1.confidence]

        for j in range(i + 1, len(results)):
            if j in used:
                continue
            r2 = results[j]
            # Same line (vertical overlap) and horizontally close
            v_overlap = not (r2.bounds[1] > r1.bounds[3] or r2.bounds[3] < r1.bounds[1])
            h_close = abs(r2.bounds[0] - group_bounds[2]) < distance
            if v_overlap and h_close:
                group_text += " " + r2.text
                group_bounds[0] = min(group_bounds[0], r2.bounds[0])
                group_bounds[1] = min(group_bounds[1], r2.bounds[1])
                group_bounds[2] = max(group_bounds[2], r2.bounds[2])
                group_bounds[3] = max(group_bounds[3], r2.bounds[3])
                group_conf.append(r2.confidence)
                used.add(j)

        cx = (group_bounds[0] + group_bounds[2]) // 2
        cy = (group_bounds[1] + group_bounds[3]) // 2
        merged.append(
            OCRResult(
                text=group_text,
                bounds=tuple(group_bounds),  # type: ignore[arg-type]
                center=(cx, cy),
                confidence=round(sum(group_conf) / len(group_conf), 3),
            )
        )

    return merged


def extract_text_simple(image: Image.Image) -> str:
    """Quick helper — return all detected text as a single string."""
    results = extract_text(image)
    return "\n".join(r.text for r in results)
