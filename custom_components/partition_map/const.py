"""Constantes de Partition Map."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "partition_map"
NAME: Final = "Partition Map"
VERSION: Final = "0.6.0"

# L'occupation est relue souvent, la table des partitions rarement.
UPDATE_INTERVAL: Final = timedelta(minutes=5)
LAYOUT_INTERVAL: Final = timedelta(minutes=30)
MOUNT_USAGE_TIMEOUT: Final = 30

PANEL_URL_PATH: Final = "partition-map"
PANEL_COMPONENT: Final = "partition-map-panel"
PANEL_ICON: Final = "mdi:harddisk"
STATIC_URL: Final = "/partition_map_static"

# Options des alertes
CONF_WARNING_THRESHOLD: Final = "warning_threshold"
CONF_CRITICAL_THRESHOLD: Final = "critical_threshold"
CONF_INCLUDE_MOUNTS: Final = "include_mounts"
DEFAULT_WARNING_THRESHOLD: Final = 85
DEFAULT_CRITICAL_THRESHOLD: Final = 95
DEFAULT_INCLUDE_MOUNTS: Final = True

# Niveau de détail du tableau sous chaque barre (la barre reste complète)
CONF_DETAIL_LEVEL: Final = "detail_level"
DETAIL_SIMPLE: Final = "simple"
DETAIL_DETAILED: Final = "detailed"
DEFAULT_DETAIL_LEVEL: Final = DETAIL_DETAILED
HYSTERESIS: Final = 2  # points de % sous le seuil pour réarmer une alerte

# Identifiant du stockage de la partition data active
STORAGE_DATA: Final = "data"

ALERT_STORE_VERSION: Final = 1
