"""Switch entities: Beuteerkennung, Tasten, RFID, Beute-Zeitsperre."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

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
    entities: list[SwitchEntity] = [
        FlappieSwitch(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in SWITCHES
    ]
    first_device_id = next(iter(coordinator.data.devices), None)
    if first_device_id is not None:
        entities.extend(
            FlappieHealthOptionSwitch(coordinator, first_device_id, option, icon)
            for option, icon in (
                ("sync_cats", "mdi:link-variant"),
                ("combo", "mdi:pill-multiple"),
            )
        )
    async_add_entities(entities)


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


class FlappieHealthOptionSwitch(FlappieEntity, SwitchEntity, RestoreEntity):
    """Koppel-Optionen des Gesundheits-Trackings (lokal, neustartfest).

    sync_cats: Eingaben gelten fuer alle Katzen gemeinsam.
    combo: Wurmkur und Flohbehandlung werden gemeinsam gepflegt
    (Kombipraeparat).
    """

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator, device_id: str, option: str, icon: str
    ) -> None:
        super().__init__(coordinator, device_id, f"health_{option}")
        self._option = option
        self._attr_translation_key = f"health_{option}"
        self._attr_icon = icon

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in ("on", "off"):
            self.coordinator.health_options[self._option] = last_state.state == "on"
            self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self.coordinator.health_options.get(self._option, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.health_options[self._option] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.health_options[self._option] = False
        self.async_write_ha_state()
