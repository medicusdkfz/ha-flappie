"""Event entity: neue Aktivitäts-/Beute-Ereignisse an der Klappe."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FlappieConfigEntry
from .const import EVENT_TYPE_ACTIVITY, EVENT_TYPE_PREY, SIGNAL_NEW_BUNDLE
from .entity import FlappieEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlappieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FlappieBundleEvent(coordinator, device_id, entry.entry_id)
        for device_id in coordinator.data.devices
    )


class FlappieBundleEvent(FlappieEntity, EventEntity):
    """Feuert bei jedem neuen Bundle (Katze gesichtet / Beute erkannt)."""

    _attr_translation_key = "flap_event"
    _attr_event_types = [EVENT_TYPE_ACTIVITY, EVENT_TYPE_PREY]
    _attr_icon = "mdi:cat"

    def __init__(self, coordinator, device_id: str, entry_id: str) -> None:
        super().__init__(coordinator, device_id, "flap_event")
        self._entry_id = entry_id

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_NEW_BUNDLE.format(self._entry_id),
                self._handle_bundle,
            )
        )

    @callback
    def _handle_bundle(self, bundle: dict[str, Any]) -> None:
        if bundle.get("catflap_id") != self._device_id:
            return
        self._trigger_event(
            EVENT_TYPE_PREY if bundle.get("is_prey") else EVENT_TYPE_ACTIVITY,
            {
                "bundle_id": bundle.get("id"),
                "created_at": bundle.get("created_at"),
                "has_video": bundle.get("video_file") is not None,
            },
        )
        self.async_write_ha_state()
