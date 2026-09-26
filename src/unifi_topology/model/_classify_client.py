"""Private client classification helpers."""

from __future__ import annotations

from .helpers import first_string_field, get_field

# Client device category detection patterns
_CLIENT_NAME_PATTERNS: dict[str, tuple[str, ...]] = {
    "camera": ("camera", "cam", "doorbell", "uvc", "protect", "ring", "nest cam", "arlo"),
    "tv": ("tv", "television", "apple tv", "chromecast", "roku", "fire tv", "shield", "smart tv"),
    "phone": ("phone", "iphone", "android", "pixel", "galaxy", "mobile", "voip", "handset"),
    "printer": ("printer", "print", "laserjet", "inkjet", "epson", "canon", "brother", "hp "),
    "nas": ("nas", "synology", "qnap", "diskstation", "drobo", "freenas", "truenas"),
    "speaker": ("sonos", "homepod", "echo", "alexa", "google home", "speaker", "soundbar"),
    "game_console": ("playstation", "ps4", "ps5", "xbox", "nintendo", "switch", "steam deck"),
    "iot": ("sensor", "thermostat", "nest", "hue", "smart", "zigbee", "z-wave", "iot"),
}

# OUI/vendor patterns for manufacturer-based detection
_CLIENT_VENDOR_PATTERNS: dict[str, tuple[str, ...]] = {
    "camera": ("ubiquiti", "hikvision", "dahua", "axis", "ring", "arlo", "nest", "wyze"),
    "tv": ("samsung tv", "lg tv", "sony tv", "vizio", "tcl", "roku", "apple tv"),
    "phone": ("apple", "samsung mobile", "google pixel", "oneplus", "xiaomi"),
    "printer": ("hp inc", "canon", "epson", "brother", "lexmark", "xerox", "ricoh"),
    "nas": ("synology", "qnap", "western digital", "seagate", "netgear readynas"),
    "speaker": ("sonos", "bose", "harman", "bang & olufsen", "denon"),
    "game_console": ("sony interactive", "microsoft xbox", "nintendo"),
}

# UniFi product line mappings
_UNIFI_PRODUCT_CATEGORIES: dict[str, str] = {
    "protect": "camera",
    "talk": "phone",
    "access": "iot",
    "led": "iot",
    "connect": "iot",
}
_UNIFI_MODEL_CAMERA_TOKENS = ("camera", "doorbell", "uvc", "g4", "g5")


def _match_category(value: str, patterns_by_category: dict[str, tuple[str, ...]]) -> str | None:
    normalized = value.lower()
    for category, patterns in patterns_by_category.items():
        if any(pattern in normalized for pattern in patterns):
            return category
    return None


def _classify_by_name(name: str) -> str | None:
    """Classify client by display name heuristics."""
    return _match_category(name, _CLIENT_NAME_PATTERNS)


def _classify_by_vendor(vendor: str) -> str | None:
    """Classify client by OUI/vendor name."""
    return _match_category(vendor, _CLIENT_VENDOR_PATTERNS)


def _classify_unifi_product_line(ucore: dict[str, object]) -> str | None:
    product_line = ucore.get("product_line")
    if not isinstance(product_line, str):
        return None
    line_lower = product_line.lower()
    for line_prefix, category in _UNIFI_PRODUCT_CATEGORIES.items():
        if line_lower.startswith(line_prefix):
            return category
    return None


def _classify_unifi_model_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value_lower = value.lower()
    if any(token in value_lower for token in _UNIFI_MODEL_CAMERA_TOKENS):
        return "camera"
    if _is_phone_model(value_lower):
        return "phone"
    return None


def _is_phone_model(value_lower: str) -> bool:
    return "talk" in value_lower or "phone" in value_lower


def _classify_unifi_model(ucore: dict[str, object]) -> str | None:
    for key in ("product_shortname", "computed_model", "product_model"):
        category = _classify_unifi_model_value(ucore.get(key))
        if category:
            return category
    return None


def _classify_by_unifi_info(ucore: dict[str, object]) -> str | None:
    """Classify client by UniFi device info (product_line, model)."""
    return _classify_unifi_product_line(ucore) or _classify_unifi_model(ucore)


def _client_ucore_info(client: object) -> dict[str, object] | None:
    """Get UniFi device info from client."""
    info = get_field(client, "unifi_device_info_from_ucore")
    if isinstance(info, dict):
        return info
    return None


def _client_ucore_display_name(client: object) -> str | None:
    """Get display name from UniFi device info."""
    return _client_ucore_name(client) or _client_ucore_model(client)


def _client_ucore_name(client: object) -> str | None:
    """Get the user-assigned name (e.g. Protect alias) from UniFi device info."""
    ucore = _client_ucore_info(client)
    if not ucore:
        return None
    return first_string_field(ucore, "name")


def _client_ucore_model(client: object) -> str | None:
    """Get the product model string from UniFi device info."""
    ucore = _client_ucore_info(client)
    if not ucore:
        return None
    return first_string_field(ucore, "computed_model", "product_model", "product_shortname")


def _client_vendor(client: object) -> str | None:
    """Get vendor/OUI from client."""
    return first_string_field(
        client, "oui", "vendor", "vendor_name", "manufacturer", "manufacturer_name"
    )


def _client_unifi_flag(client: object) -> bool | None:
    """Check explicit UniFi device flags.

    Any positive flag is decisive. A negative is only decisive for the
    authoritative ``is_unifi``/``is_unifi_device`` flags; a narrow negative such
    as ``is_uap: False`` (e.g. a wired UniFi Protect camera) must not override
    positive ucore device info, so it yields ``None`` to fall through.
    """
    authoritative = ("is_unifi", "is_unifi_device")
    for key in (*authoritative, "is_ubnt", "is_uap", "is_managed"):
        as_flag = _as_optional_bool(get_field(client, key))
        if as_flag is True:
            return True
        if as_flag is False and key in authoritative:
            return False
    return None


def _as_optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return None


def _ucore_has_device_info(ucore: dict[str, object]) -> bool:
    """Check whether a ucore dict contains any meaningful UniFi device data."""
    managed = ucore.get("managed")
    if isinstance(managed, bool) and managed:
        return True
    return any(
        isinstance(ucore.get(key), str) and str(ucore.get(key)).strip()
        for key in ("product_line", "product_shortname", "name", "computed_model", "product_model")
    )


def _client_has_ucore_device_info(client: object) -> bool:
    ucore = _client_ucore_info(client)
    return bool(ucore and _ucore_has_device_info(ucore))


def _vendor_is_unifi(vendor: str | None) -> bool:
    if not vendor:
        return False
    normalized = vendor.lower()
    return "ubiquiti" in normalized or "unifi" in normalized


def client_is_unifi(client: object) -> bool:
    """Determine if a client is a UniFi device."""
    flag = _client_unifi_flag(client)
    if flag is not None:
        return flag
    if _client_has_ucore_device_info(client):
        return True
    return _vendor_is_unifi(_client_vendor(client))


def _classify_client_from_ucore(client: object) -> str | None:
    ucore = _client_ucore_info(client)
    if not ucore:
        return None
    return _classify_by_unifi_info(ucore)


def _classify_client_from_name(client: object) -> str | None:
    name = client_display_name(client)
    if not name:
        return None
    return _classify_by_name(name)


def _classify_client_from_vendor(client: object) -> str | None:
    vendor = _client_vendor(client)
    if not vendor:
        return None
    return _classify_by_vendor(vendor)


def classify_client_type(client: object) -> str:
    """Classify a client into a device category.

    Detection priority:
    1. UniFi device info (product_line, model)
    2. Display name heuristics
    3. OUI/vendor patterns

    Returns one of: camera, tv, phone, printer, nas, speaker, game_console, iot, client
    """
    for classifier in (
        _classify_client_from_ucore,
        _classify_client_from_name,
        _classify_client_from_vendor,
    ):
        category = classifier(client)
        if category:
            return category

    return "client"


def client_display_name(client: object) -> str | None:
    """Get display name for a client.

    User-assigned names win (Network alias, then the UniFi device name that
    Protect/Talk expose via ucore). The hostname ranks above the ucore model
    string because it is per device, while the model is not: cameras whose
    ucore block lacks a name would otherwise all be labelled by their model.
    """
    return (
        first_string_field(client, "name")
        or _client_ucore_name(client)
        or first_string_field(client, "hostname")
        or _client_ucore_model(client)
        or first_string_field(client, "mac")
    )
