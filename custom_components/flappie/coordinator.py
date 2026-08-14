"""Data update coordinator for the Flappie integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

try:  # mean_type ersetzt has_mean in neueren HA-Versionen
    from homeassistant.components.recorder.models import StatisticMeanType
except ImportError:  # pragma: no cover
    StatisticMeanType = None

from .api import FlappieApiClient, FlappieApiError, FlappieAuthError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SIGNAL_NEW_BUNDLE

_LOGGER = logging.getLogger(__name__)


def parse_flappie_datetime(value: str | None) -> datetime | None:
    """Parse a timestamp from the Flappie API.

    Die Cloud liefert naive Zeitstempel in der Geraete-Zeitzone (zone_info),
    nicht in UTC — verifiziert 08/2026 durch Live-Vergleich eines realen
    Durchgangs (Ereignis 13:33 Lokalzeit == created_at "13:33:57"). Die
    HA-Zeitzone entspricht in der Praxis der zone_info der Klappe.
    """
    if not value:
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return parsed


@dataclass
class FlappieDeviceData:
    """Everything we know about one cat door."""

    device: dict[str, Any]
    settings: dict[str, Any]
    status: dict[str, Any]
    information: dict[str, Any] = field(default_factory=dict)
    operational: dict[str, Any] = field(default_factory=dict)
    last_bundle: dict[str, Any] | None = None
    last_prey_bundle: dict[str, Any] | None = None
    recent_bundles: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FlappieData:
    """Coordinator payload."""

    devices: dict[str, FlappieDeviceData]
    dashboard: dict[str, Any]
    cats: dict[int, dict[str, Any]] = field(default_factory=dict)
    activity_today: int | None = None
    prey_today: int | None = None


class FlappieCoordinator(DataUpdateCoordinator[FlappieData]):
    """Polls the Flappie cloud and fans data out to the entities."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: FlappieApiClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self._information: dict[str, dict[str, Any]] = {}
        self._known_bundle_ids: set[int] | None = None
        self._stats_last_sync: datetime | None = None

    async def _async_update_data(self) -> FlappieData:
        try:
            return await self._fetch()
        except FlappieAuthError as err:
            raise ConfigEntryAuthFailed from err
        except FlappieApiError as err:
            raise UpdateFailed(str(err)) from err

    async def _fetch(self) -> FlappieData:
        # Achtung: das Backend ignoriert die fromCreatedAt/toCreatedAt-Filter
        # (Stand 08/2026); Tageszaehler werden daher lokal aus den
        # paginierten Bundles berechnet.
        today_start = dt_util.start_of_local_day()
        devices, dashboard, cats, bundle_records = await asyncio.gather(
            self.api.async_get_devices(),
            self.api.async_get_dashboard(),
            self.api.async_list_cats(),
            self._async_fetch_bundles_until(dt_util.as_utc(today_start)),
        )
        today_records = [
            b
            for b in bundle_records
            if (created := parse_flappie_datetime(b.get("created_at")))
            and created >= dt_util.as_utc(today_start)
        ]

        operational = {
            status.get("device_id"): status
            for status in dashboard.get("operational_status") or []
        }

        per_device: dict[str, FlappieDeviceData] = {}
        for device in devices:
            device_id = device["id"]
            settings, status = await asyncio.gather(
                self.api.async_get_device_settings(device_id),
                self.api.async_get_device_status(device_id),
            )
            if device_id not in self._information:
                try:
                    self._information[device_id] = (
                        await self.api.async_get_device_information(device_id)
                    )
                except FlappieApiError:
                    self._information[device_id] = {}

            device_records = [
                b for b in bundle_records if b.get("catflap_id") == device_id
            ]
            per_device[device_id] = FlappieDeviceData(
                device=device,
                settings=settings,
                status=status,
                information=self._information[device_id],
                operational=operational.get(device_id) or {},
                last_bundle=device_records[0] if device_records else None,
                last_prey_bundle=next(
                    (b for b in device_records if b.get("is_prey")), None
                ),
                recent_bundles=device_records[:10],
            )

        self._dispatch_new_bundles(bundle_records[:20])
        data = FlappieData(
            devices=per_device,
            dashboard=dashboard,
            cats={cat["id"]: cat for cat in cats if "id" in cat},
            activity_today=len(today_records),
            prey_today=sum(1 for b in today_records if b.get("is_prey")),
        )
        await self._async_sync_statistics(data)
        return data

    async def _async_fetch_bundles_until(
        self, cutoff_utc: datetime, max_pages: int = 5
    ) -> list[dict[str, Any]]:
        """Bundles seitenweise laden, bis cutoff_utc erreicht ist."""
        records: list[dict[str, Any]] = []
        page = 1
        while page <= max_pages:
            resp = await self.api.async_list_bundles(page=page)
            recs = resp.get("records") or []
            records.extend(recs)
            if not recs or not resp.get("next_page"):
                break
            oldest = parse_flappie_datetime(recs[-1].get("created_at"))
            if oldest is not None and oldest < cutoff_utc:
                break
            page += 1
        return records

    async def _async_fetch_all_bundles(
        self, max_pages: int = 25
    ) -> list[dict[str, Any]]:
        """Alle noch nicht verfallenen Bundles laden (Fenster ~7 Tage)."""
        records: list[dict[str, Any]] = []
        page = 1
        while page <= max_pages:
            resp = await self.api.async_list_bundles(page=page)
            recs = resp.get("records") or []
            records.extend(recs)
            if not recs or not resp.get("next_page"):
                break
            page += 1
        return records

    def _dispatch_new_bundles(self, records: list[dict[str, Any]]) -> None:
        """Fire a dispatcher signal for every bundle we haven't seen yet."""
        ids = {b["id"] for b in records if "id" in b}
        if self._known_bundle_ids is None:
            # Erster Abruf: nur merken, keine Events für Altbestand feuern.
            self._known_bundle_ids = ids
            return
        new_ids = ids - self._known_bundle_ids
        self._known_bundle_ids |= ids
        for bundle in sorted(
            (b for b in records if b.get("id") in new_ids),
            key=lambda b: b.get("created_at") or "",
        ):
            async_dispatcher_send(
                self.hass,
                SIGNAL_NEW_BUNDLE.format(self.config_entry.entry_id),
                bundle,
            )

    # -------------------------------------------------- Langzeitstatistik

    def _stat_metadata(self, statistic_id: str, name: str) -> StatisticMetaData:
        meta: dict[str, Any] = {
            "source": DOMAIN,
            "statistic_id": statistic_id,
            "name": name,
            "unit_of_measurement": None,
            "has_sum": True,
        }
        if StatisticMeanType is not None:
            meta["mean_type"] = StatisticMeanType.NONE
        else:
            meta["has_mean"] = False
        return meta  # type: ignore[return-value]

    async def _async_sync_statistics(self, data: FlappieData) -> None:
        """Import Beute-/Aktivitaets-Zeitreihen als externe Statistiken.

        Laeuft hoechstens einmal pro Stunde; Fehler duerfen das normale
        Update nie blockieren.
        """
        now = dt_util.utcnow()
        if (
            self._stats_last_sync is not None
            and now - self._stats_last_sync < timedelta(hours=1)
        ):
            return
        try:
            await self._sync_prey_statistics(data)
            await self._sync_activity_statistics()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Statistik-Import fehlgeschlagen: %s", err)
            return
        self._stats_last_sync = now

    def _registration_date(self, data: FlappieData) -> datetime:
        """Aeltestes registered_at aller Klappen (Fallback: 1 Jahr)."""
        dates = [
            parsed
            for device_data in data.devices.values()
            if (
                parsed := parse_flappie_datetime(
                    device_data.device.get("registered_at")
                )
            )
        ]
        if dates:
            return min(dates)
        return dt_util.utcnow() - timedelta(days=365)

    async def _sync_prey_statistics(self, data: FlappieData) -> None:
        """Beute pro Tag seit Registrierung; die Cloud hat die volle Historie."""
        start = self._registration_date(data)
        series = await self.api.async_get_prey_stats(
            group_by="day",
            start_date=dt_util.as_local(start).date().isoformat(),
            end_date=dt_util.now().date().isoformat(),
        )
        # Die API liefert die Serie absteigend; fuer kumulierte Summen
        # muss aufsteigend sortiert werden.
        parsed = [
            (day, point.get("event_count") or 0)
            for point in series
            if (day := parse_flappie_datetime(point.get("date"))) is not None
        ]
        parsed.sort(key=lambda item: item[0])
        stats: list[StatisticData] = []
        cumulative = 0
        for day, count in parsed:
            cumulative += count
            if count == 0:
                continue  # Nulltage sparen; die Summe bleibt konsistent
            stats.append(
                StatisticData(
                    start=dt_util.start_of_local_day(dt_util.as_local(day)),
                    state=count,
                    sum=cumulative,
                )
            )
        if stats:
            async_add_external_statistics(
                self.hass,
                self._stat_metadata(f"{DOMAIN}:prey_daily", "Flappie Beute pro Tag"),
                stats,
            )

    async def _sync_activity_statistics(self) -> None:
        """Klappen-Ereignisse pro Tag.

        Das Backend ignoriert Datumsfilter und die Bundle-Liste verfaellt
        nach ~7 Tagen. Daher: alle verfuegbaren Bundles laden, lokal pro Tag
        zaehlen und die Summe aus der letzten gespeicherten Statistikzeile
        fortschreiben.
        """
        statistic_id = f"{DOMAIN}:activity_daily"
        records = await self._async_fetch_all_bundles()
        counts: dict[datetime, int] = {}
        for bundle in records:
            created = parse_flappie_datetime(bundle.get("created_at"))
            if created is None:
                continue
            day = dt_util.start_of_local_day(dt_util.as_local(created))
            counts[day] = counts.get(day, 0) + 1
        if not counts:
            return

        today_start = dt_util.start_of_local_day()
        # Der aelteste Tag im Fenster ist wegen des Verfalls evtl. unvollstaendig.
        oldest_full = dt_util.start_of_local_day(
            min(counts) + timedelta(days=1, hours=4)
        )

        last = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics, self.hass, 1, statistic_id, True, {"state", "sum"}
        )
        if last and statistic_id in last and last[statistic_id]:
            row = last[statistic_id][0]
            first_day = dt_util.start_of_local_day(
                dt_util.as_local(dt_util.utc_from_timestamp(row["start"]))
            )
            base = (row.get("sum") or 0) - (row.get("state") or 0)
            if (today_start - first_day).days > 60:
                # Zu grosse Luecke (HA lange aus): neu ab Fenster beginnen.
                first_day = oldest_full
        else:
            base = 0
            first_day = oldest_full

        stats: list[StatisticData] = []
        cumulative = base
        day = first_day
        while day <= today_start:
            count = counts.get(day, 0)
            cumulative += count
            stats.append(StatisticData(start=day, state=count, sum=cumulative))
            day = dt_util.start_of_local_day(day + timedelta(days=1, hours=4))
        if stats:
            async_add_external_statistics(
                self.hass,
                self._stat_metadata(statistic_id, "Flappie Aktivität pro Tag"),
                stats,
            )

    async def async_patch_settings(
        self, device_id: str, patch: dict[str, Any]
    ) -> None:
        """Patch device settings and push the fresh state to all entities."""
        try:
            settings = await self.api.async_patch_device_settings(device_id, patch)
        except FlappieAuthError as err:
            raise ConfigEntryAuthFailed from err
        if self.data and device_id in self.data.devices:
            self.data.devices[device_id].settings = settings
            self.async_update_listeners()
