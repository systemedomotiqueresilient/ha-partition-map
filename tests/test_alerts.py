"""Alertes d'espace disque et de partition orpheline."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant, ServiceCall
import pytest

from custom_components.partition_map.alerts import (
    LEVEL_CRITICAL,
    LEVEL_OK,
    LEVEL_WARNING,
    AlertManager,
    compute_level,
    format_bytes,
)

from .conftest import GB, make_entry


@pytest.mark.parametrize(
    ("percent", "previous", "expected"),
    [
        (50, LEVEL_OK, LEVEL_OK),
        (85, LEVEL_OK, LEVEL_WARNING),
        (96, LEVEL_OK, LEVEL_CRITICAL),
        (96, LEVEL_WARNING, LEVEL_CRITICAL),
        (84, LEVEL_WARNING, LEVEL_WARNING),  # hystérésis : 84 > 85 - 2
        (82, LEVEL_WARNING, LEVEL_OK),
        (94, LEVEL_CRITICAL, LEVEL_CRITICAL),  # 94 > 95 - 2
        (90, LEVEL_CRITICAL, LEVEL_WARNING),
        (None, LEVEL_WARNING, LEVEL_WARNING),
    ],
)
def test_compute_level(percent: float | None, previous: int, expected: int) -> None:
    assert compute_level(percent, previous, 85, 95) == expected


def test_format_bytes() -> None:
    units = ["o", "Ko", "Mo", "Go", "To"]
    assert format_bytes(512, units) == "512 o"
    assert format_bytes(int(33.6 * GB), units) == "33.6 Go"
    assert format_bytes(int(33.6 * GB), units, ",") == "33,6 Go"
    assert format_bytes(int(215.51 * GB), units) == "216 Go"


@pytest.fixture
def phone(hass: HomeAssistant) -> list[ServiceCall]:
    calls: list[ServiceCall] = []

    async def handler(call: ServiceCall) -> None:
        calls.append(call)

    hass.services.async_register("notify", "mobile_app_pixel_9", handler)
    return calls


@pytest.fixture
def persistent():
    with patch("custom_components.partition_map.alerts.persistent_notification") as mock:
        yield mock


async def _setup(hass: HomeAssistant, **data: Any):
    entry = make_entry(data={"admin_notify_target": "notify.mobile_app_pixel_9", **data})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _titles(calls: list[ServiceCall]) -> list[str]:
    return [c.data["title"] for c in calls]


async def test_threshold_crossing_once(
    hass: HomeAssistant, supervisor, ha_deps, phone, persistent
) -> None:
    hass.config.language = "fr"
    entry = await _setup(hass)
    coordinator = entry.runtime_data

    # Au démarrage : BackUP_HAOS à 92,8 % (avertissement) + partition orpheline
    assert sorted(_titles(phone)) == [
        "ℹ️ haos-test - Partition orpheline",
        "⚠️ haos-test - Stockage presque plein",
    ]
    warning = next(c for c in phone if "Stockage" in c.data["title"])
    assert warning.data["data"] == {
        "tag": "partition_map_BackUP_HAOS",
        "notification_icon": "mdi:harddisk",
    }
    assert warning.data["message"] == (
        "Stockage réseau BackUP_HAOS : 92,8 % utilisé (200 Go sur 216 Go, 15,5 Go libres)"
    )
    assert persistent.async_create.call_count == 2

    # Nouvelle lecture identique : pas de doublon
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert len(phone) == 2

    # Passage en critique : nouvelle alerte
    supervisor.mounts["BackUP_HAOS"] = (210 * GB, 215.51 * GB)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _titles(phone)[-1] == "🚨 haos-test - Stockage critique"

    # Redescente franche : réarmement et notification persistante retirée
    supervisor.mounts["BackUP_HAOS"] = (150 * GB, 215.51 * GB)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert coordinator.alerts.levels["BackUP_HAOS"] == LEVEL_OK
    persistent.async_dismiss.assert_called_with(hass, "partition_map_BackUP_HAOS")

    # Nouveau franchissement : nouvelle alerte
    supervisor.mounts["BackUP_HAOS"] = (190 * GB, 215.51 * GB)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert len(phone) == 4


async def test_no_target_persistent_only(
    hass: HomeAssistant, supervisor, ha_deps, phone, persistent
) -> None:
    await _setup(hass, admin_notify_target=None)
    assert phone == []
    assert persistent.async_create.call_count == 2


async def test_missing_service_logged(
    hass: HomeAssistant, supervisor, ha_deps, persistent, caplog
) -> None:
    await _setup(hass, admin_notify_target="notify.mobile_app_disparu")
    assert "notify.mobile_app_disparu introuvable" in caplog.text
    assert persistent.async_create.call_count == 2


async def test_levels_survive_restart(
    hass: HomeAssistant, supervisor, ha_deps, phone, persistent, hass_storage
) -> None:
    entry = await _setup(hass)
    assert len(phone) == 2
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    manager = AlertManager(hass, entry)
    await manager.async_load()
    assert manager.levels["BackUP_HAOS"] == LEVEL_WARNING
    assert manager.orphans_notified == {"/dev/sdb8"}

    # Rechargement : rien n'est renvoyé
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert len(phone) == 2

    # Suppression définitive : l'état des alertes est effacé
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert f"partition_map.{entry.entry_id}.alerts" not in hass_storage


async def test_english_texts(hass: HomeAssistant, supervisor, ha_deps, phone, persistent) -> None:
    hass.config.language = "en"
    await _setup(hass)
    assert "⚠️ haos-test - Storage almost full" in _titles(phone)
    warning = next(c for c in phone if "Storage" in c.data["title"])
    assert "92.8% used (200 GB of 216 GB, 15.5 GB free)" in warning.data["message"]


async def test_notify_entity_target(hass: HomeAssistant, supervisor, ha_deps, persistent) -> None:
    """Module 1.1.0 : une entité notify passe par notify.send_message, sans data."""
    sent: list[ServiceCall] = []

    async def send_message(call: ServiceCall) -> None:
        sent.append(call)

    hass.services.async_register("notify", "send_message", send_message)
    hass.states.async_set("notify.pixel_9", "unknown")
    await _setup(hass, admin_notify_target="notify.pixel_9")

    assert len(sent) == 2
    assert {c.data["entity_id"] for c in sent} == {"notify.pixel_9"}
    assert all("data" not in c.data for c in sent)
