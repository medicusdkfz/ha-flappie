"""Number entity: Dauer der Beute-Zeitsperre."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FlappieConfigEntry
from .entity import FlappieEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlappieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FlappiePreyLockDuration(coordinator, device_id)
        for device_id in coordinator.data.devices
    )


class FlappiePreyLockDuration(FlappieEntity, NumberEntity):
    """prey_timed_lock_duration_seconds (Standard der App: 900 s)."""

    _attr_translation_key = "prey_lock_duration"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_native_min_value = 60
    _attr_native_max_value = 86400
    _attr_native_step = 60
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-lock-outline"

    def __init__(self, coordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "prey_lock_duration")

    @property
    def native_value(self) -> int | None:
        return self.device_data.settings.get("prey_timed_lock_duration_seconds")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_patch_settings(
            self._device_id, {"prey_timed_lock_duration_seconds": int(value)}
        )
