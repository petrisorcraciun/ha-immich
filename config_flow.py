import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, CONF_API_KEY, CONF_API_URL, STATISTICS_ENDPOINT
import aiohttp
from typing import Any, Dict, Optional, Tuple

def ensure_api_url(api_url: str) -> str:
    api_url = api_url.rstrip('/')
    if not api_url.endswith('/api'):
        api_url = f"{api_url}/api"
    return api_url

async def validate_immich(api_url: str, api_key: str) -> Tuple[bool, Optional[str]]:
    try:
        api_url = ensure_api_url(api_url)
        async with aiohttp.ClientSession() as session:
            headers = {
                "x-api-key": api_key,
                "Accept": "application/json"
            }
            async with session.get(f"{api_url}/{STATISTICS_ENDPOINT}", headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    return True, None
                return False, f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)

class ImmichConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> Any:
        errors = {}
        if user_input is not None:
            # Prevent duplicate server
            for entry in self._async_current_entries():
                if entry.data.get(CONF_API_URL, '').strip().lower() == user_input[CONF_API_URL].strip().lower():
                    errors["base"] = "already_configured"
                    break
            else:
                valid, err = await validate_immich(user_input[CONF_API_URL], user_input[CONF_API_KEY])
                if valid:
                    return self.async_create_entry(title=user_input[CONF_API_URL], data=user_input)
                errors["base"] = f"cannot_connect: {err}"

        data_schema = vol.Schema({
            vol.Required(CONF_API_URL): str,
            vol.Required(CONF_API_KEY): str,
            vol.Optional("scan_interval", default=5): int,
        })
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> Any:
        return ImmichOptionsFlowHandler(config_entry)

class ImmichOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__(config_entry)

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> Any:
        errors = {}
        if user_input is not None:
            valid, err = await validate_immich(user_input[CONF_API_URL], user_input[CONF_API_KEY])
            if valid:
                return self.async_create_entry(title="", data=user_input)
            errors["base"] = f"cannot_connect: {err}"

        data_schema = vol.Schema({
            vol.Required(CONF_API_URL, default=self.config_entry.data.get(CONF_API_URL, "")): str,
            vol.Required(CONF_API_KEY, default=self.config_entry.data.get(CONF_API_KEY, "")): str,
            vol.Optional("scan_interval", default=self.config_entry.data.get("scan_interval", 5)): int,
        })
        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
