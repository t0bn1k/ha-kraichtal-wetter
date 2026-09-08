DOMAIN = "kraichtal_wetter"
CONF_API_URL = "api_url"
CONF_API_KEY = "key"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 300
PLATFORMS = ["sensor", "weather"]

# Default Kraichtal Wetter URL (hardcoded per request)
DEFAULT_API_URL = "https://kraichtal-wetter.de/dashboard/api.php"

# Where users request their own API key. Passed into the config flow as a
# description placeholder rather than written into the translations: hassfest
# rejects a literal URL in any translated string.
APPLY_URL = "https://kraichtal-wetter.de/dashboard/apply.php"
