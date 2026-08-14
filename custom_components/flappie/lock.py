"""Lock entity: die Katzenklappe selbst."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FlappieConfigEntry
from .const import POLICY_CLOSED, POLICY_OPEN, POLICY_TO_OPTION
from .entity import FlappieEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlappieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FlappieLock(coordinator, device_id) for device_id in coordinator.data.devices
    )


class FlappieLock(FlappieEntity, LockEntity):
    """CLOSED = verriegelt, alles andere = entriegelt (ggf. nur einseitig)."""

    _attr_translation_key = "door"
    _attr_name = None  # Entity trägt den Gerätenamen

    def __init__(self, coordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "lock")

    @property
    def is_locked(self) -> bool:
        return self.device_data.settings.get("open_status") == POLICY_CLOSED

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        settings = self.device_data.settings
        status = self.device_data.status
        return {
            "door_policy": POLICY_TO_OPTION.get(
                settings.get("open_status"), settings.get("open_status")
            ),
            "device_state": status.get("state"),
            "lock_reason": status.get("reason"),
            "lock_until": status.get("lock_until"),
        }

    async def async_lock(self, **kwargs: Any) -> None:
        await self.coordinator.async_patch_settings(
            self._device_id, {"open_status": POLICY_CLOSED}
        )

    async def async_unlock(self, **kwargs: Any) -> None:
        await self.coordinator.async_patch_settings(
            self._device_id, {"open_status": POLICY_OPEN}
        )
