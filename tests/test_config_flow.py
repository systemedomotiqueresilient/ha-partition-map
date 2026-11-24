"""Config flow et options flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.partition_map.const import DOMAIN

from .conftest import add_sibling_target, make_entry


@pytest.fixture(autouse=True)
def hassio_and_no_setup(ha_deps):
    with (
        patch("custom_components.partition_map.config_flow.is_hassio", return_value=True),
        patch("custom_components.partition_map.async_setup_entry", return_value=True),
    ):
        yield


def _suggested(result, key: str):
    for field in result["data_schema"].schema:
        if field == key:
            return (field.description or {}).get("suggested_value")
    raise KeyError(key)


def _options(result, key: str) -> list[str]:
    for field, selector in result["data_schema"].schema.items():
        if field == key:
            return [o if isinstance(o, str) else o["value"] for o in selector.config["options"]]
    raise KeyError(key)


async def test_not_supervised(hass: HomeAssistant) -> None:
    with patch("custom_components.partition_map.config_flow.is_hassio", return_value=False):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supervised"


async def test_prefill_from_sibling(hass: HomeAssistant) -> None:
    add_sibling_target(hass, "deferred_restart", "notify.mobile_app_pixel_9")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert _suggested(result, "admin_notify_target") == "notify.mobile_app_pixel_9"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"admin_notify_target": "notify.mobile_app_pixel_9"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"admin_notify_target": "notify.mobile_app_pixel_9"}
    assert result["result"].minor_version == 2


async def test_several_values_listed(hass: HomeAssistant) -> None:
    add_sibling_target(hass, "sentinel_report", "notify.mobile_app_a", "a")
    add_sibling_target(hass, "entity_inventory", "notify.mobile_app_b", "b")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert _suggested(result, "admin_notify_target") is None
    assert _options(result, "admin_notify_target") == [
        "notify.mobile_app_a",
        "notify.mobile_app_b",
    ]


async def test_empty_and_invalid_target(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"admin_notify_target": "mobile_app_pixel"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"admin_notify_target": "invalid_target"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"admin_notify_target": None}


async def test_options_flow(hass: HomeAssistant) -> None:
    entry = make_entry(data={"admin_notify_target": "notify.mobile_app_old"})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert _suggested(result, "admin_notify_target") == "notify.mobile_app_old"

    bad = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "admin_notify_target": "notify.mobile_app_new",
            "warning_threshold": 90,
            "critical_threshold": 90,
            "include_mounts": True,
        },
    )
    assert bad["errors"] == {"critical_threshold": "critical_below_warning"}

    result = await hass.config_entries.options.async_configure(
        bad["flow_id"],
        {
            "admin_notify_target": "notify.mobile_app_new",
            "warning_threshold": 80,
            "critical_threshold": 92,
            "include_mounts": False,
            "detail_level": "simple",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data["admin_notify_target"] == "notify.mobile_app_new"
    assert entry.options == {
        "warning_threshold": 80,
        "critical_threshold": 92,
        "include_mounts": False,
        "detail_level": "simple",
    }
