"""Diagnostics : le modèle complet, utile pour les rapports de bug."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .admin_phone import MODULE_VERSION
from .const import VERSION
from .coordinator import PartitionMapConfigEntry

TO_REDACT = {"serial"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PartitionMapConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "version": VERSION,
        "admin_phone_module": MODULE_VERSION,
        "entry": {"data": dict(entry.data), "options": dict(entry.options)},
        "alerts": {
            "levels": coordinator.alerts.levels if coordinator.alerts else {},
            "orphans_notified": sorted(coordinator.alerts.orphans_notified)
            if coordinator.alerts
            else [],
        },
        "layout": async_redact_data(data.as_dict(), TO_REDACT) if data else {},
    }
