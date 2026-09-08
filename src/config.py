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
