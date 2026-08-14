"""Number entities: Dauer der Beute-Zeitsperre + Behandlungsintervalle."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FlappieConfigEntry
from .const import HEALTH_TYPES
from .entity import FlappieCatEntity, FlappieEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlappieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = [
        FlappiePreyLockDuration(coordinator, device_id)
        for device_id in coordinator.data.devices
    ]
    first_device_id = next(iter(coordinator.data.devices), None)
    entities.extend(
        FlappieHealthInterval(coordinator, cat_id, first_device_id, health_type)
        for cat_id in coordinator.data.cats
        for health_type in HEALTH_TYPES
    )
    async_add_entities(entities)


class FlappieHealthInterval(FlappieCatEntity, RestoreNumber):
    """Behandlungsintervall in Monaten; lokal gepflegt, neustartfest."""

    _attr_native_min_value = 1
    _attr_native_max_value = 36
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:calendar-refresh"

    def __init__(
        self,
        coordinator,
        cat_id: int,
        via_device_id: str | None,
        health_type: str,
    ) -> None:
        super().__init__(
            coordinator, cat_id, f"health_interval_{health_type}", via_device_id
        )
        self._health_type = health_type
        self._attr_translation_key = f"health_interval_{health_type}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        data = await self.async_get_last_number_data()
        if data is None or data.native_value is None:
            return
        entry = self.coordinator.health_entry(self._cat_id, self._health_type)
        entry["interval"] = int(data.native_value)
        self.coordinator.async_update_listeners()

    @property
    def native_value(self) -> int:
        return self.coordinator.health_entry(self._cat_id, self._health_type)[
            "interval"
        ]

    async def async_set_native_value(self, value: float) -> None:
        entry = self.coordinator.health_entry(self._cat_id, self._health_type)
        entry["interval"] = int(value)
        self.coordinator.async_update_listeners()


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
