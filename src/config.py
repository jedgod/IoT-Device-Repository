"""
Shared configuration for GreenHouseWatch.
Change MQTT_TOPIC if another classmate is using the same public broker topic.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
SAMPLES_DIR = PROJECT_ROOT / "samples"

DB_PATH = DATA_DIR / "iot_data.db"
CSV_PATH = DATA_DIR / "sensor_data.csv"
DEFAULT_CITY = "Bowie"
DEFAULT_COUNTRY = "US"

# Greenhouse site (Bowie, Maryland) for historical weather and local-time reporting
SITE_LATITUDE = 38.9429
SITE_LONGITUDE = -76.7300
SITE_TIMEZONE = "America/New_York"
WEATHER_HISTORY_PATH = DATA_DIR / "weather_history_bowie.json"
# Zones modelled hourly from real weather (Overview's primary zones)
HISTORY_ZONES = ["tomato-zone", "lettuce-zone", "seedling-zone"]

# MQTT (HiveMQ public broker — assignment requirement)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
# Unique-ish topic so the public broker is less noisy
MQTT_TOPIC = "ctec651/greenhousewatch/ipmcbit"
MQTT_CLIENT_PUB = "ctec651-ghw-publisher"
MQTT_CLIENT_SUB = "ctec651-ghw-subscriber"

# Simulation
PUBLISH_INTERVAL_SEC = 2
DEVICE_ID = "GH-SENSOR-01"

# Greenhouse operating thresholds (used for alerts + interpretation)
TEMP_MIN_C = 16.0
TEMP_MAX_C = 32.0
HUMIDITY_MIN = 40.0
HUMIDITY_MAX = 80.0
SOIL_MIN = 30.0
LIGHT_DAY_MIN = 200.0

# Monthly target temperature ranges for the dashboard and reporting views.
TEMP_MONTHLY_RANGE_C = {
    "September": {"min_c": 18.0, "max_c": 30.0},
    "October": {"min_c": 16.0, "max_c": 28.0},
    "November": {"min_c": 13.0, "max_c": 24.0},
    "December": {"min_c": 10.0, "max_c": 22.0},
}

ZONE_PROFILES = {
    "tomato-zone": {
        "label": "Tomatoes",
        "temp_min_c": 20.0,
        "temp_max_c": 28.0,
        "humidity_min": 55.0,
        "humidity_max": 75.0,
        "soil_min": 45.0,
        "description": "Heat tolerant crop with a preference for stable moisture.",
    },
    "lettuce-zone": {
        "label": "Lettuce",
        "temp_min_c": 15.0,
        "temp_max_c": 22.0,
        "humidity_min": 60.0,
        "humidity_max": 80.0,
        "soil_min": 50.0,
        "description": "Cooler crop that needs more humidity and lower heat stress.",
    },
    "cucumber-zone": {
        "label": "Cucumber",
        "temp_min_c": 21.0,
        "temp_max_c": 29.0,
        "humidity_min": 65.0,
        "humidity_max": 85.0,
        "soil_min": 52.0,
        "description": "High-growth vine crop that prefers warm, well-hydrated conditions.",
    },
    "carrot-zone": {
        "label": "Carrot",
        "temp_min_c": 12.0,
        "temp_max_c": 22.0,
        "humidity_min": 55.0,
        "humidity_max": 75.0,
        "soil_min": 48.0,
        "description": "Cool-weather root crop requiring consistent moisture and moderate temperature.",
    },
    "corn-zone": {
        "label": "Corn",
        "temp_min_c": 18.0,
        "temp_max_c": 30.0,
        "humidity_min": 50.0,
        "humidity_max": 75.0,
        "soil_min": 50.0,
        "description": "Tall grain crop requiring bright light, warm air, and steady root moisture.",
    },
    "onion-zone": {
        "label": "Onions",
        "temp_min_c": 13.0,
        "temp_max_c": 24.0,
        "humidity_min": 45.0,
        "humidity_max": 70.0,
        "soil_min": 42.0,
        "description": "Bulb crop preferring moderate temperatures and well-drained soil.",
    },
    "watermelon-zone": {
        "label": "Watermelon",
        "temp_min_c": 24.0,
        "temp_max_c": 32.0,
        "humidity_min": 50.0,
        "humidity_max": 70.0,
        "soil_min": 46.0,
        "description": "Fruit crop with a warmer threshold and strong water demand during peak growth.",
    },
    "seedling-zone": {
        "label": "Seedlings",
        "temp_min_c": 18.0,
        "temp_max_c": 24.0,
        "humidity_min": 65.0,
        "humidity_max": 82.0,
        "soil_min": 55.0,
        "description": "Sensitive propagation zone that prioritises steady moisture.",
    },
}

# Fixed chart colour per zone (validated categorical palette); colour follows the zone, never its rank.
ZONE_COLORS = {
    "tomato-zone": "#eb6834", "lettuce-zone": "#1baf7a", "seedling-zone": "#2a78d6",
    "cucumber-zone": "#eda100", "carrot-zone": "#e87ba4", "corn-zone": "#008300",
    "onion-zone": "#4a3aa7", "watermelon-zone": "#e34948",
}
DEVICE_COLOR = "#898781"

ALERT_LIFECYCLE_STATES = [
    "Normal",
    "Warning",
    "Critical",
    "Acknowledged",
    "Resolved",
]
