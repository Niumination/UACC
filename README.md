<p align="center">
  <img src="assets/hero_banner.png" alt="UACC — Universal AI Computer Control" width="100%">
</p>

<h1 align="center">🖥️ UACC — Universal AI Computer Control</h1>

<p align="center">
  <strong>Give any AI Agent the power to control a computer with pixel-precise UI interactions via MCP.</strong><br>
  <em>Open-source • Pure MCP Server • Works with any AI Agent • Vision optional</em>
</p>

<p align="center">
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Native-blue?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTEyIDJMMiA3bDEwIDUgMTAtNS0xMC01eiIvPjxwYXRoIGQ9Ik0yIDE3bDEwIDUgMTAtNSIvPjxwYXRoIGQ9Ik0yIDEybDEwIDUgMTAtNSIvPjwvc3ZnPg==" alt="MCP Native"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://github.com/uacc-project/uacc/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/version-1.0.0-orange?style=for-the-badge" alt="Version"></a>
  <a href="https://github.com/uacc-project/uacc/stargazers"><img src="https://img.shields.io/github/stars/uacc-project/uacc?style=for-the-badge&color=yellow" alt="Stars"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=for-the-badge" alt="PRs Welcome"></a>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-mcp-server">MCP Tools</a> •
  <a href="#-agent-integrations">Agent Integrations</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-examples">Examples</a> •
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

## 🔥 Pure MCP Server Architecture

UACC is a **pure Model Context Protocol (MCP) server**. It exposes 25+ pixel-precise desktop control tools directly to any AI Agent (Claude Code, Hermes, Cursor, OpenCode, OpenClaw, Claude Desktop, etc.).

> **💡 Vision optional:** Text-only AI models can "see" the screen through structured UI accessibility text maps with exact coordinates (`get_screen_info`). Vision-capable models can also capture raw or grid-encoded screenshots (`screenshot`).

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔌 **Pure MCP Server** | Works natively with Claude Code, Hermes, Cursor, OpenCode, OpenClaw, Claude Desktop (55 tools) |
| 🌐 **Browser DOM Bridge** | Chrome DevTools Protocol (CDP) integration for DOM-level CSS selector targeting (`browser_query`, `browser_click`) |
| 🌐 **Cross-Platform** | Native platform drivers for Windows, macOS, and Linux |
| 🛡️ **Self-Healing Actions** | Auto-retry fallback chain (a11y → OCR → vision) with visual action verification (`smart_click`, `verify_action`) |
| 🤖 **Agent Agnostic** | Connect any MCP-compliant AI agent or custom MCP client |
| 👁️ **Vision Optional** | Structured text map feeds allow text-only models to navigate with exact coordinates |
| 🎯 **Pixel Precise** | Element locator, fuzzy button matching, sub-10px UI targeting |
| 🖱️ **Human Mimicry** | Bézier curve mouse paths, variable typing speeds, natural pauses |
| 💾 **Workflow Memory** | Create, save, inspect, and replay multi-step automations (`create_workflow`, `run_workflow`) |
| 🛡️ **Safe Mode** | Built-in pattern blocking for destructive system commands |
| ⚡ **Zero Heavy Infra** | Pure Python package. Run locally with `pip install -e .` |

---

## 🚀 Quick Start

Get UACC running as an MCP server in under 2 minutes:

```bash
# 1. Clone & install
git clone https://github.com/uacc-project/uacc.git
cd uacc
pip install -e .

# 2. Test CLI MCP launcher (stdio)
uacc-mcp

# Or via python module
python -m uacc
```

---

## 🔌 MCP Tools (25 Native Tools)

When an AI agent connects to UACC, it gets access to standard desktop automation tools:

### Screen Understanding & Navigation
- `get_screen_info`: Returns a structured text map of interactive UI elements.
- `screenshot`: Capture full screen or specified region image.
- `find_element`: Search for UI elements by name or control type.
- `get_mouse_position`: Get current mouse coordinates.
- `wait_for_element`: Poll screen until a specific UI element appears.

### Mouse & Keyboard Control
- `click`: Click at precise screen coordinates `(x, y)`.
- `click_element`: Smart target and click an element by visible text/name.
- `type_text`: Type text via simulated human typing.
- `hotkey`: Trigger key combinations (e.g. `['ctrl', 's']`).
- `scroll`: Scroll vertically/horizontally at a position.
- `drag`: Perform Bézier curve drag-and-drop operations.
- `hover`: Move cursor to coordinate position.

### Window Management & Applications
- `get_active_window`: Inspect focused window title, bounds, process.
- `list_windows`: List all open desktop windows.
- `focus_window`: Bring target window to foreground.
- `resize_window`, `move_window`, `minimize_maximize`: Manage window size & state.
- `launch_app`: Launch application by executable name or path.
- `open_url`: Open URL in default browser.

### Clipboard & Painting
- `clipboard_read`, `clipboard_write`: Read/write system clipboard text.
- `paint_preset`: Paint geometric presets in MS Paint (rose, galaxy, mountains, peacock).
- `paint_image`: Convert image contours to mouse strokes in MS Paint.

### Workflow & Task Management
- `create_workflow`, `list_workflows`, `get_workflow`, `delete_workflow`, `run_workflow`: Persistent workflow memory stored in `~/.uacc/workflows/`.
- `uacc_planner`: Mandatory planner tool to determine tool execution sequence and canvas constraints.

---

## 🔌 Agent Integrations

Detailed configuration guides for AI agents are available in [AGENTS_INTEGRATION.md](AGENTS_INTEGRATION.md).

### Quick Integration Snippets:

#### Claude Code (CLI)
```bash
claude mcp add uacc python -m uacc.mcp
```

#### Hermes Agent
```bash
hermes mcp add uacc -- python -m uacc.mcp
hermes mcp restart
```

#### OpenCode
Add to `opencode.json`:
```json
{
  "mcp": {
    "uacc": {
      "type": "local",
      "command": ["python", "-m", "uacc.mcp"],
      "enabled": true
    }
  }
}
```

#### Cursor / Claude Desktop
Add to your MCP configuration JSON:
```json
{
  "mcpServers": {
    "uacc": {
      "command": "uacc-mcp",
      "args": []
    }
  }
}
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                  AI Agent / Client                   │
│   Claude Code │ Hermes │ OpenCode │ OpenClaw │ Cursor │
├──────────────────────────────────────────────────────┤
│                     MCP Protocol                     │
│               stdio │ SSE │ Streamable HTTP          │
├──────────────────────────────────────────────────────┤
│                   UACC MCP Server                    │
│   25+ Tools │ Screen Resources │ Workflow Memory     │
├──────────────────────────────────────────────────────┤
│                   UACC Core Engine                   │
│   Text Map │ Grid Encoder │ Accessibility Tree       │
│   OCR Engine │ Human Mimicry │ Safe Mode Guard       │
└──────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
uacc/
├── uacc/
├── __main__.py          # python -m uacc entrypoint
│   ├── config.py              # Central configuration
│   ├── mcp.py                 # python -m uacc.mcp forwarding
│   ├── core/                  # Screen capture, accessibility tree, text map, grid
│   ├── actions/               # Human mimicry mouse paths, action executor
│   ├── safety/                # Command safety filtering
│   ├── workflows/             # Persistent JSON workflow memory
│   ├── tasks/                 # Async task runner
│   └── tools/                 # Tool registry & uacc_planner
├── uacc_mcp/                  # FastMCP Server definition & tool handlers
├── examples/                  # Demo & client integration scripts
├── tests/                     # Unit & integration tests
├── AGENTS.md                  # Comprehensive agent rules & workflow docs
├── AGENTS_INTEGRATION.md      # Per-agent setup instructions
└── pyproject.toml
```

---

## 🧪 Testing

Run pytest suite to verify core engines and tool executors:

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 📄 License

[MIT](LICENSE) — Open source software.
