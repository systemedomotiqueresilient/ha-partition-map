"""Coordinator : disques, partitions et occupation des stockages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.hassio.handler import HassioAPIError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_INCLUDE_MOUNTS,
    DEFAULT_INCLUDE_MOUNTS,
    DOMAIN,
    LAYOUT_INTERVAL,
    MOUNT_USAGE_TIMEOUT,
    STORAGE_DATA,
    UPDATE_INTERVAL,
)
from .layout import Disk, as_dict, build_layout
from .supervisor import async_supervisor_get

if TYPE_CHECKING:
    from .alerts import AlertManager

_LOGGER = logging.getLogger(__name__)

type PartitionMapConfigEntry = ConfigEntry[PartitionMapCoordinator]


@dataclass(slots=True)
class StorageUsage:
    """Occupation d'un stockage : la data active ou un montage réseau."""

    id: str
    kind: str  # "data" ou "mount"
    used_bytes: int
    total_bytes: int
    mount_type: str | None = None

    @property
    def free_bytes(self) -> int:
        return max(self.total_bytes - self.used_bytes, 0)

    @property
    def percent(self) -> float | None:
        if self.total_bytes <= 0:
            return None
        return round(self.used_bytes / self.total_bytes * 100, 1)


@dataclass(slots=True)
class PartitionMapData:
    disks: list[Disk]
    storages: dict[str, StorageUsage] = field(default_factory=dict)
    hostname: str = "Home Assistant"
    updated: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "disks": as_dict(self.disks),
            "storages": {
                sid: {**asdict(st), "free_bytes": st.free_bytes, "percent": st.percent}
                for sid, st in self.storages.items()
            },
            "hostname": self.hostname,
            "updated": self.updated,
        }


def _usage(sid: str, kind: str, raw: dict[str, Any], mount_type: str | None = None) -> StorageUsage:
    return StorageUsage(
        id=sid,
        kind=kind,
        used_bytes=int(raw.get("used_bytes") or 0),
        total_bytes=int(raw.get("total_bytes") or 0),
        mount_type=mount_type,
    )


class PartitionMapCoordinator(DataUpdateCoordinator[PartitionMapData]):
    """Occupation toutes les 5 min, table des partitions toutes les 30 min."""

    config_entry: PartitionMapConfigEntry

    def __init__(self, hass: HomeAssistant, entry: PartitionMapConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.alerts: AlertManager | None = None
        self._disks: list[Disk] | None = None
        self._hostname = "Home Assistant"
        self._layout_at: datetime | None = None
        self._force_layout = False

    async def async_refresh_layout(self) -> None:
        """Relecture complète, demandée par le bouton « Actualiser »."""
        self._force_layout = True
        await self.async_refresh()

    async def _async_update_data(self) -> PartitionMapData:
        now = dt_util.utcnow()
        if (
            self._force_layout
            or self._disks is None
            or self._layout_at is None
            or now - self._layout_at >= LAYOUT_INTERVAL
        ):
            await self._async_update_layout()
            self._layout_at = now
            self._force_layout = False

        data = PartitionMapData(
            disks=self._disks or [],
            storages=await self._async_storages(),
            hostname=self._hostname,
            updated=now.isoformat(),
        )

        if self.alerts is not None:
            try:
                await self.alerts.async_process(data)
            except Exception:
                _LOGGER.exception("Échec du traitement des alertes")
        return data

    async def _async_update_layout(self) -> None:
        try:
            hardware = await async_supervisor_get(self.hass, "/hardware/info")
        except HassioAPIError as err:
            raise UpdateFailed(f"Lecture de /hardware/info impossible : {err}") from err
        self._disks = build_layout(hardware)

        try:
            host = await async_supervisor_get(self.hass, "/host/info")
            self._hostname = host.get("hostname") or self._hostname
        except HassioAPIError as err:
            _LOGGER.debug("Nom d'hôte indisponible : %s", err)

    async def _async_storages(self) -> dict[str, StorageUsage]:
        storages: dict[str, StorageUsage] = {}
        try:
            raw = await async_supervisor_get(self.hass, "/host/disks/default/usage")
            storages[STORAGE_DATA] = _usage(STORAGE_DATA, "data", raw)
        except HassioAPIError as err:
            _LOGGER.debug("Occupation de la data indisponible : %s", err)

        if not self.config_entry.options.get(CONF_INCLUDE_MOUNTS, DEFAULT_INCLUDE_MOUNTS):
            return storages

        try:
            mounts = (await async_supervisor_get(self.hass, "/mounts")).get("mounts", [])
        except HassioAPIError as err:
            _LOGGER.debug("Liste des montages indisponible : %s", err)
            return storages

        for mount in mounts:
            name = mount.get("name")
            if not name or name == STORAGE_DATA:
                continue
            try:
                raw = await async_supervisor_get(
                    self.hass, f"/host/disks/{name}/usage", timeout=MOUNT_USAGE_TIMEOUT
                )
            except HassioAPIError as err:
                # Serveur injoignable, montage inactif ou Supervisor trop ancien
                _LOGGER.debug("Occupation du montage %s indisponible : %s", name, err)
                continue
            storages[name] = _usage(name, "mount", raw, mount.get("type"))
        return storages
