"""Mise en place, migration, entités et diagnostics."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.partition_map.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.partition_map.layout import build_layout

from .conftest import HARDWARE, make_entry


def _entity(hass: HomeAssistant, domain: str, unique_id: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(domain, "partition_map", unique_id)
    assert entity_id, unique_id
    return entity_id


async def test_layout_from_real_export() -> None:
    disks = build_layout(HARDWARE)
    boot, data = disks
    assert boot.is_boot and boot.device == "/dev/sdb"
    assert [p.device for p in boot.orphans] == ["/dev/sdb8"]
    assert round(boot.unallocated / 1e9, 2) == 2.15
    assert data.is_data and not data.gaps


async def test_setup_and_entities(hass: HomeAssistant, supervisor, ha_deps) -> None:
    entry = make_entry(data={"admin_notify_target": "notify.mobile_app_pixel_9"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    target = hass.states.get(_entity(hass, "sensor", f"{entry.entry_id}_admin_notify_target"))
    assert target.state == "notify.mobile_app_pixel_9"
    assert target.attributes["notify_service"] == "notify.mobile_app_pixel_9"
    reg = er.async_get(hass).async_get(target.entity_id)
    assert reg.entity_category == "diagnostic"

    data = hass.states.get(_entity(hass, "sensor", f"{entry.entry_id}_usage_data"))
    assert float(data.state) == 83.1
    mount = hass.states.get(_entity(hass, "sensor", f"{entry.entry_id}_usage_BackUP_HAOS"))
    assert float(mount.state) == 92.8
    assert mount.attributes["kind"] == "mount"

    orphan = hass.states.get(_entity(hass, "binary_sensor", f"{entry.entry_id}_orphan_partition"))
    assert orphan.state == "on"
    assert orphan.attributes["partitions"] == ["/dev/sdb8"]

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["version"] == "0.2.0"
    assert diag["layout"]["disks"][0]["serial"] == "**REDACTED**"
    assert diag["layout"]["hostname"] == "haos-test"

    # Montage devenu injoignable : capteur indisponible, pas d'échec global
    supervisor.mounts["BackUP_HAOS"] = None
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(mount.entity_id).state == "unavailable"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_migration_from_0_1_0(hass: HomeAssistant, supervisor, ha_deps) -> None:
    """Entrée 0.1.0 (data vide, 1.1) : migrée sans perte, cible non définie."""
    entry = make_entry(data={}, minor_version=1)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.minor_version == 2
    assert entry.data == {"admin_notify_target": None}
    target = hass.states.get(_entity(hass, "sensor", f"{entry.entry_id}_admin_notify_target"))
    assert target.state == "unknown"
    assert target.attributes["notify_service"] is None


async def test_future_version_refused(hass: HomeAssistant, supervisor, ha_deps) -> None:
    entry = make_entry(version=2, minor_version=1)
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_hardware_failure_retries(hass: HomeAssistant, supervisor, ha_deps) -> None:
    supervisor.hardware_ok = False
    entry = make_entry()
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_options_change_reloads(hass: HomeAssistant, supervisor, ha_deps) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.config_entries.async_update_entry(
        entry, data={"admin_notify_target": "notify.mobile_app_new"}
    )
    await hass.async_block_till_done()
    target = hass.states.get(_entity(hass, "sensor", f"{entry.entry_id}_admin_notify_target"))
    assert target.state == "notify.mobile_app_new"
