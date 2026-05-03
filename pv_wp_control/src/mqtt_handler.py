"""MQTT Handler: Discovery, Publish, Subscribe."""

import json
import time
import paho.mqtt.client as mqtt

from config import VERSION

class MqttHandler:
    def __init__(self, config, log):
        self.config = config
        self.log = log
        self.prefix = config.mqtt_topic_prefix
        self.disc_prefix = config.mqtt_discovery_prefix

        # Dynamic parameters (default values)
        self._params = dict(config.default_params)

        # MQTT Client
        self.client = mqtt.Client(client_id="pvwp_control")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        if config.mqtt_user:
            self.client.username_pw_set(config.mqtt_user, config.mqtt_password)

        # Last Will
        self.client.will_set(
            f"{self.prefix}/availability",
            payload="offline",
            retain=True
        )

    def connect(self):
        try:
            self.client.connect(self.config.mqtt_host, self.config.mqtt_port, 60)
            self.client.loop_start()
            self.log.info(f"MQTT verbunden: {self.config.mqtt_host}:{self.config.mqtt_port}")
        except Exception as e:
            self.log.error(f"MQTT Verbindung fehlgeschlagen: {e}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log.info("MQTT: Verbunden, subscribing...")
            client.subscribe(f"{self.prefix}/set/#")
            client.publish(f"{self.prefix}/availability", "online", retain=True)
        else:
            self.log.error(f"MQTT: Verbindung fehlgeschlagen (rc={rc})")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8').strip()

        try:
            param_map = {
                f"{self.prefix}/set/mode": ('mode', str),
                f"{self.prefix}/set/offset": ('offset', float),
                f"{self.prefix}/set/min_surplus": ('min_surplus', int),
                f"{self.prefix}/set/shutdown_delay": ('shutdown_delay', int),
                f"{self.prefix}/set/min_standzeit": ('min_standzeit', int),
                f"{self.prefix}/set/max_temperature": ('max_temperature', float),
                f"{self.prefix}/set/min_power": ('min_power', int),
            }

            if topic in param_map:
                key, cast = param_map[topic]
                value = cast(payload)
                self._params[key] = value
                self.log.info(f"MQTT Param: {key} = {value}")

                # Publish back confirmed value
                self.client.publish(
                    f"{self.prefix}/{key}",
                    str(value),
                    retain=True
                )
        except Exception as e:
            self.log.error(f"MQTT message Fehler: {e} (topic={topic}, payload={payload})")

    def get_parameters(self):
        return dict(self._params)

    def publish_status(self, status):
        mappings = {
            'state': ('state', str),
            'power': ('power_consumption', str),
            'heat_output': ('heat_output', str),
            'cop': ('cop', str),
            'rl_extern': ('rl_extern', str),
            'rl_soll': ('rl_soll', str),
            'pv_surplus': ('pv_surplus', str),
            'active_limit': ('active_limit', str),
            'runtime': ('runtime', str),
            'cooldown': ('cooldown', str),
            'abregelung_timer': ('abregelung_timer', str),
            'wp_running': ('wp_running', lambda x: 'ON' if x else 'OFF'),
            'modbus_connected': ('modbus_connected', lambda x: 'ON' if x else 'OFF'),
            'energy_today': ('energy_today', str),
        }

        for key, (topic_suffix, converter) in mappings.items():
            if key in status:
                value = converter(status[key]) if callable(converter) else str(status[key])
                self.client.publish(
                    f"{self.prefix}/{topic_suffix}",
                    value,
                    retain=True
                )

    def publish_offline(self):
        self.client.publish(f"{self.prefix}/availability", "offline", retain=True)

    def publish_discovery(self):
        """HA MQTT Auto-Discovery für alle Entities."""
        device_info = {
            "identifiers": ["pvwp_control"],
            "name": "PV Wärmepumpen Steuerung",
            "manufacturer": "Custom",
            "model": "PV-WP-Control",
            "sw_version": VERSION,
        }

        # === Sensors ===
        sensors = [
            {"id": "state", "name": "Zustand", "icon": "mdi:state-machine"},
            {"id": "power_consumption", "name": "Leistungsaufnahme", "unit": "W",
             "device_class": "power", "icon": "mdi:flash"},
            {"id": "heat_output", "name": "Heizleistung", "unit": "W",
             "device_class": "power", "icon": "mdi:fire"},
            {"id": "cop", "name": "COP", "icon": "mdi:gauge"},
            {"id": "rl_extern", "name": "Speichertemperatur", "unit": "°C",
             "device_class": "temperature", "icon": "mdi:thermometer"},
            {"id": "rl_soll", "name": "Sollwert", "unit": "°C",
             "device_class": "temperature", "icon": "mdi:thermometer-check"},
            {"id": "pv_surplus", "name": "PV Überschuss", "unit": "W",
             "device_class": "power", "icon": "mdi:solar-power"},
            {"id": "active_limit", "name": "Aktives Limit", "unit": "W",
             "icon": "mdi:speedometer"},
            {"id": "runtime", "name": "Laufzeit", "unit": "min",
             "icon": "mdi:timer-outline"},
            {"id": "cooldown", "name": "Standzeit", "unit": "min",
             "icon": "mdi:timer-sand"},
            {"id": "abregelung_timer", "name": "Abschalt-Timer", "unit": "min",
             "icon": "mdi:timer-alert-outline"},
            {"id": "energy_today", "name": "Energie heute", "unit": "kWh",
             "device_class": "energy", "icon": "mdi:counter"},
        ]

        for sensor in sensors:
            config_payload = {
                "name": sensor["name"],
                "unique_id": f"pvwp_{sensor['id']}",
                "state_topic": f"{self.prefix}/{sensor['id']}",
                "availability_topic": f"{self.prefix}/availability",
                "device": device_info,
                "icon": sensor.get("icon"),
            }
            if "unit" in sensor:
                config_payload["unit_of_measurement"] = sensor["unit"]
            if "device_class" in sensor:
                config_payload["device_class"] = sensor["device_class"]

            self.client.publish(
                f"{self.disc_prefix}/sensor/pvwp/{sensor['id']}/config",
                json.dumps(config_payload),
                retain=True
            )

        # === Binary Sensors ===
        bin_sensors = [
            {"id": "wp_running", "name": "WP Kompressor",
             "device_class": "running", "icon": "mdi:heat-pump"},
            {"id": "modbus_connected", "name": "Modbus Verbindung",
             "device_class": "connectivity", "icon": "mdi:lan-connect"},
        ]

        for sensor in bin_sensors:
            config_payload = {
                "name": sensor["name"],
                "unique_id": f"pvwp_{sensor['id']}",
                "state_topic": f"{self.prefix}/{sensor['id']}",
                "availability_topic": f"{self.prefix}/availability",
                "payload_on": "ON",
                "payload_off": "OFF",
                "device_class": sensor.get("device_class"),
                "device": device_info,
                "icon": sensor.get("icon"),
            }
            self.client.publish(
                f"{self.disc_prefix}/binary_sensor/pvwp/{sensor['id']}/config",
                json.dumps(config_payload),
                retain=True
            )

        # === Select (Mode) ===
        config_payload = {
            "name": "Betriebsmodus",
            "unique_id": "pvwp_mode",
            "state_topic": f"{self.prefix}/mode",
            "command_topic": f"{self.prefix}/set/mode",
            "options": ["Aus", "PV Überschuss", "Sofort"],
            "availability_topic": f"{self.prefix}/availability",
            "device": device_info,
            "icon": "mdi:power-standby",
        }
        self.client.publish(
            f"{self.disc_prefix}/select/pvwp/mode/config",
            json.dumps(config_payload),
            retain=True
        )

        # === Numbers ===
        numbers = [
            {"id": "offset", "name": "Offset", "min": 3.0, "max": 20.0,
             "step": 0.5, "unit": "K", "icon": "mdi:thermometer-plus"},
            {"id": "min_surplus", "name": "Min. PV Überschuss", "min": 500,
             "max": 5000, "step": 100, "unit": "W", "icon": "mdi:solar-power"},
            {"id": "shutdown_delay", "name": "Ausschaltverzögerung", "min": 5,
             "max": 60, "step": 5, "unit": "min", "icon": "mdi:timer-off"},
            {"id": "min_standzeit", "name": "Min. Standzeit", "min": 5,
             "max": 60, "step": 5, "unit": "min", "icon": "mdi:timer-lock"},
            {"id": "max_temperature", "name": "Max. Speichertemperatur",
             "min": 40.0, "max": 60.0, "step": 1.0, "unit": "°C",
             "icon": "mdi:thermometer-high"},
            {"id": "min_power", "name": "Min. Leistung", "min": 500,
             "max": 2000, "step": 100, "unit": "W",
             "icon": "mdi:speedometer-slow"},
        ]

        for num in numbers:
            config_payload = {
                "name": num["name"],
                "unique_id": f"pvwp_{num['id']}",
                "state_topic": f"{self.prefix}/{num['id']}",
                "command_topic": f"{self.prefix}/set/{num['id']}",
                "min": num["min"],
                "max": num["max"],
                "step": num["step"],
                "availability_topic": f"{self.prefix}/availability",
                "device": device_info,
                "icon": num.get("icon"),
            }
            if "unit" in num:
                config_payload["unit_of_measurement"] = num["unit"]

            self.client.publish(
                f"{self.disc_prefix}/number/pvwp/{num['id']}/config",
                json.dumps(config_payload),
                retain=True
            )

        # Publish initial parameter values
        time.sleep(1)
        defaults = self.config.default_params
        for key, value in defaults.items():
            self.client.publish(f"{self.prefix}/{key}", str(value), retain=True)

        self.log.info("MQTT Discovery publiziert (Sensors, Select, Numbers)")
