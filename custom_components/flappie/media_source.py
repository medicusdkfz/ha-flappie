"""Media source: Ereignis-Videos der Flappie im HA-Medienbrowser.

Die signierten Video-URLs der Cloud laufen nach kurzer Zeit ab; beim
Abspielen wird deshalb pro Bundle eine frische URL geholt.
"""

from __future__ import annotations

from homeassistant.components.media_player import MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .api import FlappieApiError
from .const import DOMAIN
from .coordinator import parse_flappie_datetime


async def async_get_media_source(hass: HomeAssistant) -> FlappieMediaSource:
    """Set up the Flappie media source."""
    return FlappieMediaSource(hass)


class FlappieMediaSource(MediaSource):
    """Ereignis-Videos, gruppiert unter Medien -> Flappie."""

    name = "Flappie"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    def _loaded_entries(self):
        return [
            entry
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        entry_id, _, bundle_id = (item.identifier or "").partition("/")
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.state is not ConfigEntryState.LOADED:
            raise Unresolvable("Flappie-Integration nicht geladen")
        try:
            fresh = await entry.runtime_data.api.async_get_bundle(int(bundle_id))
        except (FlappieApiError, ValueError) as err:
            raise Unresolvable(f"Video nicht abrufbar: {err}") from err
        url = (fresh.get("video_file") or {}).get("url")
        if not url:
            raise Unresolvable("Dieses Ereignis hat kein Video")
        return PlayMedia(url, "video/mp4")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        children: list[BrowseMediaSource] = []
        for entry in self._loaded_entries():
            coordinator = entry.runtime_data
            for data in coordinator.data.devices.values():
                device_name = data.device.get("name") or "Flappie"
                for bundle in data.recent_bundles:
                    if not bundle.get("video_file"):
                        continue
                    created = parse_flappie_datetime(bundle.get("created_at"))
                    when = (
                        dt_util.as_local(created).strftime("%d.%m. %H:%M")
                        if created
                        else str(bundle.get("id"))
                    )
                    prefix = "🐭 Beute " if bundle.get("is_prey") else "🐾 "
                    children.append(
                        BrowseMediaSource(
                            domain=DOMAIN,
                            identifier=f"{entry.entry_id}/{bundle['id']}",
                            media_class=MediaClass.VIDEO,
                            media_content_type="video/mp4",
                            title=f"{prefix}{when} – {device_name}",
                            can_play=True,
                            can_expand=False,
                            thumbnail=bundle.get("image"),
                        )
                    )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier="",
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title="Flappie",
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.VIDEO,
            children=children,
        )
