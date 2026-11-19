"""Téléphone de l'administrateur : module commun aux intégrations SDR.

MODULE_VERSION = "1.0.0"

Ce fichier est copié À L'IDENTIQUE dans chaque intégration (Sentinel Report,
Deferred Restart, Entity Inventory, Package Keeper, Partition Map…). Une
intégration personnalisée ne peut pas dépendre d'un paquet partagé : la
cohérence repose sur la copie. Toute modification doit monter MODULE_VERSION
puis être recopiée dans tous les dépôts.

Convention :
- Chaque intégration crée SA PROPRE entité capteur (plateforme sensor,
  catégorie diagnostic) dont l'unique_id vaut "<entry_id>_admin_notify_target".
- État : le service de notification choisi (ex. "notify.mobile_app_pixel_9"),
  ou None (état "unknown" dans HA) s'il n'est pas défini.
- Attribut "notify_service" : même valeur que l'état.
- La valeur est copiée dans les données de l'entrée de config : elle reste
  valable si l'intégration sœur qui l'avait proposée est supprimée.

Ce module est en LECTURE SEULE : il ne modifie jamais une autre intégration,
une autre entité ni le registre.
"""

from __future__ import annotations

from typing import Final

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

MODULE_VERSION: Final = "1.0.0"

CONF_ADMIN_NOTIFY_TARGET: Final = "admin_notify_target"
ADMIN_TARGET_SUFFIX: Final = "_admin_notify_target"
ATTR_NOTIFY_SERVICE: Final = "notify_service"

# Domaines des intégrations sœurs dont on accepte la valeur.
SIBLING_PLATFORMS: Final = frozenset(
    {
        "deferred_restart",
        "entity_inventory",
        "package_keeper",  # réservé : intégration pas encore commencée
        "partition_map",
        "sentinel_report",
    }
)

_UNSET: Final = frozenset({"", "unknown", "unavailable", "none"})


def is_valid_target(value: object) -> bool:
    """Vrai pour une chaîne du type "notify.<service>"."""
    if not isinstance(value, str):
        return False
    value = value.strip()
    if value.lower() in _UNSET or not value.startswith("notify."):
        return False
    return len(value) > len("notify.")


def normalize_target(value: object) -> str | None:
    """Renvoie la cible nettoyée, ou None si elle n'est pas définie."""
    if isinstance(value, str) and is_valid_target(value):
        return value.strip()
    return None


@callback
def find_admin_targets(hass: HomeAssistant) -> list[str]:
    """Valeurs distinctes publiées par les entités « téléphone admin » sœurs.

    Lit le registre d'entités puis l'attribut notify_service dans le state
    machine. Une entité désactivée ou sans état est ignorée.
    """
    registry = er.async_get(hass)
    found: set[str] = set()
    for entry in registry.entities.values():
        if entry.platform not in SIBLING_PLATFORMS or entry.domain != "sensor":
            continue
        if not str(entry.unique_id).endswith(ADMIN_TARGET_SUFFIX):
            continue
        state = hass.states.get(entry.entity_id)
        if state is None:
            continue
        if target := normalize_target(state.attributes.get(ATTR_NOTIFY_SERVICE)):
            found.add(target)
    return sorted(found)


@callback
def list_mobile_notify_services(hass: HomeAssistant) -> list[str]:
    """Services notify.mobile_app_* actuellement enregistrés."""
    services = hass.services.async_services_for_domain("notify")
    return sorted(f"notify.{name}" for name in services if name.startswith("mobile_app_"))


@callback
def suggest_admin_target(
    hass: HomeAssistant, current: str | None = None
) -> tuple[str | None, list[str]]:
    """Valeur à préremplir et liste de choix pour un formulaire.

    - une valeur courante valide est toujours prioritaire ;
    - une seule valeur trouvée chez les sœurs : elle est préremplie ;
    - plusieurs valeurs différentes : rien n'est prérempli, liste de choix ;
    - aucune : liste des services notify.mobile_app_*.
    """
    siblings = find_admin_targets(hass)
    mobiles = list_mobile_notify_services(hass)
    current = normalize_target(current)

    choices: list[str] = []
    for value in (current, *siblings, *mobiles):
        if value and value not in choices:
            choices.append(value)

    if current:
        default = current
    elif len(siblings) == 1:
        default = siblings[0]
    else:
        default = None
    return default, choices
