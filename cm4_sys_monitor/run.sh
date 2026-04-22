#!/usr/bin/with-contenv bashio

HOST=$(bashio::config 'hostname')
PORT=$(bashio::config 'port')
USER=$(bashio::config 'username')
PWD=$(bashio::config 'password')
INTERVAL=$(bashio::config 'interval')
DEVICENAME=$(bashio::config 'devicename')
CLIENTID=$(bashio::config 'clientid')
FANMINTEMP=$(bashio::config 'fanmintemp')
FANMAXTEMP=$(bashio::config 'fanmaxtemp')

# Neue Sensor-Optionen auslesen
BAT_V=$(bashio::config 'bat_v')
BAT_P=$(bashio::config 'bat_percent')
BAT_C=$(bashio::config 'bat_curr')
FAN_S=$(bashio::config 'fan_speed')

# NEU: Konfigurationen für V2.0.2 auslesen
LOG_LEVEL=$(bashio::config 'log_level')
LOW_BAT_WARNING=$(bashio::config 'low_bat_warning')
FAN_HYSTERESIS=$(bashio::config 'fan_hysteresis')

bashio::log.info "Starte CM4 System Monitor v2.0.2..."

# Starte das Python-Skript mit allen Parametern
python3 system_sensors.py \
    "$HOST" "$PORT" "$USER" "$PWD" "$DEVICENAME" "$CLIENTID" \
    "$FANMINTEMP" "$FANMAXTEMP" "$INTERVAL" \
    "$BAT_V" "$BAT_P" "$BAT_C" "$FAN_S" \
    "$LOG_LEVEL" "$LOW_BAT_WARNING" "$FAN_HYSTERESIS"