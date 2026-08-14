"""Constants for the Flappie integration."""

from __future__ import annotations

DOMAIN = "flappie"

BASE_URL = "https://app.flappiedoors.com"

DEFAULT_SCAN_INTERVAL = 60  # seconds; README des API-Pakets bittet um >= 30 s

SIGNAL_NEW_BUNDLE = "flappie_new_bundle_{}"  # formatiert mit entry_id

# DoorPolicy-Werte der Cloud-API
POLICY_OPEN = "OPEN"
POLICY_CLOSED = "CLOSED"
POLICY_OPEN_IN = "OPEN_IN"
POLICY_OPEN_OUT = "OPEN_OUT"

DOOR_POLICIES = [POLICY_OPEN, POLICY_CLOSED, POLICY_OPEN_IN, POLICY_OPEN_OUT]

# Mapping Select-Option (lowercase, übersetzbar) <-> API-Wert
OPTION_TO_POLICY = {
    "open": POLICY_OPEN,
    "closed": POLICY_CLOSED,
    "open_in": POLICY_OPEN_IN,
    "open_out": POLICY_OPEN_OUT,
}
POLICY_TO_OPTION = {v: k for k, v in OPTION_TO_POLICY.items()}

EVENT_TYPE_ACTIVITY = "activity"
EVENT_TYPE_PREY = "prey"

# Gesundheits-Tracking pro Katze (lokal gepflegt, nicht aus der Cloud).
# Wert = Standard-Intervall in Monaten.
HEALTH_TYPES: dict[str, int] = {
    "worms": 3,   # Wurmkur
    "fleas": 1,   # Flohbehandlung
    "vet": 12,    # Arztbesuch
}

HEALTH_INTERVAL_MAX = 12  # Monate

# Wird bei echten Benutzeraenderungen am Gesundheits-Tracking gefeuert
# (nicht beim Restore nach Neustarts) — als Trigger fuer Automatisierungen.
EVENT_HEALTH_UPDATED = "flappie_health_updated"

HEALTH_ICONS: dict[str, str] = {
    "worms": "mdi:pill",
    "fleas": "mdi:bug-outline",
    "vet": "mdi:stethoscope",
}
