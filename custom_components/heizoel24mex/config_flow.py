"""Config flow for Heizoel24 MEX Sensor integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, LOGIN_URL, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)

TITLE = "Heizöl24 Mex Sensor"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)
STEP_REAUTH_DATA_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    auth = {"Login": {"UserName": data[CONF_USERNAME], "Password": data[CONF_PASSWORD]}}
    try:
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as session,
            session.post(LOGIN_URL, json=auth) as result,
        ):
            status = await result.json()
    except Exception as e:
        _LOGGER.warning("Login check failed: %s %s", e.__class__, e)
        raise CannotConnect from e

    if not status["Success"]:
        raise InvalidAuth


class Heizoel24MexConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Heizoel24 MEX sensor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await self._async_check_login(user_input)
            if not errors:
                return self.async_create_entry(title=TITLE, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a login rejected by the web API, e.g. after a password change."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new password of the configured account."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await self._async_check_login({**entry.data, **user_input})
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )

    async def _async_check_login(self, data: dict[str, Any]) -> dict[str, str]:
        """Try to log in and return the form errors, if any."""
        try:
            await validate_input(self.hass, data)
        except CannotConnect:
            return {"base": "cannot_connect"}
        except InvalidAuth:
            return {"base": "invalid_auth"}
        except Exception:
            _LOGGER.exception("Unexpected exception")
            return {"base": "unknown"}
        return {}


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
