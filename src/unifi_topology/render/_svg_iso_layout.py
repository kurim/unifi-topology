"""Private isometric layout and grid helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from ..model.topology import Edge
from ._svg_group_layout import (
    _assign_nodes_to_groups,
    _filter_edges_for_group,
    _resolve_group_order,
)
from ._svg_iso_district_layout import _iso_district_grid
from ._svg_iso_routing import edge_occupancy, edge_route
from ._svg_tree_layout import _layout_nodeset, _tree_layout_indices
from .svg_iso_geometry import IsoLayout, _iso_project, _iso_project_center
from .svg_theme import SvgOptions, SvgTheme

_ISO_NW_PADDING = 300
_ISO_VIEWPORT_EXPAND = 400
_ISO_GRID_EXTENT_PAD = 36


@dataclass(frozen=True)
class IsoLayoutPositions:
    layout: IsoLayout
    grid_positions: dict[str, tuple[float, float]]
    positions: dict[str, tuple[float, float]]
    width: float
    height: float
    offset_x: float
    offset_y: float


def _iso_layout(options: SvgOptions) -> IsoLayout:
    tile_width = options.node_width * 1.5
    iso_angle = math.radians(30.0)
    tile_height = tile_width * math.tan(iso_angle)
    step_width = tile_width
    step_height = tile_height
    grid_spacing_x = max(2, 1 + int(round(options.h_gap / max(tile_width, 1))))
    grid_spacing_y = max(2, 1 + int(round(options.v_gap / max(tile_height, 1))))
    padding = float(options.padding)
    tile_y_offset = tile_height / 2
    extra_pad = max(12.0, tile_width * 0.35)
    return IsoLayout(
        iso_angle=iso_angle,
        tile_width=tile_width,
        tile_height=tile_height,
        step_width=step_width,
        step_height=step_height,
        grid_spacing_x=grid_spacing_x,
        grid_spacing_y=grid_spacing_y,
        padding=padding,
        tile_y_offset=tile_y_offset,
        extra_pad=extra_pad,
    )


def _tree_grid_positions(
    layout: IsoLayout,
    positions_index: Mapping[str, float],
    levels: Mapping[str, int],
) -> dict[str, tuple[float, float]]:
    """Sibling order along one grid axis, tree depth along the other."""
    grid_positions: dict[str, tuple[float, float]] = {}
    for name, idx in positions_index.items():
        level = levels.get(name, 0)
        gx = round(idx * layout.grid_spacing_x)
        gy = round(float(level) * layout.grid_spacing_y)
        grid_positions[name] = (float(gx), float(gy))
    return grid_positions


def _project_grid(
    layout: IsoLayout,
    grid_positions: Mapping[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    return {name: _iso_project_center(layout, gx, gy) for name, (gx, gy) in grid_positions.items()}


def _project_iso_positions(
    layout: IsoLayout,
    positions_index: Mapping[str, float],
    levels: Mapping[str, int],
) -> tuple[dict[str, tuple[float, float]], dict[str, tuple[float, float]]]:
    grid_positions = _tree_grid_positions(layout, positions_index, levels)
    return grid_positions, _project_grid(layout, grid_positions)


def _layout_district_at_offset(
    edges: list[Edge],
    node_types: dict[str, str],
    subset: set[str],
    max_nodes_per_row: int | None,
    current_x: float,
) -> tuple[dict[str, float], dict[str, int], float]:
    """Lay out one node subset as its own tree, offset into its own
    column range starting at current_x. Returns (positions, levels, width).
    """
    subset_edges = _filter_edges_for_group(edges, subset)
    subset_types = {name: node_types.get(name, "other") for name in subset}
    positions, levels = _tree_layout_indices(subset_edges, subset_types, max_nodes_per_row)
    width = max(positions.values(), default=0.0) + 1
    offset_positions = {name: current_x + idx for name, idx in positions.items()}
    return offset_positions, levels, width


def _grouped_tree_layout_indices(
    edges: list[Edge],
    node_types: dict[str, str],
    groups: dict[str, list[str]],
    group_order: list[str] | None,
    max_nodes_per_row: int | None,
) -> tuple[dict[str, float], dict[str, int]]:
    """Like _tree_layout_indices, but lays each group out in its own
    column range (its own district) instead of interleaving every node
    into one tree. Each group keeps its own sibling-order/depth layout,
    including row-wrapping, and groups are placed left to right.

    Nodes left out of every group -- typically infrastructure devices,
    whose trunk/uplink ports carry traffic for every VLAN -- are laid out
    first, at column 0, exactly as the plain (non-grouped) tree layout
    would place them. VLAN districts are appended to their right, so
    grouping only adds new districts rather than displacing the backbone.
    """
    all_nodes = _layout_nodeset(edges, node_types)
    ordered_groups = _resolve_group_order(groups, group_order)
    node_to_group = _assign_nodes_to_groups(all_nodes, groups)

    positions_index: dict[str, float] = {}
    levels: dict[str, int] = {}
    current_x = 0.0

    ungrouped = all_nodes - set(node_to_group.keys())
    if ungrouped:
        backbone_positions, backbone_levels, backbone_width = _layout_district_at_offset(
            edges, node_types, ungrouped, max_nodes_per_row, current_x
        )
        positions_index.update(backbone_positions)
        levels.update(backbone_levels)
        current_x += backbone_width + 1  # one empty column before the VLAN districts

    for group_name in ordered_groups:
        group_nodes = set(groups.get(group_name, [])) & all_nodes
        if not group_nodes:
            continue
        group_positions, group_levels, width = _layout_district_at_offset(
            edges, node_types, group_nodes, max_nodes_per_row, current_x
        )
        positions_index.update(group_positions)
        levels.update(group_levels)
        current_x += width + 1  # one empty column between districts

    return positions_index, levels


def _iso_grid_positions(
    layout: IsoLayout,
    edges: list[Edge],
    node_types: dict[str, str],
    options: SvgOptions,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
) -> dict[str, tuple[float, float]]:
    if options.iso_compact_layout:
        return _iso_district_grid(edges, node_types)
    if options.layout_mode == "grouped" and groups:
        positions_index, levels = _grouped_tree_layout_indices(
            edges, node_types, groups, group_order, options.max_nodes_per_row
        )
    else:
        positions_index, levels = _tree_layout_indices(edges, node_types, options.max_nodes_per_row)
    return _tree_grid_positions(layout, positions_index, levels)


def _route_corner_positions(
    layout: IsoLayout,
    edges: list[Edge],
    grid_positions: dict[str, tuple[float, float]],
    options: SvgOptions,
) -> list[tuple[float, float]]:
    """Where edge corners land, so the canvas can be sized to hold them.

    A corner is chosen in grid space and can sit outside the box the nodes span:
    screen x depends on ``gx - gy``, so a turn between two nodes that share that
    difference projects to one side of both. The viewport is computed from node
    positions, so without this the edge is drawn off-canvas and clipped (#69).
    """
    occupied = edge_occupancy(grid_positions, avoid_nodes=options.iso_route_around_nodes)
    points: list[tuple[float, float]] = []
    for edge in edges:
        src = grid_positions.get(edge.left)
        dst = grid_positions.get(edge.right)
        if src is None or dst is None:
            continue
        route = edge_route(src, dst, occupied)
        points.extend(_iso_project_center(layout, gx, gy) for gx, gy in route[1:-1])
    return points


def _position_extents(
    positions: dict[str, tuple[float, float]],
) -> tuple[float, float, float, float]:
    if not positions:
        return 0.0, 0.0, 0.0, 0.0
    xs, ys = zip(*positions.values())
    return min(xs), min(ys), max(xs), max(ys)


def _iso_offsets(
    layout: IsoLayout,
    min_x: float,
    min_y: float,
) -> tuple[float, float]:
    return (
        -min_x + layout.padding + _ISO_NW_PADDING,
        -min_y + layout.padding + layout.tile_y_offset + _ISO_NW_PADDING,
    )


def _apply_iso_offsets(
    positions: dict[str, tuple[float, float]],
    offset_x: float,
    offset_y: float,
) -> dict[str, tuple[float, float]]:
    return {name: (x + offset_x, y + offset_y) for name, (x, y) in positions.items()}


def _iso_viewport_size(
    layout: IsoLayout,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> tuple[float, float]:
    width = (
        max_x
        - min_x
        + layout.tile_width
        + layout.padding * 2
        + layout.extra_pad
        + _ISO_VIEWPORT_EXPAND
        + _ISO_NW_PADDING
    )
    height = (
        max_y
        - min_y
        + layout.tile_height
        + layout.padding * 2
        + layout.tile_y_offset
        + layout.extra_pad
        + _ISO_VIEWPORT_EXPAND
        + _ISO_NW_PADDING
    )
    return width, height


@dataclass(frozen=True)
class _Viewport:
    offset_x: float
    offset_y: float
    width: float
    height: float


def _corner_pixels(
    layout: IsoLayout,
    corners: list[tuple[float, float]],
    viewport: _Viewport,
) -> list[tuple[float, float]]:
    """Where corners land once drawn -- edges anchor at the tile front, not centre."""
    half_w = layout.tile_width / 2
    half_h = layout.tile_height / 2
    return [(x + viewport.offset_x + half_w, y + viewport.offset_y + half_h) for x, y in corners]


def _expand_viewport(
    viewport: _Viewport,
    points: list[tuple[float, float]],
    margin: float,
) -> _Viewport:
    """Shift and grow the canvas so every point sits inside it, with a margin.

    Returns the viewport untouched when nothing overflows, which is the common
    case: node tiles and their labels are already covered by the fixed padding.
    Only a routed corner reaching past the nodes forces a change.
    """
    if not points:
        return viewport
    xs = [x for x, _y in points]
    ys = [y for _x, y in points]
    shift_x = max(0.0, margin - min(xs))
    shift_y = max(0.0, margin - min(ys))
    return _Viewport(
        offset_x=viewport.offset_x + shift_x,
        offset_y=viewport.offset_y + shift_y,
        width=max(viewport.width + shift_x, max(xs) + shift_x + margin),
        height=max(viewport.height + shift_y, max(ys) + shift_y + margin),
    )


def _iso_layout_positions(
    edges: list[Edge],
    node_types: dict[str, str],
    options: SvgOptions,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
) -> IsoLayoutPositions:
    layout = _iso_layout(options)
    grid_positions = _iso_grid_positions(layout, edges, node_types, options, groups, group_order)
    positions = _project_grid(layout, grid_positions)
    min_x, min_y, max_x, max_y = _position_extents(positions)
    offset_x, offset_y = _iso_offsets(layout, min_x, min_y)
    width, height = _iso_viewport_size(layout, min_x, min_y, max_x, max_y)
    viewport = _Viewport(offset_x=offset_x, offset_y=offset_y, width=width, height=height)
    corners = _route_corner_positions(layout, edges, grid_positions, options)
    # Half a grid unit of slack: routed edges may ride a lane offset from
    # their corners, and the outermost lane must still land inside.
    margin = layout.padding + layout.step_width / 4
    viewport = _expand_viewport(viewport, _corner_pixels(layout, corners, viewport), margin)
    return IsoLayoutPositions(
        layout=layout,
        grid_positions=grid_positions,
        positions=_apply_iso_offsets(positions, viewport.offset_x, viewport.offset_y),
        width=viewport.width,
        height=viewport.height,
        offset_x=viewport.offset_x,
        offset_y=viewport.offset_y,
    )


def _iso_grid_extents(
    grid_positions: dict[str, tuple[float, float]],
) -> tuple[int, int, int, int] | None:
    if not grid_positions:
        return None
    gxs, gys = zip(*grid_positions.values())
    return (
        _grid_extent_start(min(gxs)),
        _grid_extent_end(max(gxs)),
        _grid_extent_start(min(gys)),
        _grid_extent_end(max(gys)),
    )


def _grid_extent_start(value: float) -> int:
    return int(math.floor(value)) - _ISO_GRID_EXTENT_PAD


def _grid_extent_end(value: float) -> int:
    return int(math.ceil(value)) + _ISO_GRID_EXTENT_PAD


def _iso_grid_line(
    layout: IsoLayout,
    start: tuple[float, float],
    end: tuple[float, float],
    grid_color: str,
    offset_x: float,
    offset_y: float,
) -> str:
    x1, y1 = _iso_project(layout, *start)
    x2, y2 = _iso_project(layout, *end)
    x1 += offset_x
    y1 += offset_y
    x2 += offset_x
    y2 += offset_y
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{grid_color}" stroke-width="0.6"/>'
    )


def _iso_grid_lines(
    grid_positions: dict[str, tuple[float, float]],
    layout: IsoLayout,
    offset_x: float,
    offset_y: float,
    grid_color: str = "#efefef",
) -> list[str]:
    extents = _iso_grid_extents(grid_positions)
    if extents is None:
        return []
    gx_start, gx_end, gy_start, gy_end = extents
    grid_lines: list[str] = []
    for gx in range(gx_start, gx_end + 1):
        grid_lines.append(
            _iso_grid_line(
                layout,
                (float(gx), float(gy_start)),
                (float(gx), float(gy_end)),
                grid_color,
                offset_x,
                offset_y,
            )
        )
    for gy in range(gy_start, gy_end + 1):
        grid_lines.append(
            _iso_grid_line(
                layout,
                (float(gx_start), float(gy)),
                (float(gx_end), float(gy)),
                grid_color,
                offset_x,
                offset_y,
            )
        )
    return grid_lines


def _render_iso_grid(
    lines: list[str],
    grid_positions: dict[str, tuple[float, float]],
    layout: IsoLayout,
    theme: SvgTheme,
    offset_x: float,
    offset_y: float,
) -> None:
    grid_lines = _iso_grid_lines(grid_positions, layout, offset_x, offset_y, theme.grid_color)
    if grid_lines:
        lines.append('<g class="iso-grid" opacity="0.7">')
        lines.extend(grid_lines)
        lines.append("</g>")
