# UACC — AI Agent Instructions

Use MCP tools (`mcp_uacc_*`) directly. Do NOT write separate Python scripts wrapping UACC.

## ⚡ Mandatory Planning & Precise Grounding
- **Always call `uacc_planner` first** before any UI interaction sequence.
- **NEVER guess raw `(x, y)` coordinates from plain screenshots.**
- For self-healing clicks, use `smart_click(target="...")` or `click(target="...")` (auto-resolves coordinates via accessibility tree, OCR, and VLM).
- For custom canvas UIs (e.g. video editors, games), use `screenshot(overlay="markers")` (numbered Set-of-Mark badges) or `screenshot(overlay="grid")` (A1–Z27 coordinate grid).
- UACC automatically initializes Windows Per-Monitor DPI Awareness (`SetProcessDpiAwareness(2)`), locking coordinates to 1:1 physical pixels.

## Workflow Memory & Background Tasks
- **Workflows**: Save and replay automations with `create_workflow`, `list_workflows`, `get_workflow`, `delete_workflow`, and `run_workflow` (`~/.uacc/workflows/`).
- **Background Tasks**: Run non-blocking repetitive tasks with `start_task`, check status with `get_task_status`, and stop with `cancel_task`.

See AGENTS.md for full details and examples.
