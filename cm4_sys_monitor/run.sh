#!/usr/bin/with-contenv bashio

MQTT_HOST=$(bashio::config 'hostname')
MQTT_PORT=$(bashio::config 'port')
MQTT_USER=$(bashio::config 'username')
MQTT_PASSWORD=$(bashio::config 'password')
DEVICE_NAME=$(bashio::config 'devicename')
CLIENT_ID=$(bashio::config 'clientid')
FAN_MIN_TEMP=$(bashio::config 'fanmintemp')
FAN_MAX_TEMP=$(bashio::config 'fanmaxtemp')
INTERVAL=$(bashio::config 'interval')
ENABLE_BAT_V=$(bashio::config 'bat_v')
ENABLE_BAT_P=$(bashio::config 'bat_percent')
ENABLE_BAT_C=$(bashio::config 'bat_curr')
ENABLE_FAN_S=$(bashio::config 'fan_speed')
LOG_LEVEL=$(bashio::config 'log_level')
LOW_BAT_WARNING=$(bashio::config 'low_bat_warning')
FAN_HYSTERESIS=$(bashio::config 'fan_hysteresis')

echo "Starte CM4 System Monitor Python Skript..."

python3 system_sensors.py \
    "$MQTT_HOST" "$MQTT_PORT" "$MQTT_USER" "$MQTT_PASSWORD" \
    "$DEVICE_NAME" "$CLIENT_ID" \
    "$FAN_MIN_TEMP" "$FAN_MAX_TEMP" "$INTERVAL" \
    "$ENABLE_BAT_V" "$ENABLE_BAT_P" "$ENABLE_BAT_C" "$ENABLE_FAN_S" \
    "$LOG_LEVEL" "$LOW_BAT_WARNING" "$FAN_HYSTERESIS"