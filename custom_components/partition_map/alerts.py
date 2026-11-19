"""Alertes d'espace disque et de partition orpheline.

- Une notification par franchissement de seuil (avertissement puis critique).
- Réarmement quand l'occupation redescend de HYSTERESIS points sous le seuil.
- Niveaux mémorisés sur disque : un redémarrage ne renvoie pas la même alerte.
- Destinataires : notification persistante toujours, téléphone admin s'il est défini.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .admin_phone import CONF_ADMIN_NOTIFY_TARGET, normalize_target
from .const import (
    ALERT_STORE_VERSION,
    CONF_CRITICAL_THRESHOLD,
    CONF_WARNING_THRESHOLD,
    DEFAULT_CRITICAL_THRESHOLD,
    DEFAULT_WARNING_THRESHOLD,
    DOMAIN,
    HYSTERESIS,
    STORAGE_DATA,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import PartitionMapData, StorageUsage

_LOGGER = logging.getLogger(__name__)

LEVEL_OK = 0
LEVEL_WARNING = 1
LEVEL_CRITICAL = 2

ORPHAN_ID = "orphan"

TEXTS = {
    "fr": {
        "warning_title": "⚠️ {host} - Stockage presque plein",
        "critical_title": "🚨 {host} - Stockage critique",
        "usage": "{label} : {percent} % utilisé ({used} sur {total}, {free} libres)",
        "data_label": "Données Home Assistant",
        "mount_label": "Stockage réseau {name}",
        "orphan_title": "ℹ️ {host} - Partition orpheline",
        "orphan": "{devices} n'est plus utilisée : {size} d'espace mort. "
        "Ancienne partition de données laissée après un déplacement du disque de données.",
        "units": ["o", "Ko", "Mo", "Go", "To"],
    },
    "en": {
        "warning_title": "⚠️ {host} - Storage almost full",
        "critical_title": "🚨 {host} - Storage critical",
        "usage": "{label}: {percent}% used ({used} of {total}, {free} free)",
        "data_label": "Home Assistant data",
        "mount_label": "Network storage {name}",
        "orphan_title": "ℹ️ {host} - Orphan partition",
        "orphan": "{devices} is no longer used: {size} of dead space. "
        "Old data partition left behind after moving the data disk.",
        "units": ["B", "kB", "MB", "GB", "TB"],
    },
}


def compute_level(
    percent: float | None,
    previous: int,
    warning: float,
    critical: float,
    hysteresis: float = HYSTERESIS,
) -> int:
    """Niveau d'alerte avec hystérésis à la descente."""
    if percent is None:
        return previous
    raw = (
        LEVEL_CRITICAL if percent >= critical else LEVEL_WARNING if percent >= warning else LEVEL_OK
    )
    if raw >= previous:
        return raw
    threshold = critical if previous == LEVEL_CRITICAL else warning
    if percent > threshold - hysteresis:
        return previous
    return raw


def format_bytes(value: int, units: list[str]) -> str:
    size = float(value)
    i = 0
    while size >= 1000 and i < len(units) - 1:
        size /= 1000
        i += 1
    decimals = 0 if i == 0 or size >= 100 else 1
    return f"{size:.{decimals}f} {units[i]}"


class AlertManager:
    """Décide et envoie les alertes ; état persistant par entrée de config."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, ALERT_STORE_VERSION, f"{DOMAIN}.{entry.entry_id}.alerts"
        )
        self.levels: dict[str, int] = {}
        self.orphans_notified: set[str] = set()

    async def async_load(self) -> None:
        stored = await self._store.async_load() or {}
        self.levels = {k: int(v) for k, v in stored.get("levels", {}).items()}
        self.orphans_notified = set(stored.get("orphans_notified", []))

    async def async_remove(self) -> None:
        await self._store.async_remove()

    @property
    def _texts(self) -> dict[str, Any]:
        lang = (self.hass.config.language or "en").split("-")[0]
        return TEXTS.get(lang, TEXTS["en"])

    async def async_process(self, data: PartitionMapData) -> None:
        options = self.entry.options
        warning = options.get(CONF_WARNING_THRESHOLD, DEFAULT_WARNING_THRESHOLD)
        critical = options.get(CONF_CRITICAL_THRESHOLD, DEFAULT_CRITICAL_THRESHOLD)
        changed = False

        for sid, storage in data.storages.items():
            previous = self.levels.get(sid, LEVEL_OK)
            level = compute_level(storage.percent, previous, warning, critical)
            if level > previous:
                await self._async_notify_storage(data, storage, level)
            elif level == LEVEL_OK and previous > LEVEL_OK:
                persistent_notification.async_dismiss(self.hass, self._notification_id(sid))
            if level != previous:
                self.levels[sid] = level
                changed = True

        orphans = {p.device: p.size for d in data.disks for p in d.orphans}
        if set(orphans) - self.orphans_notified:
            await self._async_notify_orphans(data, orphans)
        if set(orphans) != self.orphans_notified:
            self.orphans_notified = set(orphans)
            changed = True

        if changed:
            await self._store.async_save(
                {"levels": self.levels, "orphans_notified": sorted(self.orphans_notified)}
            )

    @staticmethod
    def _notification_id(sid: str) -> str:
        return f"{DOMAIN}_{sid}"

    def _label(self, storage: StorageUsage) -> str:
        t = self._texts
        if storage.id == STORAGE_DATA:
            return t["data_label"]
        return t["mount_label"].format(name=storage.id)

    async def _async_notify_storage(
        self, data: PartitionMapData, storage: StorageUsage, level: int
    ) -> None:
        t = self._texts
        key = "critical_title" if level == LEVEL_CRITICAL else "warning_title"
        title = t[key].format(host=data.hostname)
        message = t["usage"].format(
            label=self._label(storage),
            percent=storage.percent,
            used=format_bytes(storage.used_bytes, t["units"]),
            total=format_bytes(storage.total_bytes, t["units"]),
            free=format_bytes(storage.free_bytes, t["units"]),
        )
        await self._async_send(self._notification_id(storage.id), title, message)

    async def _async_notify_orphans(self, data: PartitionMapData, orphans: dict[str, int]) -> None:
        t = self._texts
        title = t["orphan_title"].format(host=data.hostname)
        message = t["orphan"].format(
            devices=", ".join(sorted(orphans)),
            size=format_bytes(sum(orphans.values()), t["units"]),
        )
        await self._async_send(self._notification_id(ORPHAN_ID), title, message)

    async def _async_send(self, notification_id: str, title: str, message: str) -> None:
        persistent_notification.async_create(
            self.hass, message, title=title, notification_id=notification_id
        )
        target = normalize_target(self.entry.data.get(CONF_ADMIN_NOTIFY_TARGET))
        if target is None:
            return
        domain, service = target.split(".", 1)
        if not self.hass.services.has_service(domain, service):
            _LOGGER.warning("Service de notification %s introuvable", target)
            return
        # Le tag fait remplacer la notification précédente sur le téléphone.
        await self.hass.services.async_call(
            domain,
            service,
            {"title": title, "message": message, "data": {"tag": notification_id}},
            blocking=False,
        )
