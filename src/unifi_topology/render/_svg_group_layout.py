"""Private helpers for grouped SVG layouts and node group attributes."""

from __future__ import annotations

from dataclasses import dataclass

from ..model.topology import Edge
from ._svg_node_attrs import _svg_node_group_attrs as _svg_node_group_attrs
from ._svg_tree_layout import _layout_nodes, _layout_nodeset
from .svg_theme import SvgOptions

__all__ = [
    "GroupBounds",
    "_assign_nodes_to_groups",
    "_build_node_to_group_map",
    "_compute_group_bounds",
    "_filter_edges_for_group",
    "_layout_grouped_nodes",
    "_resolve_group_order",
    "_svg_node_group_attrs",
]


@dataclass(frozen=True)
class GroupBounds:
    name: str
    x: float
    y: float
    width: float
    height: float


def _assign_nodes_to_groups(
    nodes: set[str],
    groups: dict[str, list[str]],
) -> dict[str, str]:
    """Map each node to its group name."""
    node_to_group: dict[str, str] = {}
    for group_name, members in groups.items():
        for node in members:
            if node in nodes:
                node_to_group[node] = group_name
    return node_to_group


def _resolve_group_order(
    groups: dict[str, list[str]],
    group_order: list[str] | None,
) -> list[str]:
    """Return ordered list of group names."""
    if group_order:
        return [group_name for group_name in group_order if group_name in groups]
    return sorted(groups.keys())


def _filter_edges_for_group(
    edges: list[Edge],
    group_nodes: set[str],
) -> list[Edge]:
    """Return edges where both endpoints are in the group."""
    return [edge for edge in edges if edge.left in group_nodes and edge.right in group_nodes]


def _compute_group_bounds(
    group_name: str,
    positions: dict[str, tuple[float, float]],
    options: SvgOptions,
    offset_x: float,
) -> GroupBounds:
    """Compute bounding rectangle for a group."""
    if not positions:
        return GroupBounds(group_name, offset_x, 0, 100, 100)
    xs = [x for x, _ in positions.values()]
    ys = [y for _, y in positions.values()]
    min_x = min(xs) - options.group_padding
    min_y = min(ys) - options.group_padding
    max_x = max(xs) + options.node_width + options.group_padding
    max_y = max(ys) + options.node_height + options.group_padding
    return GroupBounds(group_name, min_x, min_y, max_x - min_x, max_y - min_y)


def _layout_grouped_nodes(
    edges: list[Edge],
    node_types: dict[str, str],
    options: SvgOptions,
    groups: dict[str, list[str]],
    group_order: list[str] | None,
) -> tuple[dict[str, tuple[float, float]], list[GroupBounds], int, int]:
    """Lay out the ordinary tree, then draw each group as a box around its members.

    Positions, parent/child hierarchy and edge routing are those of the
    physical layout; a group only pulls its leaf siblings into one contiguous
    block (see ``_leaf_blocks``) so its box has a clear place under the parent.
    Nodes that belong to no group simply get no box.
    """
    all_nodes = _layout_nodeset(edges, node_types)
    ordered_groups = _resolve_group_order(groups, group_order)
    node_to_group = _assign_nodes_to_groups(all_nodes, groups)
    positions, width, height = _layout_nodes(
        edges, node_types, options, node_to_group, ordered_groups
    )
    group_bounds_list: list[GroupBounds] = []
    for group_name in ordered_groups:
        member_positions = {
            node: positions[node] for node in groups.get(group_name, []) if node in positions
        }
        if member_positions:
            group_bounds_list.append(
                _compute_group_bounds(group_name, member_positions, options, 0.0)
            )
    return positions, group_bounds_list, int(width), int(height)


def _build_node_to_group_map(groups: dict[str, list[str]]) -> dict[str, str]:
    """Build reverse mapping from node to group name."""
    result: dict[str, str] = {}
    for group_name, members in groups.items():
        for node in members:
            result[node] = group_name
    return result
