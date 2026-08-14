"""Base entity for the Flappie integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FlappieCoordinator, FlappieDeviceData


class FlappieEntity(CoordinatorEntity[FlappieCoordinator]):
    """Common base: bindet eine Entity an eine Katzenklappe."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: FlappieCoordinator, device_id: str, key: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{key}"

        data = self.device_data
        device = data.device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.get("name") or "Flappie",
            manufacturer="Flappie Technologies AG",
            model=device.get("model"),
            sw_version=device.get("software_version"),
            hw_version=device.get("firmware_version"),
            serial_number=device_id,
        )

    @property
    def device_data(self) -> FlappieDeviceData:
        """Shortcut to this door's coordinator data."""
        return self.coordinator.data.devices[self._device_id]

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._device_id in self.coordinator.data.devices
        )


class FlappieCatEntity(CoordinatorEntity[FlappieCoordinator]):
    """Basis für Entitäten, die zu einem Katzenprofil gehören."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FlappieCoordinator,
        cat_id: int,
        key: str,
        via_device_id: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._cat_id = cat_id
        self._attr_unique_id = f"cat_{cat_id}_{key}"

        cat = self.cat
        info = DeviceInfo(
            identifiers={(DOMAIN, f"cat_{cat_id}")},
            name=cat.get("name") or f"Katze {cat_id}",
            manufacturer="Flappie",
            model=cat.get("breed") or "Cat",
        )
        if via_device_id is not None:
            info["via_device"] = (DOMAIN, via_device_id)
        self._attr_device_info = info

    @property
    def cat(self) -> dict:
        """Shortcut to this cat's profile data."""
        return self.coordinator.data.cats[self._cat_id]

    @property
    def available(self) -> bool:
        return super().available and self._cat_id in self.coordinator.data.cats
