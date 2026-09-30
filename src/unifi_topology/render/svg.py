"""SVG rendering for orthogonal network diagrams."""

from __future__ import annotations

from ..model.topology import Edge, VpnTunnel, WanInfo
from . import _svg_dual_render, _svg_render_flow
from ._svg_node_types import _TYPE_COLORS, _safe_node_type
from ._svg_render_common import finish_svg_document, start_svg_document
from .svg_edges import _render_svg_edges
from .svg_icons import _load_icons
from .svg_labels import (
    _escape_text,
    _wrap_text,
)
from .svg_layout import (
    GroupBounds,
    _build_node_to_group_map,
    _svg_node_group_attrs,
)
from .svg_theme import DEFAULT_THEME, SvgOptions, SvgTheme
from .svg_wan import (
    _render_group_boundaries,
)

DualRenderGroups = _svg_dual_render.DualRenderGroups
SvgLayoutResult = _svg_render_flow.SvgLayoutResult


def _compute_svg_layout(
    edges: list[Edge],
    node_types: dict[str, str],
    options: SvgOptions,
    groups: dict[str, list[str]] | None,
    group_order: list[str] | None,
    wan_info: WanInfo | None,
    vpn_tunnels: list[VpnTunnel] | None = None,
) -> tuple[dict[str, tuple[float, float]], list[GroupBounds], float, float, bool]:
    layout = _svg_render_flow.compute_svg_layout(
        edges,
        node_types,
        options,
        groups,
        group_order,
        wan_info,
        vpn_tunnels,
    )
    return (
        layout.positions,
        layout.group_bounds_list,
        layout.width,
        layout.height,
        layout.use_grouped,
    )


def _svg_output_size(
    options: SvgOptions,
    width: float,
    height: float,
) -> tuple[float, float]:
    return options.width or width, options.height or height


def _render_svg_group_boundaries_if_needed(
    lines: list[str],
    *,
    use_grouped: bool,
    group_bounds_list: list[GroupBounds],
    theme: SvgTheme,
    options: SvgOptions,
    group_vlan_ids: dict[str, int] | None,
) -> None:
    if use_grouped and group_bounds_list:
        _render_group_boundaries(
            lines,
            group_bounds_list,
            theme,
            options,
            group_vlan_ids=group_vlan_ids,
        )


def _render_svg_topology(
    lines: list[str],
    *,
    edges: list[Edge],
    positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    icons: dict[str, str],
    options: SvgOptions,
    node_data: dict[str, dict[str, str]] | None,
    theme: SvgTheme,
    groups: dict[str, list[str]] | None,
    node_names: dict[str, str] | None = None,
) -> None:
    node_port_labels, _ = _render_svg_edges(
        lines, edges, positions, node_types, options, theme, node_names=node_names
    )
    _render_svg_nodes(
        lines,
        positions,
        node_types,
        node_port_labels,
        icons,
        options,
        node_data,
        theme,
        groups=groups,
        node_names=node_names,
    )


def render_svg(
    edges: list[Edge],
    *,
    node_types: dict[str, str],
    node_data: dict[str, dict[str, str]] | None = None,
    node_names: dict[str, str] | None = None,
    options: SvgOptions | None = None,
    theme: SvgTheme = DEFAULT_THEME,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
    group_vlan_ids: dict[str, int] | None = None,
    wan_info: WanInfo | None = None,
    vpn_tunnels: list[VpnTunnel] | None = None,
) -> str:
    options = options or SvgOptions()
    icons = _load_icons(theme.icon_set, decal_color=theme.text_primary)

    positions, group_bounds_list, width, height, use_grouped = _compute_svg_layout(
        edges, node_types, options, groups, group_order, wan_info, vpn_tunnels
    )
    out_width, out_height = _svg_output_size(options, width, height)

    lines = start_svg_document(
        width=width,
        height=height,
        out_width=out_width,
        out_height=out_height,
        theme=theme,
        options=options,
    )
    _render_svg_group_boundaries_if_needed(
        lines,
        use_grouped=use_grouped,
        group_bounds_list=group_bounds_list,
        theme=theme,
        options=options,
        group_vlan_ids=group_vlan_ids,
    )
    _render_svg_topology(
        lines,
        edges=edges,
        positions=positions,
        node_types=node_types,
        icons=icons,
        options=options,
        node_data=node_data,
        theme=theme,
        groups=groups,
        node_names=node_names,
    )
    _svg_render_flow.render_svg_gateway_overlays(
        lines=lines,
        wan_info=wan_info,
        vpn_tunnels=vpn_tunnels,
        node_types=node_types,
        positions=positions,
        options=options,
        theme=theme,
        canvas_height=height,
    )
    return finish_svg_document(lines)


def _append_svg_node_frame(
    lines: list[str],
    *,
    name: str,
    x: float,
    y: float,
    node_type: str,
    group_attrs: str,
    options: SvgOptions,
    theme: SvgTheme,
) -> None:
    safe_type = _safe_node_type(node_type)
    stroke = theme.node_stroke or _TYPE_COLORS[safe_type][1]
    lines.append(f"<g{group_attrs}>")
    lines.append(f"<title>{_escape_text(name)}</title>")
    lines.append(
        f'<rect x="{x}" y="{y}" width="{options.node_width}" height="{options.node_height}" '
        'fill="transparent" pointer-events="all" class="node-hitbox"/>'
    )
    lines.append(
        f'<rect x="{x}" y="{y}" width="{options.node_width}" height="{options.node_height}" '
        f'rx="6" ry="6" fill="url(#node-{safe_type})" stroke="{stroke}" stroke-width="1"/>'
    )


def _append_svg_node_icon(
    lines: list[str],
    *,
    x: float,
    y: float,
    node_type: str,
    icons: dict[str, str],
    options: SvgOptions,
) -> float:
    icon_href = icons.get(node_type, icons.get("other"))
    if not icon_href:
        return x + 10
    icon_x = x + 8
    icon_y = y + (options.node_height - options.icon_size) / 2
    lines.append(
        f'<image href="{icon_href}" x="{icon_x}" y="{icon_y}" '
        f'width="{options.icon_size}" height="{options.icon_size}"/>'
    )
    return icon_x + options.icon_size + 6


def _node_label_y(y: float, *, has_port_label: bool, options: SvgOptions) -> float:
    if has_port_label:
        return y + options.node_height - 6
    return y + options.node_height / 2 + options.font_size / 2 - 2


def _append_svg_node_port_label(
    lines: list[str],
    *,
    port_label: str | None,
    text_x: float,
    y: float,
    options: SvgOptions,
    theme: SvgTheme,
) -> None:
    if not port_label:
        return
    font_size = max(options.font_size - 2, 8)
    line_height = font_size + 2
    port_y = y + font_size + 4
    wrapped = _wrap_text(port_label)
    lines.append(
        f'<text x="{text_x}" y="{port_y}" class="node-port" '
        f'text-anchor="start" fill="{theme.text_secondary}" font-size="{font_size}">'
    )
    for idx, line in enumerate(wrapped):
        dy = 0 if idx == 0 else line_height
        lines.append(f'<tspan x="{text_x}" dy="{dy}">{_escape_text(line)}</tspan>')
    lines.append("</text>")


def _append_svg_node_label(
    lines: list[str],
    *,
    name: str,
    text_x: float,
    text_y: float,
    theme: SvgTheme,
) -> None:
    lines.append(
        f'<text x="{text_x}" y="{text_y}" class="node-label" fill="{theme.text_primary}" '
        f'text-anchor="start">{_escape_text(name)}</text>'
    )


def _render_svg_nodes(
    lines: list[str],
    positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    node_port_labels: dict[str, str],
    icons: dict[str, str],
    options: SvgOptions,
    node_data: dict[str, dict[str, str]] | None,
    theme: SvgTheme,
    *,
    groups: dict[str, list[str]] | None = None,
    node_names: dict[str, str] | None = None,
) -> None:
    names = node_names or {}
    node_to_group = _build_node_to_group_map(groups) if groups else {}
    for node_id, (x, y) in positions.items():
        display_name = names.get(node_id, node_id)
        node_type = node_types.get(node_id, "other")
        group_name = node_to_group.get(node_id)
        group_attrs = _svg_node_group_attrs(node_data, node_id, node_type, group_name)
        _append_svg_node_frame(
            lines,
            name=display_name,
            x=x,
            y=y,
            node_type=node_type,
            group_attrs=group_attrs,
            options=options,
            theme=theme,
        )
        text_x = _append_svg_node_icon(
            lines,
            x=x,
            y=y,
            node_type=node_type,
            icons=icons,
            options=options,
        )
        port_label = node_port_labels.get(node_id)
        _append_svg_node_port_label(
            lines,
            port_label=port_label,
            text_x=text_x,
            y=y,
            options=options,
            theme=theme,
        )
        _append_svg_node_label(
            lines,
            name=display_name,
            text_x=text_x,
            text_y=_node_label_y(y, has_port_label=bool(port_label), options=options),
            theme=theme,
        )
        lines.append("</g>")


# --- Dual rendering ---


def _groups_from_vlan_node_map(
    vlan_node_map: dict[str, int | None],
    vlan_names: dict[int, str] | None = None,
) -> tuple[dict[str, list[str]], list[str], dict[str, int]]:
    dual_groups = _svg_dual_render._groups_from_vlan_node_map(vlan_node_map, vlan_names)
    return dual_groups.groups, dual_groups.group_order, dual_groups.group_vlan_ids


def _dual_render_fn(isometric: bool):
    if isometric:
        from .svg_isometric import render_svg_isometric

        return render_svg_isometric
    return render_svg


def render_dual(
    edges: list[Edge],
    *,
    node_types: dict[str, str],
    node_names: dict[str, str] | None = None,
    options: SvgOptions | None = None,
    theme: SvgTheme = DEFAULT_THEME,
    vlan_names: dict[int, str] | None = None,
    vlan_node_map: dict[str, int | None] | None = None,
    wan_info: WanInfo | None = None,
    vpn_tunnels: list[VpnTunnel] | None = None,
    isometric: bool = False,
) -> dict[str, str | None]:
    """Render both physical and VLAN-grouped SVGs from shared topology data.

    Returns {"physical": svg_str, "vlan": svg_str_or_none}.
    The "vlan" value is None when no VLAN data is available.
    """
    from ..model.edges import group_nodes_by_vlan

    options = options or SvgOptions()
    dual_groups = _svg_dual_render.resolve_dual_groups(
        edges=edges,
        vlan_names=vlan_names,
        vlan_node_map=vlan_node_map,
        group_nodes_by_vlan=group_nodes_by_vlan,
    )
    return _svg_dual_render.render_dual_svgs(
        edges,
        node_types=node_types,
        node_names=node_names,
        options=options,
        theme=theme,
        wan_info=wan_info,
        vpn_tunnels=vpn_tunnels,
        dual_groups=dual_groups,
        render_fn=_dual_render_fn(isometric),
    )
