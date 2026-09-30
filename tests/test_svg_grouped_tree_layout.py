"""layout_mode="grouped" keeps the topology a tree and boxes groups inside it."""

import re

import unifi_topology.render.svg as svg_module
from unifi_topology.model.topology import Edge
from unifi_topology.render.svg_theme import SvgOptions

NODE_W = 160  # SvgOptions default node_width


def _site(clients_per_switch: int = 4) -> tuple[list[Edge], dict[str, str], dict[str, list[str]]]:
    edges = [Edge("gw", "sw1"), Edge("gw", "sw2")]
    node_types = {"gw": "gateway", "sw1": "switch", "sw2": "switch"}
    groups: dict[str, list[str]] = {"LAN (sw1)": [], "IoT (sw1)": [], "LAN (sw2)": []}
    for i in range(clients_per_switch):
        name = f"a{i}"
        edges.append(Edge("sw1", name))
        node_types[name] = "client"
        groups["LAN (sw1)" if i % 2 == 0 else "IoT (sw1)"].append(name)
    for i in range(clients_per_switch):
        name = f"b{i}"
        edges.append(Edge("sw2", name))
        node_types[name] = "client"
        groups["LAN (sw2)"].append(name)
    return edges, node_types, groups


def _render(edges, node_types, groups=None, **options):
    mode = "grouped" if groups else "physical"
    return svg_module.render_svg(
        edges,
        node_types=node_types,
        options=SvgOptions(layout_mode=mode, **options),
        groups=groups,
    )


def _node_rects(svg: str) -> dict[str, tuple[float, float]]:
    rects = {}
    for match in re.finditer(r'data-node-id="([^"]+)"[^>]*>(.*?)</g>', svg, re.S):
        rect = re.search(r'<rect[^>]*x="([-\d.]+)"[^>]*y="([-\d.]+)"', match.group(2))
        if rect:
            rects[match.group(1)] = (float(rect.group(1)), float(rect.group(2)))
    return rects


def _boundaries(svg: str) -> dict[str, tuple[float, float, float, float]]:
    found = {}
    for match in re.finditer(
        r'data-group-name="([^"]+)">\s*<rect class="group-boundary" '
        r'x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)"',
        svg,
    ):
        found[match.group(1)] = tuple(float(match.group(i)) for i in range(2, 6))
    return found


def test_infrastructure_keeps_its_physical_tree_level():
    edges, node_types, groups = _site()
    grouped = _node_rects(_render(edges, node_types, groups))
    physical = _node_rects(_render(edges, node_types))
    for node in ("gw", "sw1", "sw2"):
        assert grouped[node][1] == physical[node][1]
    assert grouped["gw"][1] < grouped["sw1"][1] < grouped["a0"][1]


def test_each_parents_group_boxes_sit_directly_below_it():
    edges, node_types, groups = _site()
    svg = _render(edges, node_types, groups)
    rects = _node_rects(svg)
    boxes = _boundaries(svg)
    for parent in ("sw1", "sw2"):
        own = [box for name, box in boxes.items() if f"({parent})" in name]
        left = min(x for x, _y, _w, _h in own)
        right = max(x + w for x, _y, w, _h in own)
        centre = rects[parent][0] + NODE_W / 2
        assert left <= centre <= right
        assert all(y > rects[parent][1] for _x, y, _w, _h in own)


def test_group_members_are_one_contiguous_block_and_boxes_do_not_overlap():
    edges, node_types, groups = _site(clients_per_switch=6)
    svg = _render(edges, node_types, groups)
    boxes = list(_boundaries(svg).values())
    assert len(boxes) == 3
    for i, (x1, y1, w1, h1) in enumerate(boxes):
        for x2, y2, w2, h2 in boxes[i + 1 :]:
            separate = x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1
            assert separate


def test_infrastructure_has_no_box():
    edges, node_types, groups = _site()
    svg = _render(edges, node_types, groups)
    assert set(_boundaries(svg)) == set(groups)
    assert 'data-node-id="gw" data-node-type="gateway" data-group' not in svg


def test_edges_to_grouped_nodes_keep_normal_elbow_routing():
    edges, node_types, groups = _site()
    grouped = _render(edges, node_types, groups)
    path = re.search(r'<path d="([^"]+)"[^>]*data-edge-left="sw1" data-edge-right="a1"', grouped)
    assert path
    assert path.group(1).count(" L ") > 1
    assert "stroke-dasharray" not in path.group(0)


def test_group_blocks_wrap_with_max_nodes_per_row():
    edges, node_types, groups = _site(clients_per_switch=12)
    svg = _render(edges, node_types, groups, max_nodes_per_row=3)
    rects = _node_rects(svg)
    lan_sw2_rows = {rects[n][1] for n in groups["LAN (sw2)"]}
    assert len(lan_sw2_rows) == 4
    assert len({rects[n][0] for n in groups["LAN (sw2)"]}) == 3


def test_nodes_in_no_group_stay_in_the_tree_without_a_box():
    edges, node_types, groups = _site()
    edges.append(Edge("sw1", "loose"))
    node_types["loose"] = "client"
    svg = _render(edges, node_types, groups)
    assert "loose" in _node_rects(svg)
    assert set(_boundaries(svg)) == set(groups)
