"""Constants for the Heizoel24 MEX integration."""

DOMAIN = "heizoel24mex"

LOGIN_URL = "https://www.heizoel24.de/api/account/anmelden"
DATA_URL = "https://www.heizoel24.de/api/customer/mex/dashboard/get"

# Total timeout in seconds for a request to the web API
REQUEST_TIMEOUT = 30

# Installations from before multi-sensor support keep the unique IDs of their
# entities for the sensor they were created for, stored under this key.
CONF_LEGACY_SENSOR_ID = "legacy_sensor_id"
LEGACY_UNIQUE_ID_PREFIX = f"{DOMAIN}.mex_"
