"""Private helpers for isometric node rendering."""

from __future__ import annotations

import math

from ._svg_iso_lighting import iso_face_colors, render_contact_shadow
from ._svg_node_types import _TYPE_COLORS, _safe_node_type
from .svg_iso_geometry import (
    IsoLayout,
    _iso_front_text_position,
    _iso_name_label_position,
    _iso_tile_points,
    _points_to_svg,
    _render_iso_text,
)
from .svg_labels import _escape_text, _format_port_label_lines
from .svg_layout import _svg_node_group_attrs
from .svg_theme import SvgOptions, SvgTheme


def _iso_node_polygons(
    x: float,
    y: float,
    tile_w: float,
    tile_h: float,
    node_depth: float,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]], list[tuple[float, float]]]:
    top = [
        (x + tile_w / 2, y),
        (x + tile_w, y + tile_h / 2),
        (x + tile_w / 2, y + tile_h),
        (x, y + tile_h / 2),
    ]
    left = [
        (x, y + tile_h / 2),
        (x + tile_w / 2, y + tile_h),
        (x + tile_w / 2, y + tile_h + node_depth),
        (x, y + tile_h / 2 + node_depth),
    ]
    right = [
        (x + tile_w, y + tile_h / 2),
        (x + tile_w / 2, y + tile_h),
        (x + tile_w / 2, y + tile_h + node_depth),
        (x + tile_w, y + tile_h / 2 + node_depth),
    ]
    return top, left, right


def _iso_render_faces(
    lines: list[str],
    *,
    top: list[tuple[float, float]],
    left: list[tuple[float, float]],
    right: list[tuple[float, float]],
    fill: str,
    stroke: str,
    left_fill: str,
    right_fill: str,
    node_depth: float,
) -> None:
    if node_depth > 0:
        lines.append(
            f'<polygon points="{" ".join(f"{px},{py}" for px, py in left)}" '
            f'fill="{left_fill}" stroke="{stroke}" stroke-width="1"/>'
        )
        lines.append(
            f'<polygon points="{" ".join(f"{px},{py}" for px, py in right)}" '
            f'fill="{right_fill}" stroke="{stroke}" stroke-width="1"/>'
        )
    lines.append(
        f'<polygon points="{" ".join(f"{px},{py}" for px, py in top)}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
    )


def _render_iso_port_label(
    lines: list[str],
    *,
    port_label: str,
    prefix: str,
    center_x: float,
    center_y: float,
    tile_w: float,
    tile_h: float,
    fill: str,
    stroke: str,
    left_fill: str,
    right_fill: str,
    font_size: int,
    theme: SvgTheme,
) -> tuple[float, float]:
    stack_depth = tile_h / 2
    label_center_x = center_x
    label_center_y = center_y - stack_depth
    top_points = _iso_tile_points(label_center_x, label_center_y, tile_w, tile_h)
    tile_points = _points_to_svg(top_points)
    bottom_points = [(px, py + stack_depth) for px, py in top_points]
    right_face = [top_points[1], top_points[2], bottom_points[2], bottom_points[1]]
    left_face = [top_points[3], top_points[2], bottom_points[2], bottom_points[3]]
    lines.append(
        f'<polygon class="label-tile-side" points="{" ".join(f"{px},{py}" for px, py in left_face)}" '
        f'fill="{left_fill}" stroke="{stroke}" stroke-width="1"/>'
    )
    lines.append(
        f'<polygon class="label-tile-side" points="{" ".join(f"{px},{py}" for px, py in right_face)}" '
        f'fill="{right_fill}" stroke="{stroke}" stroke-width="1"/>'
    )
    lines.append(
        f'<polygon class="label-tile" points="{tile_points}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
    )
    left_edge_top = top_points[0]
    left_edge_bottom = top_points[3]
    edge_len = math.hypot(
        left_edge_bottom[0] - left_edge_top[0],
        left_edge_bottom[1] - left_edge_top[1],
    )
    max_chars = max(6, int((edge_len * 0.85) / (font_size * 0.6)))
    front_lines = _format_port_label_lines(port_label, prefix=prefix, max_chars=max_chars)
    if front_lines:
        text_x, text_y, edge_angle = _iso_front_text_position(top_points, tile_w, tile_h)
        _render_iso_text(
            lines,
            text_x=text_x,
            text_y=text_y,
            angle=edge_angle,
            text_lines=front_lines,
            font_size=font_size,
            fill=theme.text_secondary,
        )
    return label_center_x, label_center_y


def _iso_front_face_label_position(
    left_face: list[tuple[float, float]],
    tile_height: float,
    font_size: int,
) -> tuple[float, float, float]:
    """Position label on the front (left) face of an isometric node."""
    top_left = left_face[0]
    top_right = left_face[1]
    bottom_right = left_face[2]
    bottom_left = left_face[3]

    center_x = (top_left[0] + top_right[0] + bottom_right[0] + bottom_left[0]) / 4
    center_y = (top_left[1] + top_right[1] + bottom_right[1] + bottom_left[1]) / 4
    angle = math.degrees(math.atan2(top_right[1] - top_left[1], top_right[0] - top_left[0]))
    label_x = center_x - tile_height * 0.01
    label_y = center_y + font_size * 0.5 + tile_height * 0.04 - 6
    return label_x, label_y, angle


def _icon_center(
    lines: list[str],
    *,
    port_label: str | None,
    port_prefix: str | None,
    center_x: float,
    center_y: float,
    tile_w: float,
    tile_h: float,
    fill: str,
    stroke: str,
    left_fill: str,
    right_fill: str,
    options: SvgOptions,
    theme: SvgTheme,
) -> tuple[float, float]:
    if not port_label:
        return center_x, center_y
    font_size = max(options.font_size - 2, 8)
    prefix = port_prefix or "switch"
    return _render_iso_port_label(
        lines,
        port_label=port_label,
        prefix=prefix,
        center_x=center_x,
        center_y=center_y,
        tile_w=tile_w,
        tile_h=tile_h,
        fill=fill,
        stroke=stroke,
        left_fill=left_fill,
        right_fill=right_fill,
        font_size=font_size,
        theme=theme,
    )


# Extra lift, in tile heights, for icons whose artwork does not sit at the bottom
# of its own frame. The isopacks access point is a tall radio mast that has to be
# raised so its base meets the tile; the UniFi set is normalized to a common frame
# (scripts/normalize_icon_viewbox.py), so the same lift leaves its flat ceiling
# disc hovering. Sets absent here get no extra lift.
_ICON_SET_EXTRA_LIFT: dict[str, dict[str, float]] = {
    "isometric": {"ap": 0.4},
    "modern": {"ap": 0.4},
}


_ICON_TILE_RATIO = 1.08


def _icon_y_offset(
    *,
    node_type: str,
    is_client: bool,
    port_label: str | None,
    tile_h: float,
    icon_set: str = "isometric",
) -> float:
    offset = tile_h * (0.02 if port_label else 0.04) + tile_h * 0.05
    offset += tile_h * _ICON_SET_EXTRA_LIFT.get(icon_set, {}).get(node_type, 0.0)
    if is_client:
        offset += tile_h * 0.05
    return offset


def _render_iso_node_icon(
    lines: list[str],
    *,
    icon_href: str | None,
    center_x: float,
    center_y: float,
    tile_w: float,
    tile_h: float,
    node_type: str,
    is_client: bool,
    port_label: str | None,
    port_prefix: str | None,
    fill: str,
    stroke: str,
    left_fill: str,
    right_fill: str,
    options: SvgOptions,
    theme: SvgTheme,
) -> None:
    """Render the icon for an isometric node, including port label tile if needed."""
    icon_center_x, icon_center_y = _icon_center(
        lines,
        port_label=port_label,
        port_prefix=port_prefix,
        center_x=center_x,
        center_y=center_y,
        tile_w=tile_w,
        tile_h=tile_h,
        fill=fill,
        stroke=stroke,
        left_fill=left_fill,
        right_fill=right_fill,
        options=options,
        theme=theme,
    )
    if not icon_href:
        return
    # Icons sit on the tile rather than filling it; much above this and they
    # overhang the top face they are meant to be standing on.
    iso_icon_size = min(tile_w, tile_h) * _ICON_TILE_RATIO
    icon_x = icon_center_x - iso_icon_size / 2
    icon_y = (
        icon_center_y
        - iso_icon_size / 2
        - _icon_y_offset(
            node_type=node_type,
            is_client=is_client,
            port_label=port_label,
            tile_h=tile_h,
            icon_set=theme.icon_set,
        )
    )
    lines.append(
        f'<image href="{icon_href}" x="{icon_x}" y="{icon_y}" '
        f'width="{iso_icon_size}" height="{iso_icon_size}" '
        f'preserveAspectRatio="xMidYMid meet" filter="url(#iso-icon-emboss)"/>'
    )


def _render_iso_node_name(
    lines: list[str],
    *,
    name: str,
    top: list[tuple[float, float]],
    left: list[tuple[float, float]],
    tile_w: float,
    tile_h: float,
    port_label: str | None,
    node_depth: float,
    font_size: int,
    theme: SvgTheme,
) -> None:
    """Render the name label for an isometric node."""
    if not port_label and node_depth > 0:
        name_x, name_y, name_angle = _iso_front_face_label_position(
            left,
            tile_height=tile_h,
            font_size=font_size,
        )
    else:
        name_x, name_y, name_angle = _iso_name_label_position(
            top,
            tile_width=tile_w,
            tile_height=tile_h,
            font_size=font_size,
        )
    name_transform = (
        f"translate({name_x} {name_y}) rotate({name_angle}) skewX(30) "
        f"translate({-name_x} {-name_y})"
    )
    lines.append(
        f'<text x="{name_x}" y="{name_y}" class="node-label" text-anchor="middle" '
        f'fill="{theme.text_primary}" font-size="{font_size}" '
        f'transform="{name_transform}">{_escape_text(name)}</text>'
    )


def _node_depth(port_label: str | None, layout: IsoLayout) -> float:
    if port_label:
        return 0.0
    return layout.tile_height * 0.15


def _render_iso_node(
    lines: list[str],
    *,
    node_id: str,
    name: str,
    x: float,
    y: float,
    node_type: str,
    icons: dict[str, str],
    options: SvgOptions,
    port_label: str | None,
    port_prefix: str | None,
    layout: IsoLayout,
    theme: SvgTheme,
    group_name: str | None = None,
) -> None:
    safe_type = _safe_node_type(node_type)
    stroke = theme.node_stroke or _TYPE_COLORS[safe_type][1]
    fill = f"url(#iso-node-{safe_type})"
    tile_w = layout.tile_width
    tile_h = layout.tile_height
    is_client = node_type in ("client", "client_cluster")
    node_depth = _node_depth(port_label, layout)

    group_attrs = _svg_node_group_attrs(None, node_id, node_type, group_name)
    lines.append(f"<g{group_attrs}>")
    lines.append(f"<title>{_escape_text(name)}</title>")
    if options.iso_lighting:
        render_contact_shadow(
            lines,
            x=x,
            y=y,
            tile_w=tile_w,
            tile_h=tile_h,
            node_depth=node_depth,
            filter_id="iso-contact-shadow",
        )
    top, left, right = _iso_node_polygons(x, y, tile_w, tile_h, node_depth)
    lines.append(
        f'<polygon points="{_points_to_svg(top)}" fill="transparent" '
        'pointer-events="all" class="node-hitbox"/>'
    )
    if options.iso_lighting:
        left_fill, right_fill = iso_face_colors(node_type, theme)
    else:
        left_fill = theme.node_side_left
        right_fill = theme.node_side_right
    _iso_render_faces(
        lines,
        top=top,
        left=left,
        right=right,
        fill=fill,
        stroke=stroke,
        left_fill=left_fill,
        right_fill=right_fill,
        node_depth=node_depth,
    )
    _render_iso_node_icon(
        lines,
        icon_href=icons.get(node_type, icons.get("other")),
        center_x=x + tile_w / 2,
        center_y=y + tile_h / 2,
        tile_w=tile_w,
        tile_h=tile_h,
        node_type=node_type,
        is_client=is_client,
        port_label=port_label,
        port_prefix=port_prefix,
        fill=fill,
        stroke=stroke,
        left_fill=left_fill,
        right_fill=right_fill,
        options=options,
        theme=theme,
    )
    _render_iso_node_name(
        lines,
        name=name,
        top=top,
        left=left,
        tile_w=tile_w,
        tile_h=tile_h,
        port_label=port_label,
        node_depth=node_depth,
        font_size=max(options.font_size - 2, 8),
        theme=theme,
    )
    lines.append("</g>")


def _render_iso_nodes(
    lines: list[str],
    *,
    positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    node_names: dict[str, str] | None = None,
    icons: dict[str, str],
    options: SvgOptions,
    layout: IsoLayout,
    node_port_labels: dict[str, str],
    node_port_prefix: dict[str, str],
    theme: SvgTheme,
    node_to_group: dict[str, str] | None = None,
) -> None:
    names = node_names or {}
    group_of = node_to_group or {}
    # Draw back-to-front so nearer nodes and their shadows overlap farther ones.
    ordered = sorted(positions.items(), key=lambda item: item[1][1])
    for node_id, (x, y) in ordered:
        _render_iso_node(
            lines,
            node_id=node_id,
            name=names.get(node_id, node_id),
            x=x,
            y=y,
            node_type=node_types.get(node_id, "other"),
            icons=icons,
            options=options,
            port_label=node_port_labels.get(node_id),
            port_prefix=node_port_prefix.get(node_id),
            layout=layout,
            theme=theme,
            group_name=group_of.get(node_id),
        )
