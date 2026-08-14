"""Select entity: Türmodus (OPEN / CLOSED / OPEN_IN / OPEN_OUT)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FlappieConfigEntry
from .const import OPTION_TO_POLICY, POLICY_TO_OPTION
from .entity import FlappieEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlappieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FlappieDoorPolicySelect(coordinator, device_id)
        for device_id in coordinator.data.devices
    )


class FlappieDoorPolicySelect(FlappieEntity, SelectEntity):
    """Steuert open_status inklusive der Einweg-Modi."""

    _attr_translation_key = "door_policy"
    _attr_options = list(OPTION_TO_POLICY)
    _attr_icon = "mdi:door-sliding"

    def __init__(self, coordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "door_policy")

    @property
    def current_option(self) -> str | None:
        return POLICY_TO_OPTION.get(self.device_data.settings.get("open_status"))

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_patch_settings(
            self._device_id, {"open_status": OPTION_TO_POLICY[option]}
        )
