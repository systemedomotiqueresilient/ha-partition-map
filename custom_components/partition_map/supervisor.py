"""Accès en lecture à l'API du Supervisor."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

try:  # Core récent : client passthrough (non réexporté par hassio/__init__.py)
    from homeassistant.components.hassio.handler import (
        get_supervisor_passthrough_client,
    )
except ImportError:  # Core plus ancien : l'instance HassIO est dans hass.data
    get_supervisor_passthrough_client = None


async def async_supervisor_get(hass: HomeAssistant, path: str, timeout: int = 10) -> dict[str, Any]:
    """GET sur le Supervisor ; renvoie le contenu de "data".

    Lève HassioAPIError en cas d'échec. aiohasupervisor n'a pas de module
    "hardware" : on passe par le client passthrough de l'intégration hassio
    (API interne, à surveiller à chaque version de Home Assistant).
    """
    if get_supervisor_passthrough_client is not None:
        client = get_supervisor_passthrough_client(hass)
    else:
        client = hass.data["hassio"]
    result = await client.send_command(path, method="get", timeout=timeout)
    if isinstance(result, dict) and "result" in result and "data" in result:
        return result["data"]
    return result
