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
2. **Text-Map First, Vision Second**
   - Prefer `get_screen_info` or `smart_click` for fast accessibility targeting over raw pixel visual grounding.
   - Fall back to `detect_elements_visual` or `screenshot` for canvas apps, games, or remote desktop environments.
3. **Action Verification**
   - Take a snapshot with `take_snapshot` before performing state-altering UI actions, then verify with `verify_action`.
4. **Batch Execution (`execute_actions`)**
   - Combine rapid sequential keyboard/mouse steps inside `execute_actions` to minimize network/LLM roundtrips.

---

## 🔐 Model Licenses & Safety Attributions

- UACC itself is licensed under the **MIT License**.
- When integrating UACC with proprietary or open-weights LLMs, ensure compliance with their respective Terms of Service and Model Licenses (e.g. Anthropic Commercial Terms, OpenAI Usage Policies, Llama 3 Community License).
- **Safety Mode (`UACC_SAFE_MODE=true`)** is enabled by default to prevent agents from executing destructive system patterns.
