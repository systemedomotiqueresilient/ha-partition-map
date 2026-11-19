"""Config flow et options flow de Partition Map."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.hassio import is_hassio
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from .admin_phone import (
    CONF_ADMIN_NOTIFY_TARGET,
    is_valid_target,
    normalize_target,
    suggest_admin_target,
)
from .const import (
    CONF_CRITICAL_THRESHOLD,
    CONF_INCLUDE_MOUNTS,
    CONF_WARNING_THRESHOLD,
    DEFAULT_CRITICAL_THRESHOLD,
    DEFAULT_INCLUDE_MOUNTS,
    DEFAULT_WARNING_THRESHOLD,
    DOMAIN,
    NAME,
)


def _target_field(hass: HomeAssistant, current: str | None) -> dict[Any, Any]:
    """Champ « téléphone admin » prérempli selon la convention commune."""
    default, choices = suggest_admin_target(hass, current)
    key = vol.Optional(
        CONF_ADMIN_NOTIFY_TARGET,
        description={"suggested_value": default} if default else None,
    )
    return {
        key: SelectSelector(
            SelectSelectorConfig(
                options=choices,
                custom_value=True,  # saisie libre possible
                mode=SelectSelectorMode.DROPDOWN,
                sort=False,
            )
        )
    }


def _check_target(user_input: dict[str, Any], errors: dict[str, str]) -> str | None:
    """Valide la cible saisie ; un champ vide signifie « non définie »."""
    raw = (user_input.get(CONF_ADMIN_NOTIFY_TARGET) or "").strip()
    if raw and not is_valid_target(raw):
        errors[CONF_ADMIN_NOTIFY_TARGET] = "invalid_target"
    return normalize_target(raw)


class PartitionMapConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ajout de l'intégration depuis l'interface."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # Les données viennent du Supervisor : HAOS ou Supervised uniquement.
        if not is_hassio(self.hass):
            return self.async_abort(reason="not_supervised")

        errors: dict[str, str] = {}
        if user_input is not None:
            target = _check_target(user_input, errors)
            if not errors:
                return self.async_create_entry(title=NAME, data={CONF_ADMIN_NOTIFY_TARGET: target})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(_target_field(self.hass, None)),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PartitionMapOptionsFlow()


class PartitionMapOptionsFlow(OptionsFlow):
    """Téléphone admin (écrit dans entry.data) et seuils d'alerte (options)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        errors: dict[str, str] = {}

        if user_input is not None:
            target = _check_target(user_input, errors)
            warning = int(user_input[CONF_WARNING_THRESHOLD])
            critical = int(user_input[CONF_CRITICAL_THRESHOLD])
            if critical <= warning:
                errors[CONF_CRITICAL_THRESHOLD] = "critical_below_warning"
            if not errors:
                # Source unique de vérité pour la cible : entry.data
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_ADMIN_NOTIFY_TARGET: target}
                )
                return self.async_create_entry(
                    data={
                        CONF_WARNING_THRESHOLD: warning,
                        CONF_CRITICAL_THRESHOLD: critical,
                        CONF_INCLUDE_MOUNTS: bool(user_input[CONF_INCLUDE_MOUNTS]),
                    }
                )

        options = entry.options
        percent = NumberSelector(
            NumberSelectorConfig(
                min=50, max=99, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="%"
            )
        )
        schema = vol.Schema(
            {
                **_target_field(self.hass, entry.data.get(CONF_ADMIN_NOTIFY_TARGET)),
                vol.Required(
                    CONF_WARNING_THRESHOLD,
                    default=options.get(CONF_WARNING_THRESHOLD, DEFAULT_WARNING_THRESHOLD),
                ): percent,
                vol.Required(
                    CONF_CRITICAL_THRESHOLD,
                    default=options.get(CONF_CRITICAL_THRESHOLD, DEFAULT_CRITICAL_THRESHOLD),
                ): percent,
                vol.Required(
                    CONF_INCLUDE_MOUNTS,
                    default=options.get(CONF_INCLUDE_MOUNTS, DEFAULT_INCLUDE_MOUNTS),
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
