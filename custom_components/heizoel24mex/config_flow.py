"""Config flow for Heizoel24 MEX Sensor integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, LOGIN_URL

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    # if not await hub.authenticate(data[CONF_USERNAME], data[CONF_PASSWORD]):
    #    raise InvalidAuth
    data = {"Login": {"UserName": data[CONF_USERNAME], "Password": data[CONF_PASSWORD]}}
    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth
    try:
        async with (
            aiohttp.ClientSession() as session,
            session.post(LOGIN_URL, json=data) as result,
        ):
            status = await result.json()
    except Exception as e:
        msg = f"Exception within mex24heizoel::validate_input {e.__class__} {e}"
        _LOGGER.warning(msg)
        raise CannotConnect from e

    if not status["Success"]:
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": "Heizöl24 Mex Sensor"}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mex 24 Heizöl Sensor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
