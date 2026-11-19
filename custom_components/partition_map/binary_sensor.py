"""Capteur binaire : espace disque mort détecté."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import PartitionMapConfigEntry, PartitionMapCoordinator
from .sensor import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PartitionMapConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([OrphanPartitionSensor(entry.runtime_data)])


class OrphanPartitionSensor(CoordinatorEntity[PartitionMapCoordinator], BinarySensorEntity):
    """Allumé quand une ancienne partition data n'est plus montée."""

    _attr_has_entity_name = True
    _attr_translation_key = "orphan_partition"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PartitionMapCoordinator) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_orphan_partition"
        self._attr_device_info = device_info(entry_id)

    @property
    def is_on(self) -> bool:
        return any(d.orphans for d in self.coordinator.data.disks)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        disks = self.coordinator.data.disks
        orphans = [p for d in disks for p in d.orphans]
        return {
            "partitions": [p.device for p in orphans],
            "orphan_bytes": sum(p.size for p in orphans),
            "unallocated_bytes": sum(d.unallocated for d in disks),
        }
