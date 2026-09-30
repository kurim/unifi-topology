"""Tests for core isometric SVG rendering behavior."""

import unifi_topology.render.svg_isometric as svg_iso_module
import unifi_topology.render.svg_layout as svg_layout_module
from unifi_topology.model.topology import Edge


def test_tree_layout_indices_cycle_returns_nodes():
    positions, _levels = svg_layout_module._tree_layout_indices(
        [Edge("A", "B"), Edge("B", "A")],
        {"A": "switch", "B": "switch"},
    )
    assert set(positions.keys()) == {"A", "B"}


def test_tree_layout_indices_empty_returns_empty():
    positions, _levels = svg_layout_module._tree_layout_indices([], {})
    assert positions == {}


def test_render_svg_isometric_handles_no_edges():
    output = svg_iso_module.render_svg_isometric([], node_types={})
    assert output.startswith("<svg")


def test_render_svg_isometric_without_icons(monkeypatch):
    monkeypatch.setattr(
        svg_iso_module,
        "_load_isometric_icons",
        lambda icon_set="isometric", decal_color="#5A6878", decal_colors=None: {},
    )
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    assert "<image" not in output


def test_render_svg_isometric_skips_missing_positions(monkeypatch):
    from unifi_topology.render import _svg_iso_layout

    monkeypatch.setattr(_svg_iso_layout, "_tree_layout_indices", lambda *_a, **_k: ({}, {}))
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    assert 'stroke="url(#iso-link' not in output


def test_render_svg_isometric_elbow_path():
    output = svg_iso_module.render_svg_isometric(
        [Edge("Root", "B"), Edge("Root", "C")],
        node_types={"Root": "gateway", "B": "switch", "C": "switch"},
    )
    assert output.count(" L ") >= 2


def test_render_svg_isometric_poe_icon():
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B", poe=True)],
        node_types={"A": "switch", "B": "switch"},
    )
    assert "iso-poe-bolt" in output


def test_render_svg_isometric_defs_use_iso_node_prefix():
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    assert 'id="iso-node-switch"' in output


def test_render_svg_isometric_nodes_reference_iso_node_prefix():
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    assert 'fill="url(#iso-node-switch)"' in output


def test_render_svg_isometric_adds_edge_data_attributes():
    output = svg_iso_module.render_svg_isometric(
        [Edge("Gateway", "Switch")],
        node_types={"Gateway": "gateway", "Switch": "switch"},
    )
    assert 'data-edge-left="Gateway"' in output
    assert 'data-edge-right="Switch"' in output
