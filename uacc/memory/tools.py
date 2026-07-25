"""
MCP Tool Wrappers for the Semantic Knowledge Graph.

Exposes cross-session memory as callable tools that agents
can use to remember, recall, and learn from past sessions.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from uacc.memory.semantic_graph import RelationType, SemanticGraph

logger = logging.getLogger(__name__)

_GRAPH: SemanticGraph | None = None


def _get_graph() -> SemanticGraph:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = SemanticGraph()
    return _GRAPH


def remember_action(
    app_name: str,
    action_name: str,
    element_label: str = "",
    result: str = "success",
    reasoning: str = "",
) -> str:
    """Record a successful action in the cross-session knowledge graph.

    The graph persists across agent sessions under ``~/.uacc/semantic_graph.json``,
    enabling UACC to remember UI patterns from previous runs.

    Args:
        app_name: Application the action was performed in (e.g. "Notepad", "Chrome").
        action_name: The action performed (e.g. "click", "type", "hotkey").
        element_label: Text label of the target UI element (e.g. "Save", "Close").
        result: "success" or "failure".
        reasoning: Why this action was performed (for future recall context).

    Returns:
        JSON summary of what was recorded.
    """
    graph = _get_graph()
    graph.record_action_sequence(app_name, action_name, element_label, result)

    if reasoning:
        app_id = app_name.lower().replace(" ", "_")
        app = graph.find_entity(app_name, "app")
        if app:
            app.properties.setdefault("reasoning_history", [])
            app.properties["reasoning_history"].append({
                "action": action_name,
                "reasoning": reasoning,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            if len(app.properties["reasoning_history"]) > 50:
                app.properties["reasoning_history"] = app.properties["reasoning_history"][-50:]

    graph.save()

    return json.dumps({
        "success": True,
        "recorded": {
            "app": app_name,
            "action": action_name,
            "element": element_label,
            "result": result,
        },
        "graph_stats": graph.summary(),
    })


def query_knowledge(app_name: str) -> str:
    """Query what UACC knows about an application from past sessions.

    Returns known UI patterns, elements, action types, and the last-seen
    timestamp for the given application. Helps the agent understand what
    to expect when interacting with a familiar app.

    Args:
        app_name: Application name to look up (e.g. "Notepad", "Chrome").

    Returns:
        JSON with known patterns, elements, and action history.
    """
    graph = _get_graph()
    patterns = graph.get_app_patterns(app_name)

    if not patterns:
        return json.dumps({
            "success": True,
            "known": False,
            "app": app_name,
            "message": f"No prior knowledge for '{app_name}'",
        })

    return json.dumps({
        "success": True,
        "known": True,
        "app": patterns["name"],
        "patterns": patterns["patterns"],
        "last_seen": patterns.get("last_seen", ""),
        "graph_stats": graph.summary(),
    })


def recall_related_apps(app_name: str) -> str:
    """Find applications related to the given app via the knowledge graph.

    Uses SIMILAR_TO relationships and shared UI element patterns
    to discover related apps. Useful when the agent needs to apply
    knowledge from one app to a similar one.

    Args:
        app_name: Application name to find related apps for.

    Returns:
        JSON with a list of related applications.
    """
    graph = _get_graph()
    similar = graph.find_similar_apps(app_name)

    entity = graph.find_entity(app_name)
    if not entity and not similar:
        return json.dumps({
            "success": True,
            "app": app_name,
            "related_apps": [],
            "message": f"No related apps found for '{app_name}'",
        })

    app_id = entity.id if entity else app_name.lower().replace(" ", "_")
    related = set(similar)

    for rel in graph.query(app_id):
        target_name = ""
        target = graph._entities.get(rel.target_id)
        if target and target.entity_type == "app" and target.name != app_name:
            target_name = target.name
        elif rel.source_id != app_id:
            source = graph._entities.get(rel.source_id)
            if source and source.entity_type == "app" and source.name != app_name:
                target_name = source.name
        if target_name:
            related.add(target_name)

    return json.dumps({
        "success": True,
        "app": app_name,
        "related_apps": sorted(related),
        "total": len(related),
    })


def memory_summary() -> str:
    """Get statistics about the cross-session knowledge graph.

    Shows how many apps, elements, and relationships UACC has
    learned across all sessions.

    Returns:
        JSON with entity and relation counts.
    """
    graph = _get_graph()
    return json.dumps({
        "success": True,
        "memory": graph.summary(),
    })


def get_app_action_history(app_name: str, limit: int = 10) -> str:
    """Get the action history for a specific application.

    Args:
        app_name: Application name.
        limit: Maximum number of history entries.

    Returns:
        JSON with recent actions and reasoning for the app.
    """
    graph = _get_graph()
    entity = graph.find_entity(app_name, "app")
    if not entity:
        return json.dumps({
            "success": True,
            "app": app_name,
            "history": [],
            "message": f"No history for '{app_name}'",
        })

    history = entity.properties.get("reasoning_history", [])
    return json.dumps({
        "success": True,
        "app": entity.name,
        "history": history[-limit:],
        "total_entries": len(history),
    })


def record_strategy_performance(
    app_name: str,
    strategy_name: str,
    target: str,
    success: bool,
    duration_ms: int,
) -> str:
    """Record which strategy succeeded or failed for a specific app/element pair.

    Used by the adaptive self-healing engine to learn the optimal
    strategy ordering per application over time.

    Args:
        app_name: Application name.
        strategy_name: Strategy name (e.g. "accessibility", "ocr", "vision").
        target: The target element label.
        success: Whether the strategy succeeded.
        duration_ms: How long the strategy took in milliseconds.

    Returns:
        JSON confirmation.
    """
    graph = _get_graph()
    app_id = app_name.lower().replace(" ", "_")
    strategy_id = f"{app_id}__strategy_{strategy_name}"

    graph.ensure_entity(
        strategy_id,
        f"strategy:{strategy_name}",
        "strategy",
        properties={
            "app": app_name,
            "strategy": strategy_name,
            "success_count": 1 if success else 0,
            "failure_count": 0 if success else 1,
            "total_duration_ms": duration_ms,
            "avg_duration_ms": duration_ms,
        },
    )
    graph.add_relation(
        app_id, strategy_id,
        RelationType.FOLLOWED_BY,
        weight=1.0 if success else 0.3,
        properties={"target": target, "success": success, "duration_ms": duration_ms},
    )
    graph.save()

    return json.dumps({
        "success": True,
        "recorded": {
            "app": app_name,
            "strategy": strategy_name,
            "target": target,
            "success": success,
        },
    })
