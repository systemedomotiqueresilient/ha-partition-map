"""Partition Map : vue façon GParted des disques de Home Assistant OS."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.frontend import async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import voluptuous as vol

from .admin_phone import CONF_ADMIN_NOTIFY_TARGET
from .alerts import AlertManager
from .const import (
    DOMAIN,
    NAME,
    PANEL_COMPONENT,
    PANEL_ICON,
    PANEL_URL_PATH,
    STATIC_URL,
    VERSION,
)
from .coordinator import PartitionMapConfigEntry, PartitionMapCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

FRONTEND_DIR = Path(__file__).parent / "frontend"
PANEL_JS = "partition-map-panel.js"


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """1.1 (v0.1.0, data vide) → 1.2 (cible du téléphone admin)."""
    if entry.version > 1:
        return False  # entrée créée par une version plus récente
    if entry.minor_version < 2:
        data = {**entry.data}
        data.setdefault(CONF_ADMIN_NOTIFY_TARGET, None)
        hass.config_entries.async_update_entry(entry, data=data, minor_version=2)
        _LOGGER.debug("Entrée %s migrée en 1.2", entry.entry_id)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PartitionMapConfigEntry) -> bool:
    """Configure l'intégration à partir de son entrée."""
    coordinator = PartitionMapCoordinator(hass, entry)
    coordinator.alerts = AlertManager(hass, entry)
    await coordinator.alerts.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await _async_register_frontend(hass)
    websocket_api.async_register_command(hass, ws_layout)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Cible ou seuils modifiés par l'options flow : on recharge.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PartitionMapConfigEntry) -> bool:
    """Décharge l'intégration et retire le panneau."""
    async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Suppression définitive : on efface l'état des alertes."""
    await AlertManager(hass, entry).async_remove()


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Sert le JS du panneau et l'ajoute à la barre latérale (admins seulement)."""
    if not hass.data.get(f"{DOMAIN}_static"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
        )
        hass.data[f"{DOMAIN}_static"] = True

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title=NAME,
        sidebar_icon=PANEL_ICON,
        # ?v= force le rechargement du JS après une mise à jour HACS
        module_url=f"{STATIC_URL}/{PANEL_JS}?v={VERSION}",
        require_admin=True,
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/layout",
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_layout(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Renvoie le modèle des disques et des stockages au panneau."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], "not_loaded", f"{NAME} n'est pas chargé")
        return
    coordinator: PartitionMapCoordinator = entries[0].runtime_data
    if msg["refresh"]:
        await coordinator.async_refresh_layout()
    if coordinator.data is None:
        connection.send_error(msg["id"], "no_data", "Aucune donnée disponible")
        return
    connection.send_result(msg["id"], coordinator.data.as_dict())
