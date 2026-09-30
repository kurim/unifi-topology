"""Tests for wrapping many leaf siblings into multiple layout rows."""

import re

from unifi_topology.model.topology import Edge
from unifi_topology.render import svg as svg_module
from unifi_topology.render import svg_isometric as svg_iso_module
from unifi_topology.render._svg_tree_layout import _tree_layout_indices
from unifi_topology.render.svg_theme import SvgOptions


def _switch_with_clients(count: int) -> tuple[list[Edge], dict[str, str]]:
    edges = [Edge("gw", "sw1")]
    node_types = {"gw": "gateway", "sw1": "switch"}
    for i in range(count):
        name = f"c{i}"
        edges.append(Edge("sw1", name))
        node_types[name] = "client"
    return edges, node_types


def test_default_keeps_all_leaves_on_one_row():
    edges, node_types = _switch_with_clients(12)
    positions, levels = _tree_layout_indices(edges, node_types)
    client_levels = {levels[f"c{i}"] for i in range(12)}
    assert client_levels == {2}
    assert len({positions[f"c{i}"] for i in range(12)}) == 12


def test_wraps_leaves_exceeding_threshold_into_rows():
    edges, node_types = _switch_with_clients(12)
    positions, levels = _tree_layout_indices(edges, node_types, max_nodes_per_row=5)
    client_levels = [levels[f"c{i}"] for i in range(12)]
    # 12 leaves at width 5 -> 3 rows (5, 5, 2), spread across 3 levels.
    assert set(client_levels) == {2, 3, 4}
    columns = {positions[f"c{i}"] for i in range(12)}
    assert len(columns) == 5


def test_no_wrap_when_count_at_or_below_threshold():
    edges, node_types = _switch_with_clients(5)
    positions, levels = _tree_layout_indices(edges, node_types, max_nodes_per_row=5)
    assert {levels[f"c{i}"] for i in range(5)} == {2}
    assert len({positions[f"c{i}"] for i in range(5)}) == 5


def test_wrapped_positions_do_not_collide():
    edges, node_types = _switch_with_clients(23)
    positions, levels = _tree_layout_indices(edges, node_types, max_nodes_per_row=7)
    coords = [(positions[name], levels[name]) for name in node_types]
    assert len(coords) == len(set(coords))


def test_disabled_for_falsy_or_negative_threshold():
    edges, node_types = _switch_with_clients(12)
    baseline, _ = _tree_layout_indices(edges, node_types)
    for threshold in (0, -1):
        positions, levels = _tree_layout_indices(edges, node_types, max_nodes_per_row=threshold)
        assert positions == baseline
        assert {levels[f"c{i}"] for i in range(12)} == {2}


def test_mixed_leaf_and_switch_children_only_wraps_leaves():
    edges = [Edge("gw", "sw1"), Edge("sw1", "sw2")]
    node_types = {"gw": "gateway", "sw1": "switch", "sw2": "switch"}
    for i in range(9):
        edges.append(Edge("sw1", f"c{i}"))
        node_types[f"c{i}"] = "client"
    positions, levels = _tree_layout_indices(edges, node_types, max_nodes_per_row=4)
    assert levels["sw2"] == 2
    assert set(levels[f"c{i}"] for i in range(9)) == {2, 3, 4}


def test_render_svg_shrinks_width_and_grows_height_when_wrapped():
    edges, node_types = _switch_with_clients(40)

    wide = svg_module.render_svg(edges, node_types=node_types)
    wrapped = svg_module.render_svg(
        edges,
        node_types=node_types,
        options=SvgOptions(max_nodes_per_row=10),
    )

    def _dims(svg: str) -> tuple[float, float]:
        w = float(re.search(r'width="([\d.]+)"', svg).group(1))
        h = float(re.search(r'height="([\d.]+)"', svg).group(1))
        return w, h

    wide_w, wide_h = _dims(wide)
    wrapped_w, wrapped_h = _dims(wrapped)
    assert wrapped_w < wide_w
    assert wrapped_h > wide_h


def test_render_svg_isometric_also_wraps_by_default_layout():
    edges, node_types = _switch_with_clients(40)

    wide = svg_iso_module.render_svg_isometric(edges, node_types=node_types)
    wrapped = svg_iso_module.render_svg_isometric(
        edges,
        node_types=node_types,
        options=SvgOptions(max_nodes_per_row=10),
    )

    def _dims(svg: str) -> tuple[float, float]:
        w = float(re.search(r'width="([\d.]+)"', svg).group(1))
        h = float(re.search(r'height="([\d.]+)"', svg).group(1))
        return w, h

    wide_w, _wide_h = _dims(wide)
    wrapped_w, _wrapped_h = _dims(wrapped)
    assert wrapped_w < wide_w


def test_render_svg_isometric_compact_layout_ignores_max_nodes_per_row():
    """iso_compact_layout uses its own district packing, not the tree wrap."""
    edges, node_types = _switch_with_clients(40)
    options = SvgOptions(iso_compact_layout=True, max_nodes_per_row=10)
    output = svg_iso_module.render_svg_isometric(edges, node_types=node_types, options=options)
    assert output.startswith("<svg")
