"""Switch entities: Beuteerkennung, Tasten, RFID, Beute-Zeitsperre."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FlappieConfigEntry
from .entity import FlappieEntity


@dataclass(frozen=True, kw_only=True)
class FlappieSwitchDescription(SwitchEntityDescription):
    """Beschreibt einen Settings-Bool-Schalter."""

    settings_field: str


SWITCHES: tuple[FlappieSwitchDescription, ...] = (
    FlappieSwitchDescription(
        key="prey_detection",
        translation_key="prey_detection",
        settings_field="prey_detection_user_preference",
        icon="mdi:paw",
    ),
    FlappieSwitchDescription(
        key="prey_timed_lock",
        translation_key="prey_timed_lock",
        settings_field="prey_timed_lock_enabled",
        icon="mdi:timer-lock",
        entity_category=EntityCategory.CONFIG,
    ),
    FlappieSwitchDescription(
        key="buttons",
        translation_key="buttons",
        settings_field="buttons_enabled",
        icon="mdi:gesture-tap-button",
        entity_category=EntityCategory.CONFIG,
    ),
    FlappieSwitchDescription(
        # Laut Hersteller liest die Flappie keine Chips; das Backend-Feld
        # existiert trotzdem. Standardmäßig ausgeblendet, Wirkung unbekannt.
        key="rfid",
        translation_key="rfid",
        settings_field="rfid",
        icon="mdi:nfc-variant",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlappieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FlappieSwitch(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in SWITCHES
    )


class FlappieSwitch(FlappieEntity, SwitchEntity):
    """Ein Bool-Feld aus den Geräte-Settings."""

    entity_description: FlappieSwitchDescription

    def __init__(
        self, coordinator, device_id: str, description: FlappieSwitchDescription
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = self.device_data.settings.get(self.entity_description.settings_field)
        return value if isinstance(value, bool) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)

    async def _async_set(self, value: bool) -> None:
        await self.coordinator.async_patch_settings(
            self._device_id, {self.entity_description.settings_field: value}
        )
