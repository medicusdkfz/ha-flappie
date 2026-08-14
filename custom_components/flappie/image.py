"""Image entity: Foto des letzten Ereignisses an der Klappe."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import FlappieConfigEntry
from .api import FlappieApiError
from .coordinator import parse_flappie_datetime
from .entity import FlappieCatEntity, FlappieEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlappieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[ImageEntity] = [
        FlappieLastEventImage(hass, coordinator, device_id)
        for device_id in coordinator.data.devices
    ]
    entities.extend(
        FlappieRecentEventImage(hass, coordinator, device_id, index)
        for device_id in coordinator.data.devices
        for index in range(4)
    )
    first_device_id = next(iter(coordinator.data.devices), None)
    entities.extend(
        FlappieCatAvatar(hass, coordinator, cat_id, first_device_id)
        for cat_id, cat in coordinator.data.cats.items()
        if cat.get("avatar_url")
    )
    async_add_entities(entities)


class FlappieLastEventImage(FlappieEntity, ImageEntity):
    """Holt beim Abruf frische signierte Medien-URLs (die alten laufen ab)."""

    _attr_translation_key = "last_event_image"

    def __init__(self, hass: HomeAssistant, coordinator, device_id: str) -> None:
        FlappieEntity.__init__(self, coordinator, device_id, "last_event_image")
        ImageEntity.__init__(self, hass)

    @property
    def image_last_updated(self) -> datetime | None:
        bundle = self.device_data.last_bundle
        if bundle is None:
            return None
        return parse_flappie_datetime(bundle.get("created_at"))

    @callback
    def _handle_coordinator_update(self) -> None:
        # Neues Bundle => Frontend soll das Bild neu laden.
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        bundle = self.device_data.last_bundle
        if bundle is None:
            return None
        try:
            fresh = await self.coordinator.api.async_get_bundle(bundle["id"])
        except FlappieApiError as err:
            _LOGGER.warning("Konnte Bundle %s nicht laden: %s", bundle["id"], err)
            return None

        url = fresh.get("image")
        if not url:
            files = fresh.get("image_files") or []
            url = files[0]["url"] if files else None
        if not url:
            return None

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url) as resp:
                if resp.status >= 400:
                    _LOGGER.warning(
                        "Bildabruf fehlgeschlagen (HTTP %s)", resp.status
                    )
                    return None
                # Das CDN liefert "binary/octet-stream"; Typ aus der URL ableiten.
                ctype = resp.content_type or ""
                if not ctype.startswith("image/"):
                    path = url.split("?", 1)[0].lower()
                    ctype = "image/png" if path.endswith(".png") else "image/jpeg"
                self._attr_content_type = ctype
                return await resp.read()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Bildabruf fehlgeschlagen: %s", err)
            return None


class FlappieRecentEventImage(FlappieEntity, ImageEntity):
    """Bild des n-neuesten Ereignisses mit Video (fuer Dashboard-Karten)."""

    def __init__(
        self, hass: HomeAssistant, coordinator, device_id: str, index: int
    ) -> None:
        FlappieEntity.__init__(self, coordinator, device_id, f"event_image_{index + 1}")
        ImageEntity.__init__(self, hass)
        self._index = index
        self._attr_translation_key = f"event_image_{index + 1}"

    def _bundle(self) -> dict | None:
        videos = [
            b for b in self.device_data.recent_bundles if b.get("video_file")
        ]
        return videos[self._index] if self._index < len(videos) else None

    @property
    def available(self) -> bool:
        return super().available and self._bundle() is not None

    @property
    def image_last_updated(self) -> datetime | None:
        bundle = self._bundle()
        if bundle is None:
            return None
        return parse_flappie_datetime(bundle.get("created_at"))

    @property
    def extra_state_attributes(self) -> dict:
        bundle = self._bundle() or {}
        return {
            "bundle_id": bundle.get("id"),
            "created_at": bundle.get("created_at"),
            "is_prey": bundle.get("is_prey"),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        bundle = self._bundle()
        if bundle is None:
            return None
        try:
            fresh = await self.coordinator.api.async_get_bundle(bundle["id"])
        except FlappieApiError as err:
            _LOGGER.warning("Konnte Bundle %s nicht laden: %s", bundle["id"], err)
            return None
        url = fresh.get("image")
        if not url:
            files = fresh.get("image_files") or []
            url = files[0]["url"] if files else None
        if not url:
            return None
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url) as resp:
                if resp.status >= 400:
                    return None
                ctype = resp.content_type or ""
                if not ctype.startswith("image/"):
                    path = url.split("?", 1)[0].lower()
                    ctype = "image/png" if path.endswith(".png") else "image/jpeg"
                self._attr_content_type = ctype
                return await resp.read()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Bildabruf fehlgeschlagen: %s", err)
            return None


class FlappieCatAvatar(FlappieCatEntity, ImageEntity):
    """Profilbild einer Katze."""

    _attr_translation_key = "cat_avatar"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        cat_id: int,
        via_device_id: str | None,
    ) -> None:
        FlappieCatEntity.__init__(self, coordinator, cat_id, "avatar", via_device_id)
        ImageEntity.__init__(self, hass)
        self._last_url: str | None = self.cat.get("avatar_url")
        self._attr_image_last_updated = dt_util.utcnow()

    @callback
    def _handle_coordinator_update(self) -> None:
        if self._cat_id in self.coordinator.data.cats:
            url = self.cat.get("avatar_url")
            if url != self._last_url:
                # Neues Profilbild => Frontend zum Neuladen bewegen.
                self._last_url = url
                self._attr_image_last_updated = dt_util.utcnow()
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        try:
            cats = await self.coordinator.api.async_list_cats()
        except FlappieApiError as err:
            _LOGGER.warning("Konnte Katzenprofile nicht laden: %s", err)
            return None
        cat = next((c for c in cats if c.get("id") == self._cat_id), None)
        url = (cat or {}).get("avatar_url")
        if not url:
            return None

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url) as resp:
                if resp.status >= 400:
                    _LOGGER.warning(
                        "Avatar-Abruf fehlgeschlagen (HTTP %s)", resp.status
                    )
                    return None
                ctype = resp.content_type or ""
                if not ctype.startswith("image/"):
                    path = url.split("?", 1)[0].lower()
                    ctype = "image/png" if path.endswith(".png") else "image/jpeg"
                self._attr_content_type = ctype
                return await resp.read()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Avatar-Abruf fehlgeschlagen: %s", err)
            return None
