# Changelog

## 0.8.2 — 2026-08-14

- CI runs the full HACS validation without the `brands` exception (the shipped brand icon satisfies the check) — prerequisite for the listing in the HACS default store

## 0.8.1 — 2026-08-14

- Ship the brand icon directly with the integration (`brand/icon.png`, supported since Home Assistant 2026.3) — the “icon not available” placeholder in the integrations page and HACS is gone. The home-assistant/brands repository no longer accepts icons for custom integrations.

## 0.8.0 — 2026-08-14

- Treatment intervals are now capped at **12 months** and use a slider (values above 12 are clamped on restore)
- New config switches on the cat door device:
  - **Treatments: link cats** — a date/interval entry applies to all cats at once
  - **Treatments: combo product (worms & fleas)** — deworming and flea treatment are maintained together (spot-on combo products)
  - Both combinable; every affected cat/treatment gets its own `flappie_health_updated` event (and thus its own calendar entry)

## 0.7.1 — 2026-08-14

- New event **`flappie_health_updated`** fired only on real user changes to the health tracker (never on restore after a restart) with `cat_name`, `health_type`, `last`, `interval_months` and `next_due` — the reliable trigger for calendar automations. Triggering on the *next due* sensors instead creates duplicate calendar entries on every Home Assistant restart.

## 0.7.0 — 2026-08-14

- New **Days until …** sensor per treatment (negative = overdue) — enables numeric dashboard conditions such as traffic-light colouring (red overdue, orange ≤ 14 days, green otherwise)

## 0.6.0 — 2026-08-14

- **Cat health tracking** per cat for deworming, flea treatment and vet visits: settable *last treatment* date, per-cat *interval in months* (defaults: 3/1/12), computed *next due* date and a *due* binary sensor for automations. Values are stored locally in Home Assistant (restart-safe) — the Flappie cloud has no such data.

## 0.5.0 — 2026-08-14

- New per-cat sensors: **Birthday** (date), **Age** (years), **Breed** and **Gender** (translated enum) — previously only available as attributes on the weight sensor

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
