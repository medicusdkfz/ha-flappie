# Changelog

## 0.4.2 — 2026-08-14

- Fixed: cloud timestamps are timezone-naive **local time** (the device's `zone_info`), not UTC — all event timestamps were shifted by the UTC offset (e.g. +2 h in CEST). Verified against a real flap passage. Timestamps are now interpreted in Home Assistant's local timezone.
- Documented the cloud's processing latency (~5–10 min from flap passage to visibility in app/API)

## 0.4.1 — 2026-08-14

- Fixed: prey statistics series from the cloud is returned newest-first; cumulative sums are now computed in ascending order (charts showed negative bars before)

## 0.4.0 — 2026-08-14

- Long-term statistics: `flappie:activity_daily` (events per day, 7-day backfill, then continuously extended) and `flappie:prey_daily` (full history since device registration)
- New sensors: *Events today* and *Prey today* (reset at local midnight)
- Daily counts are computed client-side by paginating the event list — the backend ignores the documented `fromCreatedAt`/`toCreatedAt` filters

## 0.3.0 — 2026-08-14

- *Last prey event* sensor now reads the persistent `latest_prey_detection` field from the cloud dashboard (the event list expires after 7 days and lost older prey events)
- Four image entities *Event 1–4* for dashboard picture cards
- Media source: recent event videos playable in the HA media browser with fresh signed URLs on demand
- RFID switch disabled by default (the vendor states the door does not read microchips; the backend flag's effect is unknown)

## 0.2.0 — 2026-08-14

- Cat profiles become HA devices with weight sensor (breed, gender, birthday as attributes) and avatar image
- Image content type derived from the file extension (the CDN reports `binary/octet-stream`)

## 0.1.0 — 2026-08-14

- Initial release: config flow with re-auth, lock, door-mode select, settings switches and number, sensors, binary sensors, last-event image, event entity, German and English translations
