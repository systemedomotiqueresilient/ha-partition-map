"""Téléphone de l'administrateur : module commun aux intégrations SDR.

MODULE_VERSION = "1.3.0"

Ce fichier est copié À L'IDENTIQUE dans chaque intégration (Sentinel Report,
Deferred Restart, Entity Inventory, Package Keeper, Partition Map, Outdoor Brief…). Une
intégration personnalisée ne peut pas dépendre d'un paquet partagé : la
cohérence repose sur la copie. Toute modification doit monter MODULE_VERSION
puis être recopiée dans tous les dépôts.

Convention :
- Chaque intégration crée SA PROPRE entité capteur (plateforme sensor,
  catégorie diagnostic) dont l'unique_id vaut "<entry_id>_admin_notify_target".
- État : la cible choisie, ou None (état "unknown" dans HA) si elle n'est pas
  définie. Deux formes sont acceptées (1.1.0) : un service de notification
  (ex. "notify.mobile_app_pixel_9") ou une entité notify (ex. "notify.pixel_9").
- Attribut "notify_service" : même valeur que l'état.
- Attribut "admin_phone_convention" (1.3.0) : version de la convention,
  écrit par admin_sensor_attributes. Avec le codeowner SDR du manifest, il
  permet de reconnaître une sœur absente de SIBLING_PLATFORMS.
- La valeur est copiée dans les données de l'entrée de config : elle reste
  valable si l'intégration sœur qui l'avait proposée est supprimée.

Ce module est en LECTURE SEULE : il ne modifie jamais une autre intégration,
une autre entité ni le registre. Sa seule action est l'envoi d'une
notification vers la cible (async_notify_admin).
"""

from __future__ import annotations

import logging
from typing import Any, Final

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.loader import IntegrationNotLoaded, async_get_loaded_integration
from homeassistant.util import slugify
import voluptuous as vol

MODULE_VERSION: Final = "1.3.0"

_LOGGER = logging.getLogger(__name__)

CONF_ADMIN_NOTIFY_TARGET: Final = "admin_notify_target"
ADMIN_TARGET_SUFFIX: Final = "_admin_notify_target"
ATTR_NOTIFY_SERVICE: Final = "notify_service"

# Reconnaissance ouverte des sœurs (1.3.0).
ATTR_CONVENTION: Final = "admin_phone_convention"
CONVENTION_VERSION: Final = 1
SDR_CODEOWNER: Final = "@systemedomotiqueresilient"

# Domaines des intégrations sœurs acceptés sans marqueur (règles 1.2.0).
# Une sœur absente de cette liste est reconnue par is_open_sibling (1.3.0).
SIBLING_PLATFORMS: Final = frozenset(
    {
        "deferred_restart",
        "entity_inventory",
        "outdoor_brief",
        "package_keeper",
        "partition_map",
        "sentinel_report",
    }
)

_UNSET: Final = frozenset({"", "unknown", "unavailable", "none"})


def is_valid_target(value: object) -> bool:
    """Vrai pour une chaîne du type "notify.<service>" ou "notify.<entité>"."""
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


def admin_sensor_attributes(target: object) -> dict[str, Any]:
    """Attributs du capteur « téléphone admin » (1.3.0).

    À utiliser dans extra_state_attributes : notify_service (cible ou None)
    et le marqueur de convention qui permet la reconnaissance ouverte.
    """
    return {
        ATTR_NOTIFY_SERVICE: normalize_target(target),
        ATTR_CONVENTION: CONVENTION_VERSION,
    }


@callback
def target_exists(hass: HomeAssistant, target: object) -> bool:
    """Vrai si la cible est une entité notify présente ou un service notify enregistré."""
    target = normalize_target(target)
    if target is None:
        return False
    if hass.states.get(target) is not None:
        return True
    name = target.removeprefix("notify.")
    return name != "send_message" and hass.services.has_service("notify", name)


@callback
def is_sdr_integration(hass: HomeAssistant, domain: str) -> bool:
    """Vrai si l'intégration chargée déclare le codeowner SDR dans son manifest."""
    try:
        integration = async_get_loaded_integration(hass, domain)
    except (IntegrationNotLoaded, KeyError):
        return False
    codeowners = integration.manifest.get("codeowners") or []
    return SDR_CODEOWNER in codeowners


@callback
def is_open_sibling(hass: HomeAssistant, entry: er.RegistryEntry) -> bool:
    """Sœur hors liste (1.3.0) : les cinq critères doivent tous passer.

    1. unique_id terminé par _admin_notify_target ;
    2. capteur de catégorie diagnostic ;
    3. manifest de l'intégration avec le codeowner SDR ;
    4. attribut admin_phone_convention égal à CONVENTION_VERSION ;
    5. notify_service désigne une cible qui existe.
    """
    if entry.domain != "sensor" or not str(entry.unique_id).endswith(ADMIN_TARGET_SUFFIX):
        return False
    if entry.entity_category != EntityCategory.DIAGNOSTIC:
        return False
    if not is_sdr_integration(hass, entry.platform):
        return False
    state = hass.states.get(entry.entity_id)
    if state is None:
        return False
    marker = state.attributes.get(ATTR_CONVENTION)
    if type(marker) is not int or marker != CONVENTION_VERSION:
        return False
    return target_exists(hass, state.attributes.get(ATTR_NOTIFY_SERVICE))


@callback
def find_admin_targets(hass: HomeAssistant) -> list[str]:
    """Valeurs distinctes publiées par les entités « téléphone admin » sœurs.

    Lit le registre d'entités puis l'attribut notify_service dans le state
    machine. Une entité désactivée ou sans état est ignorée. Une plateforme
    de SIBLING_PLATFORMS suit les règles 1.2.0 ; une autre doit passer
    is_open_sibling (1.3.0).
    """
    registry = er.async_get(hass)
    found: set[str] = set()
    for entry in registry.entities.values():
        if entry.domain != "sensor":
            continue
        if entry.platform in SIBLING_PLATFORMS:
            if not str(entry.unique_id).endswith(ADMIN_TARGET_SUFFIX):
                continue
        elif not is_open_sibling(hass, entry):
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
def list_mobile_notify_entities(hass: HomeAssistant) -> list[str]:
    """Entités notify de l'application mobile (appelées via notify.send_message)."""
    registry = er.async_get(hass)
    return sorted(
        entry.entity_id
        for entry in registry.entities.values()
        if entry.domain == "notify"
        and entry.platform == "mobile_app"
        and not entry.disabled_by
        and hass.states.get(entry.entity_id) is not None
    )


@callback
def suggest_admin_target(
    hass: HomeAssistant, current: str | None = None
) -> tuple[str | None, list[str]]:
    """Valeur à préremplir et liste de choix pour un formulaire.

    - une valeur courante valide est toujours prioritaire ;
    - une seule valeur trouvée chez les sœurs : elle est préremplie ;
    - plusieurs valeurs différentes : rien n'est prérempli, liste de choix ;
    - aucune : liste des services notify.mobile_app_* puis des entités notify
      de l'application mobile (1.1.0).
    """
    siblings = find_admin_targets(hass)
    mobiles = list_mobile_notify_services(hass) + list_mobile_notify_entities(hass)
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


@callback
def mobile_service_for_entity(hass: HomeAssistant, target: object) -> str | None:
    """Service notify.mobile_app_* du même appareil qu'une entité notify (1.3.0).

    notify.send_message ne transmet ni image, ni tag, ni lien. Pour une entité
    notify de l'application mobile, on retrouve le service du même appareil :
    nom enregistré par l'application, puis nom de l'appareil, puis nom donné
    par l'utilisateur. None si rien ne correspond.
    """
    target = normalize_target(target)
    if target is None:
        return None
    entry = er.async_get(hass).async_get(target)
    if entry is None or entry.domain != "notify" or entry.platform != "mobile_app":
        return None
    names: list[str] = []
    if entry.config_entry_id and (
        config_entry := hass.config_entries.async_get_entry(entry.config_entry_id)
    ):
        names.append(str(config_entry.data.get("device_name") or ""))
    if entry.device_id and (device := dr.async_get(hass).async_get(entry.device_id)):
        names.extend((device.name or "", device.name_by_user or ""))
    for name in names:
        service = f"mobile_app_{slugify(name)}" if name else ""
        if service and hass.services.has_service("notify", service):
            return f"notify.{service}"
    return None


async def async_notify_admin(
    hass: HomeAssistant,
    target: object,
    title: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> bool:
    """Envoie une notification à la cible ; renvoie True si l'appel a abouti.

    - entité notify de l'application mobile avec `data` (1.3.0) : envoi au
      service notify.mobile_app_* du même appareil, pour garder image, tag et
      lien ; s'il est introuvable, envoi sans data comme ci-dessous ;
    - entité notify existante (ex. "notify.pixel_9") : action notify.send_message ;
    - sinon service notify.<nom> enregistré (ex. "notify.mobile_app_pixel_9") :
      appel direct, avec `data` transmis tel quel ;
    - cible absente ou introuvable : rien n'est envoyé, False.

    Ne lève jamais d'exception : un échec d'envoi ne doit pas bloquer
    l'intégration appelante (il est seulement journalisé). `data` n'est pas
    transmis à notify.send_message, qui ne l'accepte pas.
    """
    target = normalize_target(target)
    if target is None:
        return False
    if data and (service := mobile_service_for_entity(hass, target)):
        target = service
    name = target.removeprefix("notify.")
    try:
        if hass.states.get(target) is not None and hass.services.has_service(
            "notify", "send_message"
        ):
            await hass.services.async_call(
                "notify",
                "send_message",
                {"entity_id": target, "title": title, "message": message},
                blocking=True,
            )
            return True
        if name != "send_message" and hass.services.has_service("notify", name):
            payload: dict[str, Any] = {"title": title, "message": message}
            if data:
                payload["data"] = data
            await hass.services.async_call("notify", name, payload, blocking=True)
            return True
    except (HomeAssistantError, vol.Invalid) as err:
        _LOGGER.warning("Notification vers %s impossible : %s", target, err)
        return False
    _LOGGER.warning("Notification impossible : %s introuvable", target)
    return False
