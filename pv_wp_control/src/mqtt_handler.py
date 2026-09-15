"""MQTT Handler: Discovery, Publish, Subscribe."""

import json
import paho.mqtt.client as mqtt

from config import VERSION, DEFAULT_PARAMS
from param_store import ParamStore


# So lange wartet das Beenden auf die Zustellung von "offline"
MQTT_STOP_TIMEOUT_S = 2


class MqttHandler:
    def __init__(self, config, log):
        self.config = config
        self.log = log
        self.prefix = config.mqtt_topic_prefix
        self.disc_prefix = config.mqtt_discovery_prefix
        self.availability_topic = f"{self.prefix}/availability"
        # Home Assistant meldet hier "online", wenn es (neu) gestartet ist
        self.ha_status_topic = f"{self.disc_prefix}/status"

        # Persistenter Parameter-Speicher
        self._store = ParamStore(DEFAULT_PARAMS, log)

        # MQTT Client
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id="pvwp_control")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        if config.mqtt_user:
            self.client.username_pw_set(config.mqtt_user, config.mqtt_password)

        # Last Will
        self.client.will_set(self.availability_topic, payload="offline",
                             retain=True)

    def connect(self):
        # Der Hintergrund-Thread verbindet und verbindet neu – auch wenn der
        # Broker beim Start der App noch nicht erreichbar ist
        try:
            self.client.connect_async(self.config.mqtt_host,
                                      self.config.mqtt_port)
            self.client.loop_start()
            self.log.info(f"MQTT: verbinde mit "
                          f"{self.config.mqtt_host}:{self.config.mqtt_port}")
        except Exception as e:
            self.log.error(f"MQTT Verbindung fehlgeschlagen: {e}")

    def disconnect(self):
        self.client.disconnect()
        self.client.loop_stop()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.log.error(f"MQTT: Verbindung fehlgeschlagen ({reason_code})")
            return
        self.log.info(f"MQTT verbunden: "
                      f"{self.config.mqtt_host}:{self.config.mqtt_port}")
        client.subscribe(f"{self.prefix}/set/#")
        client.subscribe(self.ha_status_topic)
        client.publish(self.availability_topic, "online", retain=True)
        # Bei jeder Verbindung – auch ein Broker ohne Persistenz hat danach alles
        self.publish_discovery()

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.log.warning(
                f"MQTT: Verbindung getrennt ({reason_code}), verbinde neu")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8').strip()

        if not payload:
            return

        if topic == self.ha_status_topic:
            if payload == 'online':
                self.log.info("MQTT: Home Assistant online, sende Discovery")
                self.publish_discovery()
            return

        try:
            # Command topic: {prefix}/set/{key}
            key = topic[len(f"{self.prefix}/set/"):]
            if key in DEFAULT_PARAMS:
                # Typ des Parameters aus seinem Startwert
                value = type(DEFAULT_PARAMS[key])(payload)
                self._store.set(key, value)
                self.log.info(f"MQTT Param: {key} = {value}")

                # Publish back confirmed value (für HA UI)
                self.client.publish(
                    f"{self.prefix}/{key}", str(value), retain=True)

        except (ValueError, TypeError) as e:
            self.log.debug(
                f"MQTT message parse skip: {e} "
                f"(topic={topic}, payload={payload})")
        except Exception as e:
            self.log.error(
                f"MQTT message Fehler: {e} "
                f"(topic={topic}, payload={payload})")

    def get_parameters(self):
        return self._store.get_all()

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
            'battery_soc': ('battery_soc', str),
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
        info = self.client.publish(self.availability_topic, "offline",
                                   retain=True)
        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            info.wait_for_publish(timeout=MQTT_STOP_TIMEOUT_S)

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
             "device_class": "power", "icon": "mdi:flash",
             "state_class": "measurement"},
            {"id": "heat_output", "name": "Heizleistung", "unit": "W",
             "device_class": "power", "icon": "mdi:fire",
             "state_class": "measurement"},
            {"id": "cop", "name": "COP", "icon": "mdi:gauge",
             "state_class": "measurement"},
            {"id": "rl_extern", "name": "Speichertemperatur", "unit": "°C",
             "device_class": "temperature", "icon": "mdi:thermometer",
             "state_class": "measurement"},
            {"id": "rl_soll", "name": "Sollwert", "unit": "°C",
             "device_class": "temperature", "icon": "mdi:thermometer-check",
             "state_class": "measurement"},
            {"id": "pv_surplus", "name": "PV Überschuss", "unit": "W",
             "device_class": "power", "icon": "mdi:solar-power",
             "state_class": "measurement"},
            {"id": "active_limit", "name": "Aktives Limit", "unit": "W",
             "icon": "mdi:speedometer",
             "state_class": "measurement"},
            {"id": "runtime", "name": "Laufzeit", "unit": "min",
             "icon": "mdi:timer-outline"},
            {"id": "cooldown", "name": "Standzeit", "unit": "min",
             "icon": "mdi:timer-sand"},
            {"id": "abregelung_timer", "name": "Abschalt-Timer", "unit": "min",
             "icon": "mdi:timer-alert-outline"},
            {"id": "energy_today", "name": "Energie heute", "unit": "kWh",
             "device_class": "energy", "icon": "mdi:counter",
             "state_class": "total_increasing"},
            {"id": "battery_soc", "name": "Batteriestand", "unit": "%",
             "device_class": "battery", "icon": "mdi:battery-charging-60",
             "state_class": "measurement"},
        ]

        for sensor in sensors:
            config_payload = {
                "name": sensor["name"],
                "unique_id": f"pvwp_{sensor['id']}",
                "state_topic": f"{self.prefix}/{sensor['id']}",
                "availability_topic": self.availability_topic,
                "device": device_info,
                "icon": sensor.get("icon"),
            }
            if "unit" in sensor:
                config_payload["unit_of_measurement"] = sensor["unit"]
            if "device_class" in sensor:
                config_payload["device_class"] = sensor["device_class"]
            if "state_class" in sensor:
                config_payload["state_class"] = sensor["state_class"]

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
                "availability_topic": self.availability_topic,
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
            "availability_topic": self.availability_topic,
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
            {"id": "min_start_duration", "name": "Min. Überschuss-Dauer",
             "min": 1, "max": 15, "step": 1, "unit": "min",
             "icon": "mdi:timer-sand"},
            {"id": "min_battery_soc", "name": "Min. Batteriestand",
             "min": 0, "max": 100, "step": 5, "unit": "%",
             "icon": "mdi:battery-charging-40"},
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
                "availability_topic": self.availability_topic,
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

        # Aktuelle Parameter-Werte an MQTT publizieren (für HA UI Sync)
        params = self._store.get_all()
        for key, value in params.items():
            self.client.publish(
                f"{self.prefix}/{key}", str(value), retain=True)

        self.log.info("MQTT Discovery publiziert (Sensors, Select, Numbers)")
