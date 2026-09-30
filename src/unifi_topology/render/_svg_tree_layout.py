"""Private helpers for tree-based SVG node layout."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from ..model.topology import Edge
from ._svg_node_types import _TYPE_ORDER
from .svg_theme import SvgOptions


def _layout_nodes(
    edges: list[Edge], node_types: dict[str, str], options: SvgOptions
) -> tuple[dict[str, tuple[float, float]], int, int]:
    positions_index, levels = _tree_layout_indices(edges, node_types, options.max_nodes_per_row)
    positions: dict[str, tuple[float, float]] = {}
    max_index = max(positions_index.values(), default=0.0)
    leaf_count = max(1, math.ceil(max_index) + 1)
    for name, idx in positions_index.items():
        level = levels.get(name, 0)
        x = options.padding + idx * (options.node_width + options.h_gap)
        y = options.padding + level * (options.node_height + options.v_gap)
        positions[name] = (x, y)

    width = (
        options.padding * 2
        + leaf_count * options.node_width
        + max(0, leaf_count - 1) * options.h_gap
    )
    max_level = max(levels.values(), default=0)
    height = (
        options.padding * 2
        + (max_level + 1) * options.node_height
        + max(0, max_level) * options.v_gap
    )
    return positions, width, height


def _layout_nodeset(edges: list[Edge], node_types: dict[str, str]) -> set[str]:
    nodes = set(node_types.keys())
    for edge in edges:
        nodes.add(edge.left)
        nodes.add(edge.right)
    return nodes


def _build_children_maps(
    edges: list[Edge], nodes: set[str]
) -> tuple[dict[str, list[str]], dict[str, int]]:
    children: dict[str, list[str]] = {name: [] for name in nodes}
    incoming: dict[str, int] = {name: 0 for name in nodes}
    for edge in edges:
        children[edge.left].append(edge.right)
        incoming[edge.right] = incoming.get(edge.right, 0) + 1
    return children, incoming


def _sort_key_for_nodes(node_types: dict[str, str]) -> Callable[[str], tuple[int, str]]:
    type_order = {t: i for i, t in enumerate(_TYPE_ORDER)}

    def sort_key(name: str) -> tuple[int, str]:
        return (type_order.get(node_types.get(name, "other"), 99), name.lower())

    return sort_key


def _sort_children(children: dict[str, list[str]], sort_key) -> None:
    for child_list in children.values():
        child_list.sort(key=sort_key)


def _gateway_roots(node_types: dict[str, str]) -> list[str]:
    return [name for name, node_type in node_types.items() if node_type == "gateway"]


def _zero_incoming_roots(nodes: set[str], incoming: dict[str, int]) -> list[str]:
    return [name for name in nodes if incoming.get(name, 0) == 0]


def _resolve_roots(
    nodes: set[str],
    incoming: dict[str, int],
    node_types: dict[str, str],
    sort_key,
) -> list[str]:
    gateways = _gateway_roots(node_types)
    roots = gateways or _zero_incoming_roots(nodes, incoming) or list(nodes)
    return sorted(roots, key=sort_key)


@dataclass
class _LayoutState:
    levels: dict[str, int] = field(default_factory=dict)
    positions_index: dict[str, float] = field(default_factory=dict)
    visited: set[str] = field(default_factory=set)
    cursor: int = 0


def _leaf_position(state: _LayoutState, node: str) -> float:
    idx = float(state.cursor)
    state.cursor += 1
    state.positions_index[node] = idx
    return idx


def _record_layout_level(state: _LayoutState, node: str, level: int) -> None:
    state.levels[node] = min(state.levels.get(node, level), level)


def _child_position(
    child: str,
    level: int,
    children: dict[str, list[str]],
    state: _LayoutState,
    max_nodes_per_row: int | None,
) -> float:
    if child in state.visited:
        return state.positions_index.get(child, float(state.cursor))
    return _dfs_position(child, level + 1, children, state, max_nodes_per_row)


def _wrapped_leaf_positions(
    leaf_children: list[str],
    level: int,
    state: _LayoutState,
    max_nodes_per_row: int,
) -> list[float]:
    """Lay siblings with no children of their own out in a wrapped grid.

    Many leaves (e.g. clients on a switch) otherwise share one row that
    grows as wide as the group is large. Wrapping keeps the row width
    bounded and stacks the overflow into additional rows below the first,
    within the column range this group already occupies.
    """
    columns = min(len(leaf_children), max_nodes_per_row)
    base_col = state.cursor
    positions: list[float] = []
    for offset, leaf in enumerate(leaf_children):
        idx = float(base_col + offset % columns)
        row = offset // columns
        state.visited.add(leaf)
        state.positions_index[leaf] = idx
        _record_layout_level(state, leaf, level + 1 + row)
        positions.append(idx)
    state.cursor = base_col + columns
    return positions


def _child_indices(
    node: str,
    level: int,
    children: dict[str, list[str]],
    state: _LayoutState,
    max_nodes_per_row: int | None,
) -> list[float]:
    kids = children.get(node, [])
    if not max_nodes_per_row or max_nodes_per_row < 1:
        return [_child_position(child, level, children, state, max_nodes_per_row) for child in kids]
    wrappable = [child for child in kids if child not in state.visited and not children.get(child)]
    indices = [
        _child_position(child, level, children, state, max_nodes_per_row)
        for child in kids
        if child not in wrappable
    ]
    if len(wrappable) > max_nodes_per_row:
        indices.extend(_wrapped_leaf_positions(wrappable, level, state, max_nodes_per_row))
    else:
        indices.extend(
            _child_position(child, level, children, state, max_nodes_per_row) for child in wrappable
        )
    return indices


def _assign_position(node: str, child_indices: list[float], state: _LayoutState) -> float:
    if not child_indices:
        return _leaf_position(state, node)
    idx = sum(child_indices) / len(child_indices)
    state.positions_index[node] = idx
    return idx


def _dfs_position(
    node: str,
    level: int,
    children: dict[str, list[str]],
    state: _LayoutState,
    max_nodes_per_row: int | None = None,
) -> float:
    existing = state.positions_index.get(node)
    if existing is not None:
        return existing
    state.visited.add(node)
    _record_layout_level(state, node, level)
    child_indices = _child_indices(node, level, children, state, max_nodes_per_row)
    return _assign_position(node, child_indices, state)


def _layout_positions(
    nodes: set[str],
    children: dict[str, list[str]],
    *,
    roots: list[str],
    sort_key,
    max_nodes_per_row: int | None = None,
) -> tuple[dict[str, float], dict[str, int]]:
    state = _LayoutState()
    for root in roots:
        _dfs_position(root, 0, children, state, max_nodes_per_row)
    for node in sorted(nodes, key=sort_key):
        if node not in state.positions_index:
            _dfs_position(node, 0, children, state, max_nodes_per_row)
    return state.positions_index, state.levels


def _tree_layout_indices(
    edges: list[Edge],
    node_types: dict[str, str],
    max_nodes_per_row: int | None = None,
) -> tuple[dict[str, float], dict[str, int]]:
    nodes = _layout_nodeset(edges, node_types)
    children, incoming = _build_children_maps(edges, nodes)
    sort_key = _sort_key_for_nodes(node_types)
    _sort_children(children, sort_key)
    roots = _resolve_roots(nodes, incoming, node_types, sort_key)
    return _layout_positions(
        nodes,
        children,
        roots=roots,
        sort_key=sort_key,
        max_nodes_per_row=max_nodes_per_row,
    )
