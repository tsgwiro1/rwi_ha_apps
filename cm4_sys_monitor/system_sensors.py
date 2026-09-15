#!/usr/bin/env python3
import os
import json
import time
import signal
import logging
import paho.mqtt.client as mqtt
from usv_status import INA219
from fan import RaspiCM4IOBoardFanSensor

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("system_sensors")

# Home Assistant schreibt die App-Optionen hierher
OPTIONS_PATH = "/data/options.json"

# Hardware des CM4-POE-UPS-BASE
I2C_BUS = 10
INA219_ADDR = 0x43
EMC2301_ADDR = 0x2F

# Lüfter
FAN_MIN_PERCENT = 20     # Mindestlast, sobald er läuft
FAN_FULL_PERCENT = 100   # oberhalb fanmaxtemp, beim Kickstart, beim Beenden und ohne CPU-Temperatur
FAN_STALL_RPM = 50       # darunter gilt der Lüfter als stehend
FAN_KICKSTART_S = 0.5

# Ladestand linear aus der Akkuspannung
BAT_EMPTY_V = 3.0
BAT_FULL_V = 4.2

# Home Assistant meldet hier "online", wenn es (neu) gestartet ist
HA_STATUS_TOPIC = "homeassistant/status"
# So lange wartet das Beenden auf die Meldung "offline"
MQTT_STOP_TIMEOUT_S = 2

# Schlüssel in Optionen und Nutzlast -> Discovery. "entity_id" gilt nur für neu angelegte Entitäten.
SENSORS = {
    "bat_v": {"name": "Battery Voltage", "entity_id": "battery_voltage", "unit": "V", "class": "voltage"},
    "bat_percent": {"name": "Battery", "entity_id": "battery", "unit": "%", "class": "battery"},
    "bat_curr": {"name": "Battery Current", "entity_id": "battery_current", "unit": "mA", "class": "current", "state_class": "measurement"},
    "fan_speed": {"name": "Fan Speed", "entity_id": "fan_speed", "unit": "rpm", "icon": "mdi:fan"},
}


class Stop(Exception):
    """Beenden per SIGTERM, wenn Home Assistant die App stoppt."""


def stop_handler(signum, frame):
    raise Stop()


class SystemMonitor:
    def __init__(self, opts, version):
        self.dev_name = opts["devicename"].replace(' ', '').lower()
        self.disp_name = opts["devicename"]
        self.version = version
        self.fan_min = float(opts["fanmintemp"])
        self.fan_max = float(opts["fanmaxtemp"])
        self.fan_hysteresis = float(opts["fan_hysteresis"])
        self.interval = int(opts["interval"])
        self.enabled_sensors = {key: opts[key] for key in SENSORS}

        # Logging-Level dynamisch anwenden
        logging.getLogger().setLevel(getattr(logging, opts["log_level"].upper()))
        logger.info(f"Monitor gestartet. Loglevel: {opts['log_level'].upper()}")

        # Hardware initialisieren
        self.usv = INA219(bus=I2C_BUS, addr=INA219_ADDR)
        self.fan = RaspiCM4IOBoardFanSensor(busnum=I2C_BUS, address=EMC2301_ADDR)

        # Zustandsspeicher für den Lüfter-Kickstart
        self.fan_is_on = False

        # MQTT Client einrichten
        self.state_topic = f"system-sensors/sensor/{self.dev_name}/state"
        self.availability_topic = f"system-sensors/sensor/{self.dev_name}/availability"
        self.mqtt_host = opts["hostname"]
        self.mqtt_port = int(opts["port"])
        # clientid ist optional; ohne sie vergibt paho eine zufällige ID
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=opts.get("clientid", ""))
        self.client.username_pw_set(opts["username"], opts["password"])
        # Reisst die Verbindung ab, meldet der Broker "offline"
        self.client.will_set(self.availability_topic, "offline", retain=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error(f"MQTT Verbindungsfehler: {reason_code}")
            return
        logger.info("MQTT verbunden. Sende Discovery-Konfiguration...")
        client.subscribe(HA_STATUS_TOPIC)
        # Zuerst "online": Eine geänderte Discovery mit availability_topic zeigt sonst kurz "nicht verfügbar"
        client.publish(self.availability_topic, "online", retain=True)
        self.send_discovery()

    def on_message(self, client, userdata, message):
        if message.topic == HA_STATUS_TOPIC and message.payload == b"online":
            logger.info("Home Assistant ist neu gestartet. Sende Discovery-Konfiguration...")
            self.send_discovery()

    def send_discovery(self):
        """Sendet die Discovery für aktivierte Sensoren und entfernt abgeschaltete aus Home Assistant."""
        for key, info in SENSORS.items():
            topic = f"homeassistant/sensor/{self.dev_name}/{key}/config"

            if not self.enabled_sensors[key]:
                # Eine leere retained Nachricht entfernt die Entität
                self.client.publish(topic, "", retain=True)
                continue

            payload = {
                "name": f"{self.disp_name} {info['name']}",
                "default_entity_id": f"sensor.{self.dev_name}_{info['entity_id']}",
                "state_topic": self.state_topic,
                "availability_topic": self.availability_topic,
                "unit_of_measurement": info["unit"],
                "value_template": f"{{{{ value_json.{key} }}}}",
                "unique_id": f"{self.dev_name}_{key}",
                "device": {
                    "identifiers": [f"{self.dev_name}_sensor"],
                    "name": f"{self.disp_name} Sensors",
                    "model": "CM4 IO Board",
                    "manufacturer": "Raspberry Pi",
                    "sw_version": self.version
                }
            }
            if "class" in info: payload["device_class"] = info["class"]
            if "state_class" in info: payload["state_class"] = info["state_class"]
            if "icon" in info: payload["icon"] = info["icon"]

            self.client.publish(topic, json.dumps(payload), retain=True)

    def get_cpu_temp(self):
        """Liest die aktuelle CPU-Temperatur aus dem System, None bei einem Lesefehler."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return round(float(f.read()) / 1000, 1)
        except Exception as e:
            logger.error(f"Fehler beim Lesen der CPU Temperatur: {e}")
            return None

    def regulate_fan(self, cpu_temp):
        """Hysterese & intelligente Kickstart Logik."""
        current_rpm = self.fan.fan_speed()
        logger.debug(f"Gelesen: CPU Temp = {cpu_temp}°C | Fan RPM = {current_rpm}")

        if cpu_temp is None:
            logger.warning(f"Keine CPU-Temperatur – Lüfter auf {FAN_FULL_PERCENT}%.")
            pwm = FAN_FULL_PERCENT
            self.fan_is_on = True

        elif cpu_temp < (self.fan_min - self.fan_hysteresis):
            logger.debug(f"Status: Temperatur deutlich unter Minimum ({self.fan_min - self.fan_hysteresis}°C)")
            pwm = 0
            self.fan_is_on = False

        elif cpu_temp >= self.fan_min:
            logger.debug(f"Status: Temperatur über Minimum ({self.fan_min}°C). Berechne Last...")
            if cpu_temp >= self.fan_max:
                pwm = FAN_FULL_PERCENT
            else:
                pwm = FAN_MIN_PERCENT + (cpu_temp - self.fan_min) * ((FAN_FULL_PERCENT - FAN_MIN_PERCENT) / (self.fan_max - self.fan_min))

            if not self.fan_is_on:
                if current_rpm < FAN_STALL_RPM:
                    logger.debug(f"Entscheidung: Lüfter steht (RPM < {FAN_STALL_RPM}). Führe KICKSTART aus ({FAN_FULL_PERCENT}% für {FAN_KICKSTART_S}s).")
                    self.fan.set_fan_speed_percentage(FAN_FULL_PERCENT)
                    time.sleep(FAN_KICKSTART_S)
                else:
                    logger.debug(f"Entscheidung: Überspringe Kickstart, Lüfter dreht bereits mit {current_rpm} RPM.")
                self.fan_is_on = True

        else:
            logger.debug("Status: Temperatur in der Hysterese-Zone.")
            if self.fan_is_on:
                logger.debug(f"Aktion: Lüfter war an -> lasse ihn auf Minimalstufe ({FAN_MIN_PERCENT}%) weiterlaufen.")
                pwm = FAN_MIN_PERCENT
            else:
                pwm = 0

        self.fan.set_fan_speed_percentage(int(pwm))
        logger.debug(f"Setze Fan PWM = {int(pwm)}%")

    def collect_payload(self):
        """Sammelt die Messwerte. Bei einem Lesefehler steht None darin, Home Assistant zeigt dann "unbekannt"."""
        payload = {}

        if self.enabled_sensors["bat_v"] or self.enabled_sensors["bat_percent"]:
            # Spannung und Ladestand aus derselben Messung
            v = self.usv.get_bus_voltage()

            if self.enabled_sensors["bat_v"]:
                payload["bat_v"] = round(v, 3) if v is not None else None

            if self.enabled_sensors["bat_percent"]:
                if v is not None:
                    p = max(0, min(100, (v - BAT_EMPTY_V) / (BAT_FULL_V - BAT_EMPTY_V) * 100))
                    payload["bat_percent"] = round(p, 1)
                else:
                    payload["bat_percent"] = None

        if self.enabled_sensors["bat_curr"]:
            c = self.usv.get_current()
            payload["bat_curr"] = round(c, 1) if c is not None else None

        if self.enabled_sensors["fan_speed"]:
            payload["fan_speed"] = self.fan.fan_speed()

        return payload

    def run(self):
        """Hauptschleife des Monitors."""
        logger.info(f"Verbinde mit MQTT Broker {self.mqtt_host}...")
        # Verbindet im Hintergrund und versucht es weiter, solange der Broker nicht erreichbar ist
        self.client.connect_async(self.mqtt_host, self.mqtt_port)
        self.client.loop_start()

        try:
            while True:
                self.regulate_fan(self.get_cpu_temp())

                payload = self.collect_payload()
                logger.debug(f"MQTT Payload gesammelt: {payload}")
                if payload:
                    self.client.publish(self.state_topic, json.dumps(payload))

                # Warten bis zum nächsten Intervall
                time.sleep(self.interval)

        except (Stop, KeyboardInterrupt):
            logger.info("Monitor wird beendet...")

        finally:
            # Ohne Regelung soll der Lüfter nicht stehen bleiben
            logger.info(f"Lüfter auf {FAN_FULL_PERCENT}%.")
            self.fan.set_fan_speed_percentage(FAN_FULL_PERCENT)

            info = self.client.publish(self.availability_topic, "offline", retain=True)
            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                info.wait_for_publish(timeout=MQTT_STOP_TIMEOUT_S)
            self.client.disconnect()
            self.client.loop_stop()


if __name__ == "__main__":
    with open(OPTIONS_PATH) as f:
        options = json.load(f)

    signal.signal(signal.SIGTERM, stop_handler)
    SystemMonitor(options, os.environ["APP_VERSION"]).run()
