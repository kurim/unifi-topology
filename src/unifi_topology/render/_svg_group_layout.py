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
    "_layout_single_group",
    "_offset_positions",
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


def _layout_single_group(
    edges: list[Edge],
    group_nodes: set[str],
    node_types: dict[str, str],
    options: SvgOptions,
) -> tuple[dict[str, tuple[float, float]], float, float]:
    """Layout nodes within a single group, return positions and dimensions."""
    group_edges = _filter_edges_for_group(edges, group_nodes)
    group_node_types = {name: node_types.get(name, "other") for name in group_nodes}
    positions, width, height = _layout_nodes(group_edges, group_node_types, options)
    return positions, float(width), float(height)


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


def _offset_positions(
    positions: dict[str, tuple[float, float]],
    dx: float,
    dy: float,
) -> dict[str, tuple[float, float]]:
    """Shift all positions by (dx, dy)."""
    return {name: (x + dx, y + dy) for name, (x, y) in positions.items()}


def _backbone_node_types(
    node_types: dict[str, str],
    node_to_group: dict[str, str],
) -> dict[str, str]:
    """Node types for nodes that were not pulled into any VLAN group."""
    return {name: node_type for name, node_type in node_types.items() if name not in node_to_group}


def _backbone_edges(edges: list[Edge], node_to_group: dict[str, str]) -> list[Edge]:
    """Edges where neither endpoint was pulled into a VLAN group."""
    return [
        edge for edge in edges if edge.left not in node_to_group and edge.right not in node_to_group
    ]


def _layout_grouped_nodes(
    edges: list[Edge],
    node_types: dict[str, str],
    options: SvgOptions,
    groups: dict[str, list[str]],
    group_order: list[str] | None,
) -> tuple[dict[str, tuple[float, float]], list[GroupBounds], int, int]:
    """Layout VLAN-grouped nodes in boxed lanes below the physical backbone.

    Nodes left out of every group -- typically infrastructure devices,
    whose trunk/uplink ports carry traffic for every VLAN and so can't be
    assigned to a single group -- keep the plain tree layout's position
    with no box, rather than being swept into a generic boundary. Only the
    VLAN lanes are new relative to the physical layout.
    """
    all_nodes = _layout_nodeset(edges, node_types)
    ordered_groups = _resolve_group_order(groups, group_order)
    node_to_group = _assign_nodes_to_groups(all_nodes, groups)

    backbone_positions, backbone_width, backbone_height = _layout_nodes(
        _backbone_edges(edges, node_to_group),
        _backbone_node_types(node_types, node_to_group),
        options,
    )
    all_positions: dict[str, tuple[float, float]] = dict(backbone_positions)
    lane_y = (
        float(backbone_height) + options.group_gap if backbone_positions else float(options.padding)
    )

    group_bounds_list: list[GroupBounds] = []
    current_x = float(options.padding)
    max_lane_height = 0.0

    for group_name in ordered_groups:
        group_nodes = set(groups.get(group_name, [])) & all_nodes
        if not group_nodes:
            continue
        positions, width, height = _layout_single_group(edges, group_nodes, node_types, options)
        offset_positions = _offset_positions(
            positions, current_x - options.padding, lane_y - options.padding
        )
        all_positions.update(offset_positions)
        group_bounds_list.append(
            _compute_group_bounds(group_name, offset_positions, options, current_x)
        )
        current_x += width + options.group_gap
        max_lane_height = max(max_lane_height, height)

    lanes_width = current_x - options.group_gap + options.padding if group_bounds_list else 0.0
    total_width = int(max(backbone_width, lanes_width))
    total_height = int(lane_y + max_lane_height) if group_bounds_list else int(backbone_height)
    return all_positions, group_bounds_list, total_width, total_height


def _build_node_to_group_map(groups: dict[str, list[str]]) -> dict[str, str]:
    """Build reverse mapping from node to group name."""
    result: dict[str, str] = {}
    for group_name, members in groups.items():
        for node in members:
            result[node] = group_name
    return result
