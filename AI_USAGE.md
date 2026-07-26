# AI Usage & Agent Conventions

This document outlines guidelines, conventions, and model licensing considerations for using AI models and autonomous agents with **UACC (Universal AI Computer Control)**.

---

## 🤖 Supported Models & Host Architectures

UACC is protocol-native via the **Model Context Protocol (MCP)**. It works seamlessly across both text-only and multimodal vision LLMs:

| Model Family | Transport | Capabilities in UACC |
|---|---|---|
| **Claude 3.5 / 3.7 / Opus / Sonnet** | stdio / SSE | Full MCP support, screen diff verification, text-map navigation, CDP DOM control |
| **GPT-4o / GPT-4.5 / o3** | stdio / HTTP | Full MCP support, structured element targeting, visual screen scans |
| **Gemini 1.5 Pro / 2.0 Flash** | stdio / HTTP | Full MCP support, high-frequency batch action execution |
| **Qwen 2.5 VL / DeepSeek R1 / V3** | stdio / HTTP | Local or API agent execution via FastMCP |

---

## ⚡ Tool Selection & Execution Strategy

When building or prompting AI agents with UACC, adhere to these operational conventions:

1. **Mandatory Planning (`uacc_planner`)**
   - Call `uacc_planner` before executing multi-step complex automation to get the optimal tool sequence.
2. **Self-Healing & Target Clicking First (`smart_click` & `click(target=...)`)**
   - Prefer passing text labels directly via `smart_click(target="...")` or `click(target="...")` over raw coordinate guessing. UACC automatically resolves coordinates via accessibility tree, OCR, and VLM.
3. **Visual Overlays for Custom Canvas UIs**
   - For video editors (Filmora), drawing apps, or games lacking accessibility tree elements, call `screenshot(overlay="markers")` (numbered Set-of-Mark badges) or `screenshot(overlay="grid")` (A1–Z27 coordinate grid). Do NOT visually guess raw `(x, y)` pixels from plain images.
4. **1:1 Physical Pixel Grounding (Windows DPI Aware)**
   - On Windows, UACC automatically initializes Per-Monitor DPI Awareness (`SetProcessDpiAwareness(2)`). Screen captures and mouse coordinates are locked to 1:1 physical pixels without scaling drift.
5. **Action Verification**
   - Take a snapshot with `take_snapshot` before performing state-altering UI actions, or pass `verify=True` to `smart_click` for automated visual confirmation.
6. **Batch Execution (`execute_actions`)**
   - Combine rapid sequential keyboard/mouse steps inside `execute_actions` to minimize network/LLM roundtrips.
7. **Background Tasks (`start_task`)**
   - For repetitive or long-running tasks (e.g. clicking through 50 dialogs), use non-blocking background threads via `start_task` and poll progress with `get_task_status`.

---

## 🔐 Model Licenses & Safety Attributions

- UACC itself is licensed under the **MIT License**.
- When integrating UACC with proprietary or open-weights LLMs, ensure compliance with their respective Terms of Service and Model Licenses (e.g. Anthropic Commercial Terms, OpenAI Usage Policies, Llama 3 Community License).
- **Safety Mode (`UACC_SAFE_MODE=true`)** is enabled by default to prevent agents from executing destructive system patterns.
