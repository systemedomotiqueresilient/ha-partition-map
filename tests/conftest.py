"""Fixtures communes aux tests de Partition Map."""

from __future__ import annotations

from collections.abc import Generator
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.components.hassio.handler import HassioAPIError
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.partition_map.admin_phone import ATTR_NOTIFY_SERVICE
from custom_components.partition_map.const import DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"

HARDWARE = json.loads((Path(__file__).parent / "fixtures" / "hardware_haos_vm.json").read_text())
GB = 1_000_000_000


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Autorise le chargement de custom_components/ pendant les tests."""


class FakeSupervisor:
    """Réponses du Supervisor modifiables pendant un test."""

    def __init__(self) -> None:
        self.data_usage: tuple[float, float] | None = (29.4 * GB, 35.4 * GB)
        self.mounts: dict[str, tuple[float, float] | None] = {
            "BackUP_HAOS": (200 * GB, 215.51 * GB)
        }
        self.hardware_ok = True

    async def get(self, hass: HomeAssistant, path: str, timeout: int = 10) -> dict[str, Any]:
        if path == "/hardware/info":
            if not self.hardware_ok:
                raise HassioAPIError("boom")
            return HARDWARE["data"]
        if path == "/host/info":
            return {"hostname": "haos-test"}
        if path == "/host/disks/default/usage":
            if self.data_usage is None:
                raise HassioAPIError("no usage")
            used, total = self.data_usage
            return {"id": "root", "used_bytes": int(used), "total_bytes": int(total)}
        if path == "/mounts":
            return {"mounts": [{"name": n, "type": "cifs"} for n in self.mounts]}
        if path.startswith("/host/disks/") and path.endswith("/usage"):
            name = path.split("/")[3]
            value = self.mounts.get(name)
            if value is None:
                raise HassioAPIError("mount down")
            used, total = value
            return {"id": name, "used_bytes": int(used), "total_bytes": int(total)}
        raise HassioAPIError(f"unexpected {path}")


@pytest.fixture
def supervisor() -> Generator[FakeSupervisor]:
    fake = FakeSupervisor()
    with (
        patch(
            "custom_components.partition_map.coordinator.async_supervisor_get",
            side_effect=fake.get,
        ),
        patch(
            "custom_components.partition_map._async_register_frontend",
            new=AsyncMock(),
        ),
    ):
        yield fake


@pytest.fixture
async def ha_deps(hass: HomeAssistant) -> None:
    """Dépendances lourdes (hassio, http…) déclarées chargées sans les démarrer."""
    from homeassistant.setup import async_setup_component

    hass.config.components.update({"hassio", "http", "panel_custom", "websocket_api"})
    assert await async_setup_component(hass, "persistent_notification", {})


def add_sibling_target(
    hass: HomeAssistant,
    platform: str,
    value: str | None,
    entry_id: str = "sibling",
    domain: str = "sensor",
) -> str:
    """Simule l'entité « téléphone admin » d'une intégration sœur."""
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        domain,
        platform,
        f"{entry_id}_admin_notify_target",
        suggested_object_id=f"{platform}_{entry_id}_admin_phone",
    )
    hass.states.async_set(entity.entity_id, value or "unknown", {ATTR_NOTIFY_SERVICE: value})
    return entity.entity_id


def make_entry(**kwargs: Any) -> MockConfigEntry:
    params: dict[str, Any] = {
        "domain": DOMAIN,
        "title": "Partition Map",
        "data": {"admin_notify_target": None},
        "version": 1,
        "minor_version": 2,
    }
    params.update(kwargs)
    return MockConfigEntry(**params)
