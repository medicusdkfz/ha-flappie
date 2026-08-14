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

from homeassistant.util import dt as dt_util

from . import FlappieConfigEntry
from .const import HEALTH_ICONS, HEALTH_TYPES
from .coordinator import FlappieCoordinator, FlappieDeviceData, add_months
from .entity import FlappieCatEntity, FlappieEntity


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
    entities: list[BinarySensorEntity] = [
        FlappieBinarySensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in BINARY_SENSORS
    ]
    first_device_id = next(iter(coordinator.data.devices), None)
    entities.extend(
        FlappieHealthDueBinarySensor(coordinator, cat_id, first_device_id, health_type)
        for cat_id in coordinator.data.cats
        for health_type in HEALTH_TYPES
    )
    async_add_entities(entities)


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


class FlappieHealthDueBinarySensor(FlappieCatEntity, BinarySensorEntity):
    """An, wenn die naechste Behandlung heute oder frueher faellig ist."""

    def __init__(
        self,
        coordinator,
        cat_id: int,
        via_device_id: str | None,
        health_type: str,
    ) -> None:
        super().__init__(
            coordinator, cat_id, f"health_due_{health_type}", via_device_id
        )
        self._health_type = health_type
        self._attr_translation_key = f"health_due_{health_type}"
        self._attr_icon = HEALTH_ICONS[health_type]

    @property
    def is_on(self) -> bool | None:
        entry = self.coordinator.health_entry(self._cat_id, self._health_type)
        if entry["last"] is None:
            return None
        next_due = add_months(entry["last"], entry["interval"])
        return next_due <= dt_util.now().date()
