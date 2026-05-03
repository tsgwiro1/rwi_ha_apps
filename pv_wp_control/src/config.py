"""Konfiguration laden aus Kommandozeilen-Argumenten (von run.sh)."""

import sys
import os

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
        args = sys.argv

        if len(args) < 20:
            # Fallback: Lade aus /data/options.json (für lokalen Test)
            self._load_from_options_file()
            return

        # Aus run.sh Argumenten
        self.mqtt_host = args[1]
        self.mqtt_port = int(args[2])
        self.mqtt_user = args[3]
        self.mqtt_password = args[4]
        self.wp_ip = args[5]
        self.wp_port = int(args[6])
        self.wp_slave_id = int(args[7])
        self.ha_entity_pv_surplus = args[8]
        self.modbus_refresh_s = int(args[9])
        self.measurement_interval_s = int(args[10])
        self.startup_no_limit_s = int(args[11])
        self.wp_min_standzeit_min = int(args[12])
        self.max_absolute_temperature = float(args[13])
        self.mqtt_topic_prefix = args[14]
        self.mqtt_discovery_prefix = args[15]
        self.log_level = args[16]
        self.ha_token = args[17]
        self.ha_connection_timeout_min = int(args[18])
        self.modbus_retry_delay_s = int(args[19])

        # Fixed values
        self.register_timeout_min = 15
        self.ha_url = 'http://supervisor/core/api'

    def _load_from_options_file(self):
        """Fallback für lokalen Test."""
        import json
        import os

        options_file = '/data/options.json'
        if os.path.exists(options_file):
            with open(options_file, 'r') as f:
                opts = json.load(f)
        else:
            opts = {}

        self.wp_ip = opts.get('wp_ip', '192.168.0.175')
        self.wp_port = opts.get('wp_port', 502)
        self.wp_slave_id = opts.get('wp_slave_id', 1)
        self.ha_entity_pv_surplus = opts.get('ha_entity_pv_surplus',
                                             'sensor.solar_surplus_power')
        self.modbus_refresh_s = opts.get('modbus_refresh_s', 60)
        self.measurement_interval_s = opts.get('measurement_interval_s', 15)
        self.startup_no_limit_s = opts.get('startup_no_limit_s', 180)
        self.wp_min_standzeit_min = opts.get('wp_min_standzeit_min', 20)
        self.register_timeout_min = opts.get('register_timeout_min', 15)
        self.modbus_retry_delay_s = opts.get('modbus_retry_delay_s', 30)
        self.ha_connection_timeout_min = opts.get('ha_connection_timeout_min', 5)
        self.max_absolute_temperature = opts.get('max_absolute_temperature', 60.0)
        self.mqtt_topic_prefix = opts.get('mqtt_topic_prefix', 'pvwp')
        self.mqtt_discovery_prefix = opts.get('mqtt_discovery_prefix',
                                              'homeassistant')
        self.log_level = opts.get('log_level', 'info')
        self.mqtt_host = os.environ.get('MQTT_HOST', 'localhost')
        self.mqtt_port = int(os.environ.get('MQTT_PORT', '1883'))
        self.mqtt_user = os.environ.get('MQTT_USER', '')
        self.mqtt_password = os.environ.get('MQTT_PASSWORD', '')
        self.ha_token = os.environ.get('SUPERVISOR_TOKEN', '')
        self.ha_url = 'http://supervisor/core/api'

    @property
    def default_params(self):
        return {
            'mode': 'Aus',
            'offset': 5.0,
            'min_surplus': 800,
            'shutdown_delay': 30,
            'min_standzeit': 25,
            'max_temperature': 55.0,
            'min_power': 600,
        }
