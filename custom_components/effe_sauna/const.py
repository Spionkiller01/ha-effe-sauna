"""Constants for the Effe ECC integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "effe_sauna"

API_BASE = "https://api.my.effe.it/v1"
COGNITO_URL = "https://cognito-idp.eu-central-1.amazonaws.com/"
COGNITO_CLIENT_ID = "3oben33a64egsbqtuljbvgkg5a"
APPSYNC_HOST = "gsxs2h3jabbm5kccpo4eqmwlve.appsync-api.eu-central-1.amazonaws.com"
APPSYNC_REALTIME_HOST = (
    "gsxs2h3jabbm5kccpo4eqmwlve.appsync-realtime-api.eu-central-1.amazonaws.com"
)

# Polling is only the fallback; state normally arrives through the AppSync push.
POLL_INTERVAL_PUSH = timedelta(minutes=5)
POLL_INTERVAL_NO_PUSH = timedelta(seconds=30)

COMMAND_VERSION = 4
TARGET_ALL = "ALL"
TARGET_HAMMAM = "HAMMAM"
TARGET_SAUNA = "SAUNA"

# Command functions exactly as the My Effe app sends them.
FN_INFO = "INFO"
FN_POWER = "POWER"
FN_STEAM = "STEAM"
FN_STEAM_SETPOINT = "STEAM_SETPOINT"
FN_SAUNA = "SAUNA"
FN_BIOSAUNA = "BIOSAUNA"
FN_IR = "IR"
FN_LIGHT = "LIGHT"
FN_MOOD = "MOOD"
FN_CHROMO = "CHROMO"
FN_CHROMO_SHOW = "CHROMO_SHOW"

# The app only offers three steam levels; these are the setpoints it sends.
STEAM_LEVELS = {"low": 42, "medium": 44, "high": 46}
STEAM_LEVELS_TOUCHNSTEAM = {"low": 42, "medium": 45, "high": 49}
TOUCHNSTEAM_TYPES = {"touchnsteam", "touchnsteamSmart"}

CHROMO_SHOWS = {
    "red": 1,
    "yellow": 2,
    "green": 3,
    "blue": 4,
    "water": 5,
    "sunrise": 6,
    "sunset": 7,
    "sea": 8,
    "wood": 9,
}

DIAGNOSTIC_MESSAGE_COUNT = 50
