"""Convention commune « téléphone admin »."""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.partition_map.admin_phone import (
    MODULE_VERSION,
    SIBLING_PLATFORMS,
    find_admin_targets,
    is_valid_target,
    list_mobile_notify_services,
    normalize_target,
    suggest_admin_target,
)

from .conftest import add_sibling_target, make_entry


def _register_notify(hass: HomeAssistant, *names: str) -> None:
    for name in names:
        hass.services.async_register("notify", name, lambda call: None)


def test_module_header() -> None:
    assert MODULE_VERSION == "1.1.0"
    assert {
        "sentinel_report",
        "deferred_restart",
        "entity_inventory",
        "package_keeper",
        "partition_map",
    } == set(SIBLING_PLATFORMS)


def test_copy_is_reference_1_1_0() -> None:
    """admin_phone.py doit être la copie exacte de ha-sdr 1.1.0 (commit dfc42ab)."""
    source = Path(__file__).parents[1] / "custom_components/partition_map/admin_phone.py"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == (
        "32b3619e975eaeb0606252b4cdca9f3d2402854193f88619cd4bde383b30e1f9"
    )


def test_valid_target() -> None:
    assert is_valid_target("notify.mobile_app_pixel_9")
    assert not is_valid_target("notify.")
    assert not is_valid_target("mobile_app_pixel_9")
    assert not is_valid_target("unknown")
    assert not is_valid_target(None)
    assert normalize_target("  notify.x ") == "notify.x"
    assert normalize_target("unavailable") is None


async def test_none_found(hass: HomeAssistant) -> None:
    _register_notify(hass, "mobile_app_pixel_9", "mobile_app_tablette", "smtp")
    assert find_admin_targets(hass) == []
    assert list_mobile_notify_services(hass) == [
        "notify.mobile_app_pixel_9",
        "notify.mobile_app_tablette",
    ]
    default, choices = suggest_admin_target(hass)
    assert default is None
    assert choices == ["notify.mobile_app_pixel_9", "notify.mobile_app_tablette"]


async def test_one_found(hass: HomeAssistant) -> None:
    add_sibling_target(hass, "sentinel_report", "notify.mobile_app_pixel_9")
    assert find_admin_targets(hass) == ["notify.mobile_app_pixel_9"]
    default, choices = suggest_admin_target(hass)
    assert default == "notify.mobile_app_pixel_9"
    assert choices[0] == "notify.mobile_app_pixel_9"


async def test_same_value_twice_is_one(hass: HomeAssistant) -> None:
    add_sibling_target(hass, "sentinel_report", "notify.mobile_app_pixel_9", "a")
    add_sibling_target(hass, "deferred_restart", "notify.mobile_app_pixel_9", "b")
    assert find_admin_targets(hass) == ["notify.mobile_app_pixel_9"]
    assert suggest_admin_target(hass)[0] == "notify.mobile_app_pixel_9"


async def test_several_different(hass: HomeAssistant) -> None:
    add_sibling_target(hass, "sentinel_report", "notify.mobile_app_pixel_9", "a")
    add_sibling_target(hass, "entity_inventory", "notify.mobile_app_tablette", "b")
    _register_notify(hass, "mobile_app_pixel_9")
    default, choices = suggest_admin_target(hass)
    assert default is None  # à l'utilisateur de choisir
    assert choices == ["notify.mobile_app_pixel_9", "notify.mobile_app_tablette"]


async def test_current_value_wins(hass: HomeAssistant) -> None:
    add_sibling_target(hass, "sentinel_report", "notify.mobile_app_pixel_9")
    default, choices = suggest_admin_target(hass, "notify.mobile_app_autre")
    assert default == "notify.mobile_app_autre"
    assert choices[:2] == ["notify.mobile_app_autre", "notify.mobile_app_pixel_9"]


async def test_unlisted_platform_ignored(hass: HomeAssistant) -> None:
    add_sibling_target(hass, "spook", "notify.mobile_app_spook", "a")
    add_sibling_target(hass, "sentinel", "notify.mobile_app_sentinel", "b")
    # bon suffixe, plateforme listée, mais pas un capteur
    add_sibling_target(hass, "sentinel_report", "notify.mobile_app_x", "c", domain="select")
    # plateforme listée mais cible non définie
    add_sibling_target(hass, "deferred_restart", None, "d")
    assert find_admin_targets(hass) == []


async def test_entity_without_state_ignored(hass: HomeAssistant) -> None:
    er.async_get(hass).async_get_or_create("sensor", "sentinel_report", "x_admin_notify_target")
    assert find_admin_targets(hass) == []


async def test_sibling_removed_keeps_copied_value(hass: HomeAssistant, supervisor, ha_deps) -> None:
    """La valeur copiée dans l'entrée survit à la suppression de la sœur."""
    sibling = add_sibling_target(hass, "sentinel_report", "notify.mobile_app_pixel_9")
    default, _ = suggest_admin_target(hass)
    entry = make_entry(data={"admin_notify_target": default})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # L'intégration sœur disparaît : entité et état supprimés
    er.async_get(hass).async_remove(sibling)
    hass.states.async_remove(sibling)
    await hass.async_block_till_done()

    own = er.async_get(hass).async_get_entity_id(
        "sensor", "partition_map", f"{entry.entry_id}_admin_notify_target"
    )
    state = hass.states.get(own)
    assert state.state == "notify.mobile_app_pixel_9"
    assert state.attributes["notify_service"] == "notify.mobile_app_pixel_9"
    # Notre propre entité est désormais la seule source trouvée
    assert find_admin_targets(hass) == ["notify.mobile_app_pixel_9"]
