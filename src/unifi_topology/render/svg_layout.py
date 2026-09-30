"""Layout algorithms for orthogonal SVG network diagrams."""

from __future__ import annotations

from . import _svg_group_layout, _svg_tree_layout

__all__ = [
    "GroupBounds",
    "_assign_nodes_to_groups",
    "_build_children_maps",
    "_build_node_to_group_map",
    "_compute_group_bounds",
    "_filter_edges_for_group",
    "_layout_grouped_nodes",
    "_layout_nodes",
    "_layout_nodeset",
    "_layout_positions",
    "_resolve_group_order",
    "_resolve_roots",
    "_sort_children",
    "_sort_key_for_nodes",
    "_svg_node_group_attrs",
    "_tree_layout_indices",
]

GroupBounds = _svg_group_layout.GroupBounds
_assign_nodes_to_groups = _svg_group_layout._assign_nodes_to_groups
_build_children_maps = _svg_tree_layout._build_children_maps
_build_node_to_group_map = _svg_group_layout._build_node_to_group_map
_compute_group_bounds = _svg_group_layout._compute_group_bounds
_filter_edges_for_group = _svg_group_layout._filter_edges_for_group
_layout_grouped_nodes = _svg_group_layout._layout_grouped_nodes
_layout_nodes = _svg_tree_layout._layout_nodes
_layout_nodeset = _svg_tree_layout._layout_nodeset
_layout_positions = _svg_tree_layout._layout_positions
_resolve_group_order = _svg_group_layout._resolve_group_order
_resolve_roots = _svg_tree_layout._resolve_roots
_sort_children = _svg_tree_layout._sort_children
_sort_key_for_nodes = _svg_tree_layout._sort_key_for_nodes
_svg_node_group_attrs = _svg_group_layout._svg_node_group_attrs
_tree_layout_indices = _svg_tree_layout._tree_layout_indices
