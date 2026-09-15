"""Konfiguration: App-Optionen aus /data/options.json, Version aus config.yaml."""

import json
import os
import sys

# Home Assistant schreibt die App-Optionen hierher
OPTIONS_PATH = '/data/options.json'

# REST-API von Home Assistant über den Supervisor
HA_URL = 'http://supervisor/core/api'

# Dashboard-Parameter beim ersten Start; danach gilt /data/params.json
DEFAULT_PARAMS = {
    'mode': 'Aus',
    'offset': 5.0,
    'min_surplus': 800,
    'shutdown_delay': 30,
    'min_standzeit': 25,
    'max_temperature': 55.0,
    'min_power': 600,
    'min_start_duration': 10,
    'min_battery_soc': 0,
}

# Version aus config.yaml lesen (single source of truth)
VERSION = "unknown"
_config_yaml_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
if os.path.exists(_config_yaml_path):
    with open(_config_yaml_path, 'r') as _f:
        for _line in _f:
            if _line.strip().startswith('version:'):
                VERSION = _line.split(':', 1)[1].strip().strip('"').strip("'")
                break


class Config:
    def __init__(self):
        try:
            with open(OPTIONS_PATH, 'r') as f:
                opts = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            sys.exit(f"App-Optionen nicht lesbar ({OPTIONS_PATH}): {e}")

        # Vorgaben stehen nur in config.yaml. Fehlt eine Pflichtoption,
        # bricht das Programm ab, statt mit einem eigenen Wert zu laufen.
        try:
            self.mqtt_host = opts['mqtt_host']
            self.mqtt_port = opts['mqtt_port']
            self.wp_ip = opts['wp_ip']
            self.wp_port = opts['wp_port']
            self.wp_slave_id = opts['wp_slave_id']
            self.ha_entity_pv_surplus = opts['ha_entity_pv_surplus']
            self.ha_entity_battery_soc = opts['ha_entity_battery_soc']
            self.modbus_refresh_s = opts['modbus_refresh_s']
            self.measurement_interval_s = opts['measurement_interval_s']
            self.startup_no_limit_s = opts['startup_no_limit_s']
            self.wp_min_standzeit_min = opts['wp_min_standzeit_min']
            self.modbus_retry_delay_s = opts['modbus_retry_delay_s']
            self.ha_connection_timeout_min = opts['ha_connection_timeout_min']
            self.max_absolute_temperature = opts['max_absolute_temperature']
            self.mqtt_topic_prefix = opts['mqtt_topic_prefix']
            self.mqtt_discovery_prefix = opts['mqtt_discovery_prefix']
            self.log_level = opts['log_level']
        except KeyError as e:
            sys.exit(f"App-Option fehlt: {e.args[0]} – "
                     f"in der Konfiguration der App setzen")

        # Im Schema optional: fehlt die Option, meldet sich die App ohne
        # Benutzer am Broker an
        self.mqtt_user = opts.get('mqtt_user')
        self.mqtt_password = opts.get('mqtt_password')

        try:
            self.ha_token = os.environ['SUPERVISOR_TOKEN']
        except KeyError:
            sys.exit("SUPERVISOR_TOKEN fehlt – "
                     "läuft das Programm ausserhalb von Home Assistant?")
