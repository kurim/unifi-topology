"""Tests for cross-group edge rendering under layout_mode="grouped".

A device grouped into one VLAN district can still have a real physical
parent/child in a different district (e.g. a switch's uplink is in
"Unassigned" while the switch itself lands in a named VLAN group). These
edges must stay visible -- as a direct line, visually distinct from a
normal same-group connection -- instead of using the elbow path that
assumes both ends share one coordinate space.
"""

from unifi_topology.model.topology import Edge
from unifi_topology.render._svg_render_flow import compute_svg_layout
from unifi_topology.render.svg_edges import _render_svg_edges
from unifi_topology.render.svg_theme import DEFAULT_THEME, SvgOptions


def _cross_branch_topology() -> tuple[list[Edge], dict[str, str], dict[str, list[str]]]:
    edges = [
        Edge("gw", "Robin"),
        Edge("gw", "sw1"),
        Edge("sw1", "sw2"),
        Edge("sw2", "lan-client", vlans=(1,), active_vlans=(1,)),
        Edge("sw2", "guest-client", vlans=(20,), active_vlans=(20,)),
    ]
    node_types = {
        "gw": "gateway",
        "Robin": "client",
        "sw1": "switch",
        "sw2": "switch",
        "lan-client": "client",
        "guest-client": "client",
    }
    groups = {"LAN": ["lan-client", "sw2"], "Guest": ["guest-client"]}
    return edges, node_types, groups


def _render(edges, node_types, options, groups):
    layout = compute_svg_layout(edges, node_types, options, groups, None, None, None)
    lines: list[str] = []
    _render_svg_edges(
        lines, edges, layout.positions, node_types, options, DEFAULT_THEME, groups=groups
    )
    return "\n".join(lines)


def test_cross_group_edge_uses_direct_line_not_elbow():
    edges, node_types, groups = _cross_branch_topology()
    options = SvgOptions(layout_mode="grouped")
    svg = _render(edges, node_types, options, groups)

    # sw2 (LAN group) <-> sw1 (ungrouped/"Unassigned") is a cross-group edge.
    assert 'data-edge-left="sw1" data-edge-right="sw2"' in svg
    cross_group_line = next(line for line in svg.splitlines() if 'data-edge-right="sw2"' in line)
    # A direct line has exactly one "L" segment; the elbow path has three.
    assert cross_group_line.count(" L ") == 1


def test_cross_group_edge_is_dashed():
    edges, node_types, groups = _cross_branch_topology()
    options = SvgOptions(layout_mode="grouped")
    svg = _render(edges, node_types, options, groups)

    cross_group_lines = [line for line in svg.splitlines() if 'data-edge-right="sw2"' in line]
    assert all("stroke-dasharray" in line for line in cross_group_lines)


def test_same_group_edge_keeps_elbow_and_is_not_dashed():
    edges, node_types, groups = _cross_branch_topology()
    options = SvgOptions(layout_mode="grouped")
    svg = _render(edges, node_types, options, groups)

    same_group_line = next(
        line for line in svg.splitlines() if 'data-edge-right="lan-client"' in line
    )
    # The elbow path always has more than one "L" segment; only the direct
    # cross-group connector is a single segment.
    assert same_group_line.count(" L ") > 1
    assert "stroke-dasharray" not in same_group_line


def test_ungrouped_render_never_marks_edges_cross_group():
    """No groups at all -> today's behaviour, byte for byte."""
    edges, node_types, _groups = _cross_branch_topology()
    options = SvgOptions()
    layout_grouped = compute_svg_layout(edges, node_types, options, None, None, None, None)

    lines_without_groups: list[str] = []
    _render_svg_edges(
        lines_without_groups,
        edges,
        layout_grouped.positions,
        node_types,
        options,
        DEFAULT_THEME,
    )
    lines_with_empty_groups: list[str] = []
    _render_svg_edges(
        lines_with_empty_groups,
        edges,
        layout_grouped.positions,
        node_types,
        options,
        DEFAULT_THEME,
        groups={},
    )
    assert lines_without_groups == lines_with_empty_groups
