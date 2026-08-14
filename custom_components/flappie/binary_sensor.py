"""Binary sensors for the Flappie integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FlappieConfigEntry
from .coordinator import FlappieCoordinator, FlappieDeviceData
from .entity import FlappieEntity


@dataclass(frozen=True, kw_only=True)
class FlappieBinarySensorDescription(BinarySensorEntityDescription):
    """Binary sensor mit Wert-Funktion."""

    value_fn: Callable[[FlappieCoordinator, FlappieDeviceData], bool | None]


BINARY_SENSORS: tuple[FlappieBinarySensorDescription, ...] = (
    FlappieBinarySensorDescription(
        key="prey_system_lock",
        translation_key="prey_system_lock",
        icon="mdi:paw-off",
        value_fn=lambda _, data: data.settings.get("prey_detection_system_lock"),
    ),
    FlappieBinarySensorDescription(
        key="problem",
        translation_key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda _, data: (
            None
            if data.operational.get("status") is None
            else data.operational.get("status") != 1
        ),
    ),
    FlappieBinarySensorDescription(
        key="timeplan_active",
        translation_key="timeplan_active",
        icon="mdi:calendar-clock",
        value_fn=lambda coordinator, _: coordinator.data.dashboard.get(
            "is_timeplan_active"
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlappieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FlappieBinarySensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in BINARY_SENSORS
    )


class FlappieBinarySensor(FlappieEntity, BinarySensorEntity):
    """Generischer Flappie-Binary-Sensor."""

    entity_description: FlappieBinarySensorDescription

    def __init__(
        self,
        coordinator,
        device_id: str,
        description: FlappieBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = self.entity_description.value_fn(self.coordinator, self.device_data)
        return value if isinstance(value, bool) else None
