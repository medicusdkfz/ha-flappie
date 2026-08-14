"""Date entities: letzte Behandlung je Katze (lokal gepflegt).

Diese Werte kennt die Flappie-Cloud nicht; sie leben in Home Assistant
und ueberleben Neustarts via RestoreEntity.
"""

from __future__ import annotations

from datetime import date

from homeassistant.components.date import DateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import FlappieConfigEntry
from .const import EVENT_HEALTH_UPDATED, HEALTH_ICONS, HEALTH_TYPES
from .coordinator import add_months
from .entity import FlappieCatEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlappieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    first_device_id = next(iter(coordinator.data.devices), None)
    async_add_entities(
        FlappieHealthLastDate(coordinator, cat_id, first_device_id, health_type)
        for cat_id in coordinator.data.cats
        for health_type in HEALTH_TYPES
    )


class FlappieHealthLastDate(FlappieCatEntity, DateEntity, RestoreEntity):
    """Datum der letzten Behandlung; vom Nutzer gesetzt."""

    def __init__(
        self,
        coordinator,
        cat_id: int,
        via_device_id: str | None,
        health_type: str,
    ) -> None:
        super().__init__(
            coordinator, cat_id, f"health_last_{health_type}", via_device_id
        )
        self._health_type = health_type
        self._attr_translation_key = f"health_last_{health_type}"
        self._attr_icon = HEALTH_ICONS[health_type]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in ("unknown", "unavailable"):
            return
        try:
            value = date.fromisoformat(last_state.state)
        except ValueError:
            return
        self.coordinator.health_entry(self._cat_id, self._health_type)["last"] = value
        self.coordinator.async_update_listeners()

    @property
    def native_value(self) -> date | None:
        return self.coordinator.health_entry(self._cat_id, self._health_type)["last"]

    async def async_set_value(self, value: date) -> None:
        entry = self.coordinator.health_entry(self._cat_id, self._health_type)
        entry["last"] = value
        self.coordinator.async_update_listeners()
        # Nur bei echten Benutzeraktionen (nicht beim Restore/Neustart), damit
        # z. B. Kalender-Automatisierungen keine Duplikate erzeugen.
        self.hass.bus.async_fire(
            EVENT_HEALTH_UPDATED,
            {
                "cat_id": self._cat_id,
                "cat_name": self.cat.get("name"),
                "health_type": self._health_type,
                "last": value.isoformat(),
                "interval_months": entry["interval"],
                "next_due": add_months(value, entry["interval"]).isoformat(),
            },
        )
