"""Isometric SVG rendering for network diagrams."""

from __future__ import annotations

from ..model.topology import Edge, VpnTunnel, WanInfo
from . import _svg_iso_layout, _svg_iso_overlays
from ._svg_group_edges import isometric_group_anchors
from ._svg_group_layout import _build_node_to_group_map
from ._svg_render_common import finish_svg_document, render_at_gateway, start_svg_document
from .svg_icons import _build_decal_colors, _load_isometric_icons
from .svg_iso_edges import _render_iso_edges
from .svg_iso_geometry import IsoLayout
from .svg_iso_nodes import _render_iso_nodes
from .svg_theme import DEFAULT_THEME, SvgOptions, SvgTheme
from .svg_vpn import _render_iso_vpn_tunnels

IsoLayoutPositions = _svg_iso_layout.IsoLayoutPositions
_apply_iso_offsets = _svg_iso_layout._apply_iso_offsets
_iso_grid_extents = _svg_iso_layout._iso_grid_extents
_iso_grid_line = _svg_iso_layout._iso_grid_line
_iso_grid_lines = _svg_iso_layout._iso_grid_lines
_iso_layout = _svg_iso_layout._iso_layout
_iso_layout_positions = _svg_iso_layout._iso_layout_positions
_iso_offsets = _svg_iso_layout._iso_offsets
_iso_viewport_size = _svg_iso_layout._iso_viewport_size
_position_extents = _svg_iso_layout._position_extents
_project_iso_positions = _svg_iso_layout._project_iso_positions
_render_iso_grid = _svg_iso_layout._render_iso_grid

IsoGroupBounds = _svg_iso_overlays.IsoGroupBounds
_compute_iso_group_bounds = _svg_iso_overlays._compute_iso_group_bounds
_expand_viewbox_for_overlays = _svg_iso_overlays._expand_viewbox_for_overlays
_expand_viewbox_for_wan = _svg_iso_overlays._expand_viewbox_for_wan
_find_gateway_position = _svg_iso_overlays._find_gateway_position
_render_grouped_boundaries = _svg_iso_overlays._render_grouped_boundaries
_render_iso_group_boundaries = _svg_iso_overlays._render_iso_group_boundaries
_render_iso_wan_upstream = _svg_iso_overlays._render_iso_wan_upstream
_iso_group_parallelogram = _svg_iso_overlays._iso_group_parallelogram

__all__ = [
    "IsoGroupBounds",
    "IsoLayout",
    "IsoLayoutPositions",
    "_apply_iso_offsets",
    "_compute_iso_group_bounds",
    "_expand_viewbox_for_overlays",
    "_expand_viewbox_for_wan",
    "_find_gateway_position",
    "_iso_grid_extents",
    "_iso_grid_line",
    "_iso_grid_lines",
    "_iso_group_parallelogram",
    "_iso_layout",
    "_iso_layout_positions",
    "_iso_offsets",
    "_iso_output_size",
    "_iso_viewport_size",
    "_position_extents",
    "_project_iso_positions",
    "_render_grouped_boundaries",
    "_render_iso_boundaries_if_needed",
    "_render_iso_gateway_overlays",
    "_render_iso_grid",
    "_render_iso_group_boundaries",
    "_render_iso_nodes_and_edges",
    "_render_iso_wan_upstream",
    "render_svg_isometric",
]


def _render_iso_nodes_and_edges(
    lines: list[str],
    edges: list[Edge],
    *,
    positions: dict[str, tuple[float, float]],
    grid_positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    node_names: dict[str, str] | None = None,
    icons: dict[str, str],
    layout: IsoLayout,
    options: SvgOptions,
    theme: SvgTheme,
    offset_x: float,
    offset_y: float,
    groups: dict[str, list[str]] | None = None,
) -> None:
    node_port_labels: dict[str, str] = {}
    node_port_prefix: dict[str, str] = {}
    grouped = options.layout_mode == "grouped" and bool(groups)
    _render_iso_edges(
        lines,
        edges,
        positions=positions,
        grid_positions=grid_positions,
        node_types=node_types,
        layout=layout,
        theme=theme,
        offset_x=offset_x,
        offset_y=offset_y,
        node_port_labels=node_port_labels,
        node_port_prefix=node_port_prefix,
        node_names=node_names,
        avoid_nodes=options.iso_route_around_nodes,
        groups=groups if grouped else None,
        group_anchors=isometric_group_anchors(grid_positions, groups or {}, layout, options)
        if grouped
        else None,
    )
    _render_iso_nodes(
        lines,
        positions=positions,
        node_types=node_types,
        node_names=node_names,
        icons=icons,
        options=options,
        layout=layout,
        node_port_labels=node_port_labels,
        node_port_prefix=node_port_prefix,
        theme=theme,
        node_to_group=_build_node_to_group_map(groups) if grouped and groups else None,
    )


def _render_iso_gateway_overlays(
    lines: list[str],
    *,
    wan_info: WanInfo | None,
    vpn_tunnels: list[VpnTunnel] | None,
    node_types: dict[str, str],
    positions: dict[str, tuple[float, float]],
    layout: IsoLayout,
    options: SvgOptions,
    theme: SvgTheme,
) -> None:
    render_at_gateway(
        lines=lines,
        content=wan_info,
        node_types=node_types,
        positions=positions,
        find_gateway_position=_find_gateway_position,
        render=lambda doc_lines, info, gateway_pos: _render_iso_wan_upstream(
            doc_lines, info, gateway_pos, layout, options, theme
        ),
    )
    render_at_gateway(
        lines=lines,
        content=vpn_tunnels,
        node_types=node_types,
        positions=positions,
        find_gateway_position=_find_gateway_position,
        render=lambda doc_lines, tunnels, gateway_pos: _render_iso_vpn_tunnels(
            doc_lines,
            tunnels,
            gateway_pos,
            layout.tile_width,
            layout.tile_height,
            options,
            theme,
        ),
    )


def _iso_output_size(
    options: SvgOptions,
    view_width: float,
    view_height: float,
) -> tuple[int, int]:
    return options.width or int(view_width), options.height or int(view_height)


def _render_iso_boundaries_if_needed(
    lines: list[str],
    *,
    options: SvgOptions,
    groups: dict[str, list[str]] | None,
    group_order: list[str] | None,
    group_vlan_ids: dict[str, int] | None,
    grid_positions: dict[str, tuple[float, float]],
    layout: IsoLayout,
    offset_x: float,
    offset_y: float,
    theme: SvgTheme,
) -> None:
    if options.layout_mode != "grouped" or not groups:
        return
    _render_grouped_boundaries(
        lines,
        grid_positions,
        groups,
        group_order,
        group_vlan_ids,
        layout,
        offset_x,
        offset_y,
        options,
        theme,
    )


def render_svg_isometric(
    edges: list[Edge],
    *,
    node_types: dict[str, str],
    node_names: dict[str, str] | None = None,
    options: SvgOptions | None = None,
    theme: SvgTheme = DEFAULT_THEME,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
    group_vlan_ids: dict[str, int] | None = None,
    wan_info: WanInfo | None = None,
    vpn_tunnels: list[VpnTunnel] | None = None,
) -> str:
    """Render an isometric (2.5D) SVG network diagram.

    Same interface as :func:`~unifi_network_maps.render.render_svg` but produces
    a 30-degree isometric projection with 3D-style device tiles and grid floor.
    """
    options = options or SvgOptions()
    # Derived per-type decals darken each node's gradient, which vanishes on
    # dark fills; a theme can demand one flat decal colour instead.
    per_type_decals = None if theme.icon_decal_iso else _build_decal_colors(theme)
    decal_color = theme.icon_decal_iso or theme.icon_decal
    icons = _load_isometric_icons(theme.icon_set, decal_color, per_type_decals)
    layout_positions = _iso_layout_positions(edges, node_types, options, groups, group_order)
    layout = layout_positions.layout
    grid_positions = layout_positions.grid_positions
    positions = layout_positions.positions

    view_width, view_height = _expand_viewbox_for_overlays(
        layout_positions.width,
        layout_positions.height,
        wan_info=wan_info,
        vpn_tunnels=vpn_tunnels,
        node_types=node_types,
        positions=positions,
        layout=layout,
        options=options,
    )

    out_width, out_height = _iso_output_size(options, view_width, view_height)

    lines = start_svg_document(
        width=view_width,
        height=view_height,
        out_width=out_width,
        out_height=out_height,
        theme=theme,
        options=options,
        defs_prefix="iso",
        iso=True,
    )
    _render_iso_boundaries_if_needed(
        lines,
        options=options,
        groups=groups,
        group_order=group_order,
        group_vlan_ids=group_vlan_ids,
        grid_positions=grid_positions,
        layout=layout,
        offset_x=layout_positions.offset_x,
        offset_y=layout_positions.offset_y,
        theme=theme,
    )
    if options.iso_show_grid:
        _render_iso_grid(
            lines,
            grid_positions,
            layout,
            theme,
            layout_positions.offset_x,
            layout_positions.offset_y,
        )
    _render_iso_nodes_and_edges(
        lines,
        edges,
        positions=positions,
        grid_positions=grid_positions,
        node_types=node_types,
        node_names=node_names,
        icons=icons,
        layout=layout,
        options=options,
        theme=theme,
        offset_x=layout_positions.offset_x,
        offset_y=layout_positions.offset_y,
        groups=groups,
    )
    _render_iso_gateway_overlays(
        lines,
        wan_info=wan_info,
        vpn_tunnels=vpn_tunnels,
        node_types=node_types,
        positions=positions,
        layout=layout,
        options=options,
        theme=theme,
    )

    return finish_svg_document(lines)
