"""Tests for VLAN-grouped isometric layout (layout_mode="grouped")."""

from unifi_topology.model import group_nodes_by_vlan
from unifi_topology.model.topology import Edge
from unifi_topology.render import svg_isometric as svg_iso_module
from unifi_topology.render._svg_iso_layout import _iso_grid_positions, _iso_layout
from unifi_topology.render.svg_theme import SvgOptions


def _two_vlan_topology() -> tuple[list[Edge], dict[str, str]]:
    edges = [Edge("gw", "sw1")]
    node_types = {"gw": "gateway", "sw1": "switch", "sw2": "switch"}
    for i in range(8):
        name = f"lan{i}"
        edges.append(Edge("sw1", name, vlans=(1,), active_vlans=(1,)))
        node_types[name] = "client"
    edges.append(Edge("gw", "sw2"))
    for i in range(6):
        name = f"guest{i}"
        edges.append(Edge("sw2", name, vlans=(20,), active_vlans=(20,)))
        node_types[name] = "client"
    return edges, node_types


def test_grouped_positions_keep_each_group_in_its_own_column_range():
    edges, node_types = _two_vlan_topology()
    groups, group_order, _group_vlan_ids = group_nodes_by_vlan(edges, {1: "LAN", 20: "Guest"})

    options = SvgOptions(layout_mode="grouped")
    layout = _iso_layout(options)
    grid = _iso_grid_positions(layout, edges, node_types, options, groups, group_order)

    lan_xs = [grid[n][0] for n in groups["LAN"] if n in grid]
    guest_xs = [grid[n][0] for n in groups["Guest"] if n in grid]

    assert max(lan_xs) < min(guest_xs)


def test_grouped_positions_do_not_collide():
    edges, node_types = _two_vlan_topology()
    groups, group_order, _group_vlan_ids = group_nodes_by_vlan(edges, {1: "LAN", 20: "Guest"})

    options = SvgOptions(layout_mode="grouped")
    layout = _iso_layout(options)
    grid = _iso_grid_positions(layout, edges, node_types, options, groups, group_order)

    coords = list(grid.values())
    assert len(coords) == len(set(coords))


def test_ungrouped_layout_is_unaffected_by_layout_mode_default():
    """options.layout_mode defaults to "physical"; passing groups without
    switching it to "grouped" must not change anything (existing callers
    that don't pass groups keep today's output).
    """
    edges, node_types = _two_vlan_topology()
    options = SvgOptions()
    layout = _iso_layout(options)
    groups, group_order, _ = group_nodes_by_vlan(edges, {1: "LAN", 20: "Guest"})

    grouped_call = _iso_grid_positions(layout, edges, node_types, options, groups, group_order)
    no_groups_call = _iso_grid_positions(layout, edges, node_types, options)

    assert grouped_call == no_groups_call


def test_render_svg_isometric_draws_group_boundaries():
    edges, node_types = _two_vlan_topology()
    groups, group_order, group_vlan_ids = group_nodes_by_vlan(edges, {1: "LAN", 20: "Guest"})
    options = SvgOptions(layout_mode="grouped")

    svg = svg_iso_module.render_svg_isometric(
        edges,
        node_types=node_types,
        options=options,
        groups=groups,
        group_order=group_order,
        group_vlan_ids=group_vlan_ids,
    )

    assert svg.count('class="group-boundary"') == len(groups)


def test_render_svg_isometric_without_groups_draws_no_boundaries():
    edges, node_types = _two_vlan_topology()
    svg = svg_iso_module.render_svg_isometric(edges, node_types=node_types)
    assert 'class="group-boundary"' not in svg


def test_iso_compact_layout_with_grouping_does_not_crash():
    """iso_compact_layout's own district packing ignores groups for
    positioning (unlike the default tree layout); this only guards against
    a crash if both are combined, not that boundaries are meaningful.
    """
    edges, node_types = _two_vlan_topology()
    groups, group_order, group_vlan_ids = group_nodes_by_vlan(edges, {1: "LAN", 20: "Guest"})
    options = SvgOptions(layout_mode="grouped", iso_compact_layout=True)

    svg = svg_iso_module.render_svg_isometric(
        edges,
        node_types=node_types,
        options=options,
        groups=groups,
        group_order=group_order,
        group_vlan_ids=group_vlan_ids,
    )

    assert svg.startswith("<svg")
