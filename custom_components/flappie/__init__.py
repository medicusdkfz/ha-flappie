"""The Flappie integration (inoffiziell)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FlappieApiClient, FlappieApiError, FlappieAuthError
from .coordinator import FlappieCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.IMAGE,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type FlappieConfigEntry = ConfigEntry[FlappieCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: FlappieConfigEntry) -> bool:
    """Set up Flappie from a config entry."""
    api = FlappieApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
    )
    try:
        await api.async_login()
    except FlappieAuthError as err:
        raise ConfigEntryAuthFailed from err
    except FlappieApiError as err:
        raise ConfigEntryNotReady from err

    coordinator = FlappieCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FlappieConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
