"""Capteurs : téléphone admin (convention commune) et occupation des stockages."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .admin_phone import (
    ADMIN_TARGET_SUFFIX,
    ATTR_NOTIFY_SERVICE,
    CONF_ADMIN_NOTIFY_TARGET,
    normalize_target,
)
from .const import DOMAIN, NAME, STORAGE_DATA
from .coordinator import PartitionMapConfigEntry, PartitionMapCoordinator


def device_info(entry_id: str) -> DeviceInfo:
    return DeviceInfo(identifiers={(DOMAIN, entry_id)}, name=NAME)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PartitionMapConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [AdminNotifyTargetSensor(entry)]
    # Les montages ajoutés plus tard apparaissent au prochain rechargement.
    entities.extend(StorageUsageSensor(coordinator, sid) for sid in coordinator.data.storages)
    async_add_entities(entities)


class AdminNotifyTargetSensor(SensorEntity):
    """Cible de notification de l'administrateur (convention commune SDR)."""

    _attr_has_entity_name = True
    _attr_translation_key = "admin_notify_target"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(self, entry: PartitionMapConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}{ADMIN_TARGET_SUFFIX}"
        self._attr_device_info = device_info(entry.entry_id)

    @property
    def _target(self) -> str | None:
        return normalize_target(self._entry.data.get(CONF_ADMIN_NOTIFY_TARGET))

    @property
    def native_value(self) -> str | None:
        return self._target  # None → état "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {ATTR_NOTIFY_SERVICE: self._target}


class StorageUsageSensor(CoordinatorEntity[PartitionMapCoordinator], SensorEntity):
    """Occupation en % de la data active ou d'un montage réseau."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: PartitionMapCoordinator, storage_id: str) -> None:
        super().__init__(coordinator)
        self._sid = storage_id
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_usage_{storage_id}"
        self._attr_device_info = device_info(entry_id)
        if storage_id == STORAGE_DATA:
            self._attr_translation_key = "data_usage"
        else:
            self._attr_translation_key = "mount_usage"
            self._attr_translation_placeholders = {"name": storage_id}

    @property
    def available(self) -> bool:
        return super().available and self._sid in self.coordinator.data.storages

    @property
    def native_value(self) -> float | None:
        storage = self.coordinator.data.storages.get(self._sid)
        return storage.percent if storage else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        storage = self.coordinator.data.storages.get(self._sid)
        if storage is None:
            return {}
        return {
            "used_bytes": storage.used_bytes,
            "total_bytes": storage.total_bytes,
            "free_bytes": storage.free_bytes,
            "kind": storage.kind,
            "mount_type": storage.mount_type,
        }
