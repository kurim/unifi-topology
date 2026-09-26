# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Clients whose UniFi device info (`unifi_device_info_from_ucore`) carries a product model but no `name` were labelled by that model, so several Protect cameras on one site all rendered as "G6 Pro Bullet", "G6 Turret" and so on. `client_display_name` now ranks `hostname` above the ucore model fields: the hostname is per device (controller data shows it as the slugified Protect alias) while the model is not. Order is now Network alias, ucore name, hostname, ucore model, MAC. Reported in merlijntishauser/unifi-network-maps-ha#303

## [3.2.0] - 2026-07-28

### Added
- `blueprint` built-in theme: classic white line work on blueprint-blue paper. Monochrome outlines, flat white icon decals, graph-paper grid. Enabled by two new optional theme fields usable from any theme YAML: `node_stroke` (one outline colour for every node, overriding the per-type palette) and `icon_decal_iso` (flat isometric decal colour, bypassing the per-type derivation that darkens each node's gradient and so vanishes on dark fills). Both default to unset, leaving every existing theme byte-identical
- `SvgOptions.iso_show_grid` (default `True`): draws the isometric floor grid. Set `False` for a plain background; nothing else about the render changes, including the canvas size

### Changed
- The compact isometric layout was rebuilt around one grammar per subtree: child hubs sit directly below their hub so the infrastructure trunk runs unbroken, and a hub's clients form a block immediately to its right. The previous composition put the leaf block between hub and children, which pushed connected infrastructure 4-7 cells apart, drew a 12-node chain as a 1x15 tower, and left 62 percent of the bounding box empty. The placement search now also varies leaf-block width (without it the search was a no-op for narrow trees) and scores density alongside aspect. Measured: chain 1x15 to 5x5, two-tier fill 38 to 58 percent, mean hub-to-hub distance 4.3 to 2.0 cells. Only affects `iso_compact_layout=True`
- Isometric icons are drawn slightly smaller relative to their tile (1.26 to 1.08 tile heights). At the previous size they overhung the top face they are meant to be standing on, most visibly for the flat access point disc

### Fixed
- Routed isometric edges no longer read as clients chained to clients. Two causes, measured on a live 50-node render: hub fan-outs superimposed on identical lanes (98 pairs of distinct edges sharing a segment), and 7 edges drawn straight through unrelated tiles — straight runs were exempt from avoidance entirely, and between certain nodes every two-corner route crosses something, so the minimum-cost route still ploughed through. Edges sharing a source now spread onto small parallel lane offsets with entry stubs, and a route that is still blocked shifts wholesale onto the adjacent half-integer lane, which cannot hold a node. After: 0 edges over an unrelated tile at any depth, and the only remaining shared segments are wires legitimately converging on a common endpoint. Applies under `iso_route_around_nodes`; default output is unchanged
- Isometric node side faces ignored the theme. They were shaded from `_TYPE_COLORS`, the palette documented as being for orthogonal rendering, while the top face used the theme gradient — so under the `unifi` theme an access point drew a blue top on green sides. Both now come from `svg_theme.node_type_gradients`, the single source for node colour. Output is unchanged for the default theme, whose values happened to match

## [3.1.2] - 2026-07-27

### Fixed
- Remove dead code left over from the isometric light model: the `_FACE_TOP` constant (flagged by CodeQL as an unused global) and the `iso_top_highlight` function, which was never called from anywhere. The top face is not shaded — it keeps the node's own themed fill, which is what the side faces are derived against — so neither had a caller. Rendered output is unchanged
- Isometric edges could be drawn outside the canvas and render clipped when `iso_route_around_nodes` and `iso_compact_layout` were combined (closes #69). A corner is chosen in grid space and screen x depends on `gx - gy`, so a turn between two nodes sharing that difference projects to one side of both; the viewport was sized from node positions only, so the corner fell outside the `viewBox`. The viewport now expands to contain the chosen corners, and only when one would otherwise fall outside — output is byte-identical for any diagram that already fitted, including every default render. Route selection moved to `render/_svg_iso_routing.py` so layout and drawing agree on which edges turn and where, rather than each deciding for itself

## [3.1.1] - 2026-07-27

### Added
- `SvgOptions.iso_route_around_nodes` (default `False`): routes isometric edges around intervening nodes. Both legs of an edge already ran along grid axes, but the corner was always taken on the same axis regardless of what stood in the way, so on a live 50-node topology 20 of 31 edges passed over a node that was not one of their endpoints. Routing now picks whichever L-shaped route crosses fewer occupied cells, and falls back to a three-segment route that steps into a clear lane when both are blocked. On that topology it drops to 0 of 31; every leg still runs along a grid axis, so each projects to a true isometric line
- `FirewallPolicy` now exposes domain and application matching criteria, so a rule narrowed to specific destinations is no longer indistinguishable from a wide-open one (closes #68). New fields: `destination_web_domains`, `destination_web_matching_type`, `destination_app_ids`, plus `source_matching_target` and `destination_matching_target`. The matching-target pair is the general signal — a value other than `"ANY"` means the rule is narrowed even when the criteria are not parsed into a list, so criteria this model does not yet decode (regions, app categories) still cannot read as unrestricted. All fields default to empty, so existing consumers are unaffected. Verified against a live 156-policy ruleset: the three domain- and application-restricted rules previously appeared to allow all protocols and ports
- New `unifi` icon set (`SvgTheme(icon_set="unifi")`), bundled under `assets/icons/icons-unifi/`. Original MIT-licensed artwork covering all 14 node types with no fallbacks, replacing several semantically wrong isopacks mappings: access points are ceiling discs rather than radio towers, NAS is a drive enclosure rather than a database cylinder, and `client_cluster` is a group of devices rather than a person. The existing `isometric` (isopacks) and `modern` sets are unchanged and remain the default
- `SvgOptions.iso_compact_layout` (default `False`): packs each hub and its clients into a district, and each district directly beneath its parent, so a whole subtree occupies one contiguous region. Placement follows connectivity rather than edge direction — LLDP reports a link from whichever end saw it, and following `left -> right` alone left four of ten infrastructure devices outside the gateway's tree on a live network, packed as separate blocks with their links stretched across the diagram. Measured on that network: edge crossings 23 to 0, mean infrastructure edge length 1726px to 790px. The previous layout mapped sibling order to one grid axis and tree depth to the other, so a shallow, wide network became a thin diagonal strip — 89 nodes produced a 166x4 grid on a 21504x12296 canvas. Compact packing brings that to 5904x4675, raises node density from 0.4 to 5.1 nodes per megapixel, and cuts mean edge length by roughly half
- `scripts/normalize_icon_viewbox.py`: retargets an icon set's root `viewBox` so every icon fills the same fraction of its square frame. Icons are drawn into a fixed square with `xMidYMid meet`, so uneven internal margins made some devices render as specks

### Fixed
- The `isometric` (isopacks) set no longer ships primitive placeholder icons. isopacks covers no camera, speaker, games console or sensor -- none of the 1062 SVGs in any of its collections does -- so those four node types were filled with generated stand-ins of 7-10 flat polygons, visibly a different library sitting beside the hand-drawn art. They are now the UniFi set's artwork for those subjects, restyled into the isopacks blue palette by the new `scripts/recolour_icons.py` (23-62 shapes each, geometry unchanged). `assets/icons/isometric/NOTICE` records that these four files are not isopacks work, and `scripts/generate_iso_icons.py` is removed
- Isometric access point icons floated a full tile height above their node when using an icon set other than isopacks. The lift was tuned for the isopacks radio mast, whose artwork sits high in its own frame; applied to the normalized UniFi ceiling disc it left the icon hovering. The extra lift is now per icon set, so isopacks and modern output is unchanged
- `FirewallPolicy.source_mac_addresses` was always empty against zone-based controllers. The nested parser read `mac_addresses`, but the controller sends `client_macs`; both keys are now accepted. On a live ruleset this left 8 MAC-restricted policies looking unrestricted
- Isometric layout could place two nodes on the same grid cell, silently stacking them. A parent's position was the mean of its children's indices, so two switches feeding one client resolved to the same tile (three nodes shared a tile in a 30-node topology). Only affects the new compact layout path; the default tree layout is unchanged pending a wider fix

## [3.0.2] - 2026-07-24

### Fixed
- `lookup_model_name` (and the `_stats` model-name fallback) again resolve model strings that only survive as an entry's `name` after the store-to-firmware-code re-keying of the bundled model database (e.g. `USW-Enterprise-24-PoE`, now the name of firmware code `US624P`). The lookup index now falls back to a case-insensitive `name` match, honouring the documented "accepts both store SKUs and firmware platform codes" contract
- `render_device_port_overview` Connected column was always empty: MAC-keyed port/client maps (from `build_port_map`/`build_client_port_map`) were filtered by device display name, which never matched since the node-id migration. The maps are now translated to display names, so connected devices show correctly. Pass the new optional `node_names` (MAC-to-display-name map, as `render_svg`/`render_mermaid` accept) to also resolve connected client names (closes #67)

## [3.0.1] - 2026-07-19

Full-codebase review remediation. See `docs/code-review-2026-07.md` for the
underlying findings. This is a major release: it contains three breaking
contract changes (marked **BREAKING** below).

### Security
- Sanitize `node_type` before interpolating it into SVG paint references. A crafted node type (e.g. via `node_types`) could previously inject arbitrary SVG attributes and execute script when the diagram was embedded inline. Unknown types now fall back to the `other` gradient instead of rendering an invisible node body
- Validate `node_data` attribute *names* against `^[A-Za-z_][\w-]*$` (values were already escaped); invalid keys are dropped instead of injecting attributes
- Strip XML-invalid control characters from group names in SVG output (previously used `html.escape`, which left them intact and produced an unparseable document)
- Keep `password` and `api_key` out of `Config`'s repr/str/tracebacks (`field(repr=False)`), so they no longer leak into logs or pytest output
- Restrict the theme `font_family` slug to `[a-z0-9-]` to prevent path traversal into the embedded-font loader
- Write cache files owner-only (`0600`); they contain MACs, IPs, and hostnames and were previously created world-readable

### Changed
- **BREAKING:** `fetch_*` now raise the `UnifiError` hierarchy (e.g. `UnifiApiError`) for network failures instead of leaking raw `requests` exceptions. `UnifiError` gains a `status_code` attribute. Consumers catching `requests.ConnectionError`/`requests.RequestException` must catch `UnifiError` instead
- **BREAKING:** Edge change events from `compare_topologies` now use `entity_type="edge"` (previously `"device"`). Code filtering diff events via `TopologyDiff.filter(entity_types={"device"})` will no longer match edges; use `{"edge"}`
- `Topology.from_dict` now raises `ValueError` on a snapshot whose `version` is newer than supported, instead of silently mis-deserializing it (existing snapshots are `version` 1 and unaffected)
- **BREAKING:** `collapse_client_edges` is now pure: it no longer mutates the `node_types`/`node_names` arguments and returns a `CollapsedClientEdges` named tuple `(edges, client_counts, node_types, node_names)` instead of `(edges, client_counts)`
- HTTP requests now default to a 30s timeout (`UNIFI_REQUEST_TIMEOUT_SECONDS` still overrides); previously an unset timeout meant a hung controller blocked fetches indefinitely
- Retries are now limited to transient errors — authentication failures and 4xx responses surface immediately instead of being retried up to 20 times (which risked controller rate-limiting/lockout)
- `normalize_devices` now skips and logs a malformed device rather than raising for the whole site; a single bad LLDP `local_port_idx` or a device missing name/MAC no longer aborts normalization
- `normalize_mac` canonicalizes separators (e.g. `AA-BB-..` and `aabbcc..` become `aa:bb:..`), so dash/no-separator MACs now match the device index consistently. This can change node IDs for third-party LLDP peers
- Client diffs no longer emit `node_changed` events for `signal`/`satisfaction` fluctuations (they change every poll); channel and the stable properties are still compared
- Mermaid label escaping now uses Mermaid-native forms (`#quot;` for quotes, `<br/>` for newlines) instead of unsupported backslash escapes; a single quote in a device name no longer breaks the whole diagram
- Reverse DNS resolution now runs concurrently over a bounded thread pool, and an invalid (non-IP) `dns_server` is logged at warning level instead of being silently swallowed

### Fixed
- **LLDP/Markdown port tables lost all connected-device and client data** after the v2 MAC-id migration: the maps became MAC-keyed but were looked up by device name. Port tables again show connected devices and client names
- WAN1 could resolve to the WAN2 port because assignment matching was substring-based (`"wan" in "wan2"`); matching is now exact, so both interfaces map to distinct ports
- `Device.in_gateway_mode` is now serialized and restored; a UX device in AP mode was previously reclassified as a gateway after a snapshot round-trip
- Third-party LLDP peers seen with different MAC casing/format no longer render as duplicate nodes
- `is_wired` is coerced with `as_bool`, so a stringly-typed `"false"` no longer misclassifies a wireless client as wired
- `native_vlan: true` (and similar boolean payloads) no longer coerce to VLAN 1 in integer fields
- `invalidate_cache` can now actually invalidate `devices` entries (it omitted the detail cache-key extra and silently removed nothing)
- Cache-directory resolution failures (e.g. a symlinked `.cache`) degrade to no-cache instead of raising `ValueError` from every fetch, including with `use_cache=False`
- `swap_firewall_policy_order` rolls back the first PUT if the second fails, instead of leaving both policies with a duplicate index
- API responses whose `data` field is not a list are rejected at the boundary with `UnifiApiError` instead of failing deep in model code
- Client `fw_version` is preserved through a snapshot round-trip (firmware no longer goes missing from restored inventories)
- Snapshot loaders tolerate JSON `null` for list fields (`vlans`, `active_vlans`, `tagged_vlans`) instead of raising `TypeError`
- Falsy VLAN 0 / port 0 are no longer coalesced away to a later key when comparing clients
- Devices with an empty MAC no longer collide on the diff key and get compared against each other
- Mermaid `linkStyle` indices are offset past the WAN link, so PoE/wireless styling targets the correct edges when a WAN node is present
- Mermaid rendering no longer raises `KeyError` when the gateway is typed but appears in no edge or group
- The device details table is no longer duplicated in each LLDP ports section
- `render_device_inventory_table` and multi-client entries now escape Markdown special characters (a `|` no longer misaligns the table)
- Orthogonal VPN overlay box is placed in reserved space at the canvas bottom instead of overlapping the level-1 nodes below the gateway
- Isometric floor grid is aligned with the node tiles (both now share the same offset)
- Group labels preserve mixed case (e.g. "IoT" renders as "IoT", not "Iot")
- A narrow negative UniFi flag (e.g. `is_uap: False` on a wired Protect camera) no longer overrides positive ucore device info when classifying a client as UniFi
- Authenticated sessions are retained across firewall writes instead of being discarded (which forced a fresh login on the next fetch)
- Constructing a `verify_ssl=False` client no longer disables `InsecureRequestWarning` process-wide; suppression is scoped per request
- Importing `unifi_topology.model.mock` without the optional `faker` package now raises a clear `ImportError` explaining the install
- Legacy controllers are no longer probed with a doomed UDM Pro login on every fetch (the auth style is remembered per URL), reducing 429 rate-limiting risk
- CI: the PyPI publish workflow now runs the test suite before building; the exact-pinned build backend was relaxed to avoid sdist install breakage; `click`, `msgpack`, and `pip` bumped to patched versions

### Internal
- Split `diff.py` (548 lines) into `_diff_events`, `_diff_engine`, and `_diff_specs` with `compare_topologies` as a thin facade
- Removed two callable-injection layers (`_fetch.fetch_cached`, `_svg_render_flow`) and de-duplicated overlay box-metrics, VLAN striped-edge rendering, WAN-speed formatting, and the gateway-position helper across the SVG renderers
- Model classification/coercion/edge facades no longer re-export private helpers; tests import from the real private modules
- Introduced a `ClientRecord` type alias and removed the `# type: ignore` cluster in `topology.py`
- Corrected stale facts in `AGENTS.md` (version, complexity limit, Jinja2 dependency, module layout)

## [2.2.2] - 2026-06-01

### Fixed
- Strip XML-invalid control characters (e.g. U+0003) from device/client names before SVG serialization. A single illegal character from a misencoded name previously produced an unparseable SVG, breaking the entire render for downstream consumers. Both text-content and attribute (`data-node-id`, `data-edge-left/right`, `data-group`) contexts are now sanitized (closes #51)

## [2.2.1] - 2026-05-25
### Added
- Chores: updated dependencies

## [2.2.0] - 2026-05-17

### Added
- UniFi OS API-key authentication: set `Config(api_key=...)` (or `UNIFI_API_KEY` env var) to authenticate via the `X-API-KEY` header instead of username/password. Avoids cookie-based login retries that can trip `AUTHENTICATION_FAILED_LIMIT_REACHED` on the controller. `user`/`password` remain supported; configs must supply exactly one of the two auth modes (closes #47)

## [2.1.2] - 2026-03-27

### Fixed
- Filter bogus `public_ip` values: reject loopback, private, link-local, and unspecified addresses from `connect_request_ip` so the renderer falls back to `ip_address` (closes #37)

## [2.1.1] - 2026-03-26

### Fixed
- Downgraded "missing LLDP info; using uplink fallback" log from WARNING to DEBUG to reduce noise for offline/seasonal devices (closes #34)

## [2.1.0] - 2026-03-25

### Added
- `Device.public_ip` and `WanInterface.public_ip` fields exposing the `connect_request_ip` from the UniFi API, showing the actual public IP under CGNAT instead of the carrier-assigned address (closes #33)
- Playwright-based specs scraper for products where the store JSON API no longer provides technical specifications (closes #32)
- `specs_overrides.json` with dimensions, weight, power, and form factor for 29 product pages covering 42 model entries (UCG-Fiber, UCG-Max, USW-Ultra series, ECS switches, phones, LTE, PDUs, and more)
- `make update-models` target that runs both the JSON API scraper and the Playwright scraper

### Fixed
- `lookup_model_specs()` now returns specs for 237/326 models (up from 195), including all current-gen Cloud Gateways and Switch Ultra devices (closes #32)
- Cyclic import between `topology` and `clients` modules (CodeQL #194)
- CodeQL alerts #197, #198, #199 (unused global variable, empty except clauses)

## [2.0.0] (2026-03-23)

### Changed
- **BREAKING:** Node identification switched from device names to normalized MAC addresses throughout the pipeline (fixes #31)
  - `Edge.left` / `Edge.right` now contain normalized MAC addresses instead of device names
  - `build_node_type_map()` returns a MAC-keyed dict instead of name-keyed
  - `build_topology()` `gateways` parameter now expects MAC addresses
  - `group_devices_by_type()` returns MAC lists instead of name lists
  - `collapse_client_edges()` cluster IDs changed from `"{name} ({n} clients)"` to `"{mac}__cluster"`; accepts optional `node_names` parameter
  - `build_client_edges()` accepts optional `node_names` parameter for label generation
  - `build_client_port_map()` returns MAC-keyed dict
  - SVG `data-node-id` attributes now contain MAC addresses
  - `render_svg()`, `render_svg_isometric()`, `render_mermaid()`, `render_dual()` accept optional `node_names` parameter for display labels
- Internal edge discovery uses MAC-based lookups: `_uplink_name` renamed to `_uplink_id`, `_lldp_peer_name` renamed to `_lldp_peer_id`, `EdgeInputs.device_by_name` renamed to `EdgeInputs.device_by_id`

### Added
- `build_node_names(devices, clients)` function to build a combined MAC-to-display-name mapping for all nodes
- `TopologyResult.node_names` field providing device MAC-to-name lookup from topology building

### Fixed
- Devices with duplicate display names no longer collapse into a single node (fixes #31)

## [1.3.2] (2026-03-20)

### Added
- `list_all_models()` public function to return the complete model lookup table with all model codes and their specs, docs, and URLs

## [1.3.1] (2026-03-19)

### Added
- Physical device specs scraped from Ubiquiti store: dimensions, weight, max power, form factor, rack height (`lookup_model_specs`) (closes #26)

## [1.3.0] (2026-03-17)

### Added
- Generic Mermaid diagram rendering (`render_mermaid`, `MermaidTheme`)
- Markdown device port overview tables (`render_device_port_overview`)
- LLDP Markdown table rendering (`render_lldp_md`)
- Jinja2 template engine for render output
- Enables downstream consumers (unifi-homelab-ops) to use renderers directly

### Fixed
- Model lookup for 3 devices returning empty names by adding scraper aliases for controller model codes (`UDMA6A8`/`UCGF`, `UAPA693`/`G7LT`, `USWED37`/`USM25G8P`) (fixes #23)

## [1.2.4] (2026-03-16)

### Added
- Model lookup now resolves firmware platform codes (e.g. `U6M`, `UDMPRO`) in addition to store SKUs (fixes #23)
- `lookup_model_docs()` and `lookup_firmware_changelog()` for documentation and release notes links
- Scraper extended to cross-reference the official Ubiquiti firmware API with the store, including datasheet and firmware changelog URLs

## [1.2.3] (2026-03-16)

### Fixed
- Incomplete URL substring sanitization in test suite (CodeQL #193)
- `models.json` not included in PyPI wheel, causing model name lookup to silently return empty (fixes #22)

## [1.2.2] (2026-03-15)

### Added
- Model name lookup table scraped from the official Ubiquiti store (`lookup_model_name`, `lookup_model_url`)
- `normalize_device_stats` now resolves `model_name` from the lookup table when the API omits it (fixes #21)
- `make scrape-models` target and `scripts/scrape_models.py` scraper for refreshing the bundled model data

## [1.2.1] (2026-03-15)

### Added
- `model_name` field on `DeviceStats` for friendly device names (fixes #19)
- Release notes and API notes documenting `1.2.1` compatibility expectations and release verification

### Changed
- Tightened source complexity enforcement to `A/A/A` and completed the internal adapter, model, and render refactor behind stable public exports
- Reorganized the test suite into focused modules and reduced every `tests/test_*.py` file to `100` lines or fewer for lower navigation cost
- Expanded API contract coverage so README-style usage and top-level exports/signatures are validated in CI

### Fixed
- Cache serializer now preserves `state`, `uptime`, `num_sta`, `system-stats`, temperature, traffic counters, and PoE budget fields (fixes #20)
- Corrected README and documentation examples to match the current stable library contract and rendering workflow

## [1.2.0] (2026-03-15)

### Added
- `fetch_device_stats()` for device CPU, memory, temperature, and PoE metrics
- `DeviceStats` and `PoePortStats` data models with `normalize_device_stats()` coercion

### Changed
- Test coverage boosted to 98% across all modules (899 tests)
- Consolidated fetch functions to use shared `_fetch_cached` helper, improving maintainability index to A

## [1.1.1] (2026-03-14)

### Added
- Cache invalidation: `invalidate_cache` for clearing cached API responses after write operations
- `UnifiClient` instance caching per config to avoid repeated logins and prevent 429 rate-limit errors
- `clear_client_cache()` for explicit client cache control
- `UnifiError` base exception class so consumers can catch all unifi-topology errors with a single `except UnifiError`
- Export `UnifiApiError` and `UnifiAuthError` from the public API


## [1.1.0] (2026-03-12)

### Added
- Firewall policy write operations: `toggle_firewall_policy` and `swap_firewall_policy_order`
- `pip-audit` dependency vulnerability scanning in CI and Makefile

### Changed
- CI quality checks (lint, typecheck, complexity, audit) now run in parallel instead of sequentially

## [1.0.8] (2026-03-12)

### Added
- Extended `FirewallPolicy` with source-side filtering fields: `source_ip_ranges`, `source_mac_addresses`, `source_port_ranges`, `source_network_id`
- Added destination-side fields: `destination_mac_addresses`, `destination_network_id`
- Added firewall group references: `source_port_group_id`, `destination_port_group_id`, `source_address_group_id`, `destination_address_group_id`
- Added connection/metadata fields: `connection_state_type`, `connection_logging`, `schedule`, `match_ip_sec`
- Normalization extracts all new fields from both flat and nested (v2 API) formats

## [1.0.5] (2026-03-09)

### Added
- Firewall support: `FirewallZone`, `FirewallPolicy`, `FirewallGroup` data models with normalization and flexible field name resolution
- `fetch_firewall_zones`, `fetch_firewall_policies`, `fetch_firewall_groups` with cache/retry/stale-cache fallback
- V2/Integration API support in `UnifiClient` (`_get_v2` method) for zone and policy endpoints

### Changed
- Relaxed runtime dependency pins from exact versions to compatible ranges to reduce conflicts with downstream consumers

## [1.0.4] (2026-02-28)

### Fixed
- `network_table` field lost during device cache serialization, breaking VPN tunnel extraction from cached data

## [1.0.3] (2026-02-28)

### Added
- VPN tunnel support: extraction from gateway device data and SVG rendering
- MkDocs documentation site with API reference, deployed to GitHub Pages
- `make docs` / `make docs-serve` / `make version-bump` targets
- `CONTRIBUTING.md`, issue templates, PR template
- `py.typed` marker for PEP 561 type checking support
- README badges (CI, PyPI, Python version, license)

### Changed
- Expanded `SECURITY.md` with supported versions, response timeline, and scope

## [1.0.1] (2026-02-25)

First stable release, extracted from `unifi-network-maps` v1.6.x.

### Added
- `adapters` -- UniFi API client, environment config, DNS hostname resolution
- `model` -- Topology model, device normalization, edge building, client handling, VLAN info, diff/snapshot, mock data generation
- `render` -- SVG orthogonal and isometric rendering, theming, icons, inventory tables
- `paths` -- Path validation helpers for secure file access
- Assets: SVG device icons (isometric, modern, modern-flat), theme YAML files, embedded fonts
- Full public API exported from top-level package: `build_client_edges`, `build_device_index`, `build_node_type_map`, `group_devices_by_type`, `DEFAULT_SVG_THEME`
- PyPI trusted publishing via GitHub Actions
- Dependabot and CodeQL workflows

[Unreleased]: https://github.com/merlijntishauser/unifi-topology/compare/v3.2.0...HEAD
[3.2.0]: https://github.com/merlijntishauser/unifi-topology/compare/v3.1.2...v3.2.0
[3.1.2]: https://github.com/merlijntishauser/unifi-topology/compare/v3.1.1...v3.1.2
[3.1.1]: https://github.com/merlijntishauser/unifi-topology/compare/v3.0.2...v3.1.1
[3.0.2]: https://github.com/merlijntishauser/unifi-topology/compare/v3.0.1...v3.0.2
[3.0.1]: https://github.com/merlijntishauser/unifi-topology/compare/v2.2.1...v3.0.1
[2.2.2]: https://github.com/merlijntishauser/unifi-topology/compare/v2.2.1...v2.2.2
[2.2.1]: https://github.com/merlijntishauser/unifi-topology/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/merlijntishauser/unifi-topology/compare/v2.1.2...v2.2.0
[2.1.2]: https://github.com/merlijntishauser/unifi-topology/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/merlijntishauser/unifi-topology/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/merlijntishauser/unifi-topology/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/merlijntishauser/unifi-topology/compare/v1.3.2...v2.0.0
[1.3.2]: https://github.com/merlijntishauser/unifi-topology/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/merlijntishauser/unifi-topology/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/merlijntishauser/unifi-topology/compare/v1.2.4...v1.3.0
[1.2.4]: https://github.com/merlijntishauser/unifi-topology/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/merlijntishauser/unifi-topology/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/merlijntishauser/unifi-topology/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/merlijntishauser/unifi-topology/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/merlijntishauser/unifi-topology/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/merlijntishauser/unifi-topology/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/merlijntishauser/unifi-topology/compare/v1.0.8...v1.1.0
[1.0.8]: https://github.com/merlijntishauser/unifi-topology/compare/v1.0.5...v1.0.8
[1.0.5]: https://github.com/merlijntishauser/unifi-topology/compare/v1.0.4...v1.0.5
[1.0.4]: https://github.com/merlijntishauser/unifi-topology/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/merlijntishauser/unifi-topology/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/merlijntishauser/unifi-topology/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/merlijntishauser/unifi-topology/releases/tag/v1.0.1
