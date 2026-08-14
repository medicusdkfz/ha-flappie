"""Sensor entities for the Flappie integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfMass, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import FlappieConfigEntry
from .const import HEALTH_ICONS, HEALTH_TYPES
from .coordinator import FlappieDeviceData, add_months, parse_flappie_datetime
from .entity import FlappieCatEntity, FlappieEntity


@dataclass(frozen=True, kw_only=True)
class FlappieSensorDescription(SensorEntityDescription):
    """Sensor mit Wert-Funktion über die Gerätedaten."""

    value_fn: Callable[[FlappieDeviceData], Any]
    attributes_fn: Callable[[FlappieDeviceData], dict[str, Any]] | None = None


def _last_event(data: FlappieDeviceData) -> datetime | None:
    if data.last_bundle is None:
        return None
    return parse_flappie_datetime(data.last_bundle.get("created_at"))


SENSORS: tuple[FlappieSensorDescription, ...] = (
    FlappieSensorDescription(
        key="door_state",
        translation_key="door_state",
        device_class=SensorDeviceClass.ENUM,
        options=["locked", "unlocked"],
        icon="mdi:door",
        value_fn=lambda data: data.status.get("state"),
        attributes_fn=lambda data: {
            "reason": data.status.get("reason"),
            "lock_started_at": data.status.get("lock_started_at"),
            "lock_until": data.status.get("lock_until"),
        },
    ),
    FlappieSensorDescription(
        key="last_event",
        translation_key="last_event",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:cat",
        value_fn=_last_event,
        attributes_fn=lambda data: {
            "bundle_id": (data.last_bundle or {}).get("id"),
            "is_prey": (data.last_bundle or {}).get("is_prey"),
        },
    ),
    FlappieSensorDescription(
        key="signal_quality",
        translation_key="signal_quality",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:wifi",
        value_fn=lambda data: data.operational.get("signal_quality"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlappieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        FlappieSensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in SENSORS
    ]
    entities.extend(
        FlappieBlockedPreySensor(coordinator, device_id)
        for device_id in coordinator.data.devices
    )
    entities.extend(
        FlappieLastPreySensor(coordinator, device_id)
        for device_id in coordinator.data.devices
    )
    entities.extend(
        FlappieTodaySensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in TODAY_SENSORS
    )
    first_device_id = next(iter(coordinator.data.devices), None)
    entities.extend(
        FlappieCatWeightSensor(coordinator, cat_id, first_device_id)
        for cat_id in coordinator.data.cats
    )
    entities.extend(
        FlappieCatProfileSensor(coordinator, cat_id, first_device_id, description)
        for cat_id in coordinator.data.cats
        for description in CAT_PROFILE_SENSORS
    )
    entities.extend(
        FlappieHealthNextSensor(coordinator, cat_id, first_device_id, health_type)
        for cat_id in coordinator.data.cats
        for health_type in HEALTH_TYPES
    )
    entities.extend(
        FlappieHealthDaysSensor(coordinator, cat_id, first_device_id, health_type)
        for cat_id in coordinator.data.cats
        for health_type in HEALTH_TYPES
    )
    async_add_entities(entities)


class FlappieSensor(FlappieEntity, SensorEntity):
    """Generischer Flappie-Sensor."""

    entity_description: FlappieSensorDescription

    def __init__(
        self, coordinator, device_id: str, description: FlappieSensorDescription
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.device_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.device_data)


class FlappieBlockedPreySensor(FlappieEntity, SensorEntity):
    """blocked_prey aus dem Dashboard (kontoweit)."""

    _attr_translation_key = "blocked_prey"
    _attr_icon = "mdi:shield-check"

    def __init__(self, coordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "blocked_prey")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.dashboard.get("blocked_prey")


class FlappieLastPreySensor(FlappieEntity, SensorEntity):
    """Letzter Beutefund laut Dashboard.

    Die Bundle-Liste verfaellt nach 7 Tagen; dashboard.latest_prey_detection
    liefert dagegen dauerhaft den letzten Beutefund (wie die App).
    """

    _attr_translation_key = "last_prey_event"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:paw"

    def __init__(self, coordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "last_prey_event")

    @property
    def native_value(self) -> datetime | None:
        return parse_flappie_datetime(
            self.coordinator.data.dashboard.get("latest_prey_detection")
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "bundle_id": (self.device_data.last_prey_bundle or {}).get("id"),
        }


@dataclass(frozen=True, kw_only=True)
class FlappieTodaySensorDescription(SensorEntityDescription):
    """Tageszaehler aus den kontoweiten Coordinator-Daten."""

    data_field: str


TODAY_SENSORS: tuple[FlappieTodaySensorDescription, ...] = (
    FlappieTodaySensorDescription(
        key="activity_today",
        translation_key="activity_today",
        data_field="activity_today",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:swap-horizontal",
    ),
    FlappieTodaySensorDescription(
        key="prey_today",
        translation_key="prey_today",
        data_field="prey_today",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:paw",
    ),
)


class FlappieTodaySensor(FlappieEntity, SensorEntity):
    """Heutige Ereignis-/Beutezahl (kontoweit, Reset um Mitternacht)."""

    entity_description: FlappieTodaySensorDescription

    def __init__(
        self,
        coordinator,
        device_id: str,
        description: FlappieTodaySensorDescription,
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> int | None:
        return getattr(self.coordinator.data, self.entity_description.data_field)


def _parse_cat_birthday(cat: dict[str, Any]) -> date | None:
    value = cat.get("birthday")
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _cat_age_years(cat: dict[str, Any]) -> int | None:
    birthday = _parse_cat_birthday(cat)
    if birthday is None:
        return None
    today = dt_util.now().date()
    return (
        today.year
        - birthday.year
        - ((today.month, today.day) < (birthday.month, birthday.day))
    )


@dataclass(frozen=True, kw_only=True)
class FlappieCatSensorDescription(SensorEntityDescription):
    """Sensor aus dem Katzenprofil."""

    value_fn: Callable[[dict[str, Any]], Any]


CAT_PROFILE_SENSORS: tuple[FlappieCatSensorDescription, ...] = (
    FlappieCatSensorDescription(
        key="cat_birthday",
        translation_key="cat_birthday",
        device_class=SensorDeviceClass.DATE,
        value_fn=_parse_cat_birthday,
    ),
    FlappieCatSensorDescription(
        key="cat_age",
        translation_key="cat_age",
        icon="mdi:cake-variant",
        value_fn=_cat_age_years,
    ),
    FlappieCatSensorDescription(
        key="cat_breed",
        translation_key="cat_breed",
        icon="mdi:cat",
        value_fn=lambda cat: cat.get("breed"),
    ),
    FlappieCatSensorDescription(
        key="cat_gender",
        translation_key="cat_gender",
        device_class=SensorDeviceClass.ENUM,
        options=["female", "male", "unknown"],
        icon="mdi:gender-male-female",
        value_fn=lambda cat: (cat.get("gender") or "").lower() or None,
    ),
)


class FlappieCatProfileSensor(FlappieCatEntity, SensorEntity):
    """Stammdaten aus dem Katzenprofil (in der App gepflegt)."""

    entity_description: FlappieCatSensorDescription

    def __init__(
        self,
        coordinator,
        cat_id: int,
        via_device_id: str | None,
        description: FlappieCatSensorDescription,
    ) -> None:
        super().__init__(coordinator, cat_id, description.key, via_device_id)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.cat)


class FlappieHealthNextSensor(FlappieCatEntity, SensorEntity):
    """Naechster Behandlungstermin = letzte Behandlung + Intervall."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self,
        coordinator,
        cat_id: int,
        via_device_id: str | None,
        health_type: str,
    ) -> None:
        super().__init__(
            coordinator, cat_id, f"health_next_{health_type}", via_device_id
        )
        self._health_type = health_type
        self._attr_translation_key = f"health_next_{health_type}"
        self._attr_icon = HEALTH_ICONS[health_type]

    @property
    def native_value(self) -> date | None:
        entry = self.coordinator.health_entry(self._cat_id, self._health_type)
        if entry["last"] is None:
            return None
        return add_months(entry["last"], entry["interval"])


class FlappieHealthDaysSensor(FlappieCatEntity, SensorEntity):
    """Tage bis zur naechsten Behandlung (negativ = ueberfaellig).

    Praktisch fuer Dashboards: numerische Sichtbarkeits-/Farbbedingungen
    (z. B. rot < 0, orange 0-14, gruen > 14) brauchen einen Zahlenwert.
    """

    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    def __init__(
        self,
        coordinator,
        cat_id: int,
        via_device_id: str | None,
        health_type: str,
    ) -> None:
        super().__init__(
            coordinator, cat_id, f"health_days_{health_type}", via_device_id
        )
        self._health_type = health_type
        self._attr_translation_key = f"health_days_{health_type}"
        self._attr_icon = HEALTH_ICONS[health_type]

    @property
    def native_value(self) -> int | None:
        entry = self.coordinator.health_entry(self._cat_id, self._health_type)
        if entry["last"] is None:
            return None
        next_due = add_months(entry["last"], entry["interval"])
        return (next_due - dt_util.now().date()).days


class FlappieCatWeightSensor(FlappieCatEntity, SensorEntity):
    """Gewicht aus dem Katzenprofil; Stammdaten als Attribute."""

    _attr_translation_key = "cat_weight"
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(
        self, coordinator, cat_id: int, via_device_id: str | None
    ) -> None:
        super().__init__(coordinator, cat_id, "weight", via_device_id)

    @property
    def native_value(self) -> float | None:
        return self.cat.get("weight")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "birthday": self.cat.get("birthday"),
            "gender": self.cat.get("gender"),
            "breed": self.cat.get("breed"),
        }
