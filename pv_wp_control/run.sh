#!/usr/bin/with-contenv bashio

echo "=== PV-WP-Control Add-on Starting ==="

MQTT_HOST=$(bashio::config 'mqtt_host')
MQTT_PORT=$(bashio::config 'mqtt_port')
MQTT_USER=$(bashio::config 'mqtt_user')
MQTT_PASS=$(bashio::config 'mqtt_password')
WP_IP=$(bashio::config 'wp_ip')
WP_PORT=$(bashio::config 'wp_port')
WP_SLAVE_ID=$(bashio::config 'wp_slave_id')
HA_ENTITY_PV=$(bashio::config 'ha_entity_pv_surplus')
MODBUS_REFRESH=$(bashio::config 'modbus_refresh_s')
MEASUREMENT_INTERVAL=$(bashio::config 'measurement_interval_s')
STARTUP_NO_LIMIT=$(bashio::config 'startup_no_limit_s')
WP_MIN_STANDZEIT=$(bashio::config 'wp_min_standzeit_min')
MAX_ABS_TEMP=$(bashio::config 'max_absolute_temperature')
MQTT_PREFIX=$(bashio::config 'mqtt_topic_prefix')
MQTT_DISC_PREFIX=$(bashio::config 'mqtt_discovery_prefix')
LOG_LEVEL=$(bashio::config 'log_level')
HA_TIMEOUT=$(bashio::config 'ha_connection_timeout_min')
MODBUS_RETRY=$(bashio::config 'modbus_retry_delay_s')

echo "MQTT: ${MQTT_HOST}:${MQTT_PORT} (User: ${MQTT_USER})"
echo "WP: ${WP_IP}:${WP_PORT} (Slave: ${WP_SLAVE_ID})"
echo "PV Entity: ${HA_ENTITY_PV}"

exec python3 /app/main.py \
    "${MQTT_HOST}" \
    "${MQTT_PORT}" \
    "${MQTT_USER}" \
    "${MQTT_PASS}" \
    "${WP_IP}" \
    "${WP_PORT}" \
    "${WP_SLAVE_ID}" \
    "${HA_ENTITY_PV}" \
    "${MODBUS_REFRESH}" \
    "${MEASUREMENT_INTERVAL}" \
    "${STARTUP_NO_LIMIT}" \
    "${WP_MIN_STANDZEIT}" \
    "${MAX_ABS_TEMP}" \
    "${MQTT_PREFIX}" \
    "${MQTT_DISC_PREFIX}" \
    "${LOG_LEVEL}" \
    "${SUPERVISOR_TOKEN}" \
    "${HA_TIMEOUT}" \
    "${MODBUS_RETRY}"
