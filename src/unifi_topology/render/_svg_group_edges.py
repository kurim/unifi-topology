"""Draw one edge into a group's box instead of one edge per member."""

from __future__ import annotations

from dataclasses import replace

from ..model.topology import Edge
from ._svg_group_layout import GroupBounds, _build_node_to_group_map
from .svg_iso_geometry import IsoLayout
from .svg_theme import SvgOptions

__all__ = [
    "collapse_group_edges",
    "group_anchor_key",
    "isometric_group_anchors",
    "orthogonal_group_anchors",
]


def group_anchor_key(group_name: str) -> str:
    """Stand-in node id for a group's box as an edge endpoint."""
    return f"::group::{group_name}"


def collapse_group_edges(edges: list[Edge], groups: dict[str, list[str]]) -> list[Edge]:
    """Replace the edges from one outside node into a group by a single edge.

    A box with a dozen clients under one switch or access point would
    otherwise get a dozen near-identical connectors. The kept edge ends at
    the group's anchor (see ``group_anchor_key``) and carries the first
    member edge's styling (wireless, PoE, VLAN colours). Edges inside a group,
    or between two nodes outside every group, are kept as they are.
    """
    node_to_group = _build_node_to_group_map(groups)
    seen: set[tuple[str, str]] = set()
    collapsed: list[Edge] = []
    for edge in edges:
        group = node_to_group.get(edge.right)
        if group is None or node_to_group.get(edge.left) == group:
            collapsed.append(edge)
            continue
        key = (edge.left, group)
        if key not in seen:
            seen.add(key)
            collapsed.append(replace(edge, right=group_anchor_key(group), label=None))
    return collapsed


def orthogonal_group_anchors(
    group_bounds_list: list[GroupBounds], options: SvgOptions
) -> dict[str, tuple[float, float]]:
    """Top-left of a node-sized slot whose top edge centre is the box's top edge centre."""
    return {
        group_anchor_key(bounds.name): (
            bounds.x + bounds.width / 2 - options.node_width / 2,
            bounds.y,
        )
        for bounds in group_bounds_list
    }


def isometric_group_anchors(
    grid_positions: dict[str, tuple[float, float]],
    groups: dict[str, list[str]],
    layout: IsoLayout,
    options: SvgOptions,
) -> dict[str, tuple[float, float]]:
    """Grid point at the middle of each group's near (low-row) side, where edges land."""
    padding = options.group_padding / layout.step_width + 0.5
    anchors: dict[str, tuple[float, float]] = {}
    for name, members in groups.items():
        cells = [grid_positions[node] for node in members if node in grid_positions]
        if not cells:
            continue
        gxs = [gx for gx, _gy in cells]
        min_gx = min(gxs) - padding
        max_gx = max(gxs) + layout.grid_spacing_x + padding
        anchors[group_anchor_key(name)] = (
            (min_gx + max_gx) / 2,
            # half a cell further out: the edge end is anchored at a tile's front
            min(gy for _gx, gy in cells) - padding - 0.5,
        )
    return anchors
