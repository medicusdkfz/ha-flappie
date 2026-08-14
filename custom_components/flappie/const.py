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
