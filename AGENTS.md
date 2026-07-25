# UACC — AI Agent Instructions

## 🛜 MCP Tools Only — No Python Scripts

UACC exposes **25+ native MCP tools** (`mcp_uacc_*`) that you can call directly. **Do NOT write separate Python scripts** that wrap or re-implement UACC's functionality. Use the built-in MCP tools:

| What you want | Use this MCP tool |
|---|---|
| See the screen | `mcp_uacc_get_screen_info` or `mcp_uacc_screenshot` |
| Click something | `mcp_uacc_click(x, y)` or `mcp_uacc_click_element(name="...")` |
| Type text | `mcp_uacc_type_text(text="...")` |
| Keyboard shortcuts | `mcp_uacc_hotkey(keys=["ctrl","s"])` |
| Launch an app | `mcp_uacc_launch_app(name_or_path="...")` |
| Focus a window | `mcp_uacc_focus_window(title="...")` |
## ⚡ UACC Planner MC (Mandatory Tool Selector)

**MANDATORY FOR ALL AI AGENTS**: Before initiating any UACC interactions (`click`, `type_text`, `paint_image`, `paint_preset`, `execute_actions`, etc.), you **MUST call `uacc_planner` first** to determine the optimal tool sequence, safety parameters, and bounding constraints for your task:

1. **Drawing / Art**: Use `uacc_planner` to set canvas bounds, stroke caps, and tracing strategy before invoking `paint_image` or `paint_preset`.
2. **UI Navigation**: Use `uacc_planner` then `get_screen_info` + `click_element` for fast textual targeting over raw vision.
3. **Batch Actions**: Use `uacc_planner` to group mouse/keyboard events in `execute_actions` for single rapid transactions.
4. **App Launch & Control**: Use `uacc_planner` to schedule `launch_app` followed by `type_text` or `hotkey`.

## Why

- MCP tools work in any agent (Hermes, Claude Code, OpenCode, OpenClaw, Cursor)
- No dependency on the local Python venv
- No script maintenance burden
- The tools handle human-like mouse movement, Bézier curves, timing, and error recovery built-in
- Safe mode is already configured — destructive actions are blocked

## Hermes config

The UACC MCP server is already wired up in Hermes via `hermes mcp add uacc -- python -m uacc.mcp`. If the tools aren't appearing, run `hermes mcp restart` or check `hermes mcp list`.

## 💾 Workflow Memory — Persistent Automation

UACC can **remember** multi-step automation sequences as reusable workflows. Any agent can save, list, inspect, delete, and replay them.

### MCP Tools

| Tool | What it does |
|---|---|
| `create_workflow(name, steps, description?)` | Save a named sequence of tool calls |
| `list_workflows(tag?)` | List all saved workflows, optionally by tag |
| `get_workflow(name)` | Inspect a workflow's full step definitions |
| `delete_workflow(name)` | Remove a workflow |
| `run_workflow(name)` | Execute a workflow step-by-step (replays every tool call) |

### Example — Saving a workflow

```json
{
  "tool": "create_workflow",
  "params": {
    "name": "open_notepad_type_hello",
    "description": "Launch Notepad and type Hello World",
    "tags": ["notepad", "demo"],
    "steps": [
      {"tool": "launch_app", "params": {"name_or_path": "notepad"}},
      {"tool": "wait_for_element", "params": {"name": "Untitled - Notepad"}},
      {"tool": "type_text", "params": {"text": "Hello from UACC workflow!"}}
    ]
  }
}
```

### Example — Running a saved workflow

```json
{"tool": "run_workflow", "params": {"name": "open_notepad_type_hello"}}
```

### Storage

Workflows are stored as JSON files under `~/.uacc/workflows/`. They survive agent restarts and are shared across sessions. You can also edit them manually if needed.

### Tips

- Name workflows descriptively so other agents can discover them
- Use tags like `"office"`, `"browser"`, `"dev"`, `"setup"` for organisation
- Workflows can call any MCP tool (`click`, `type_text`, `hotkey`, `launch_app`, etc.)
- After running, the workflow's `run_count` is incremented (useful to see which workflows are most used)

## Environment

- UACC root: `C:\Users\chris\Desktop\UACC`
- Venv: `C:\Users\chris\Desktop\UACC\.venv`
