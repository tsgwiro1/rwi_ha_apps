#!/usr/bin/env python3
import sys
import time
import json
import logging
import paho.mqtt.client as mqtt
from usv_status import INA219
from fan import RaspiCM4IOBoardFanSensor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("system_sensors")

class SystemMonitor:
    def __init__(self, args):
        # Mapping der Argumente (Reihenfolge wie in run.sh)
        self.mqtt_host = args[1]
        self.mqtt_port = int(args[2])
        self.mqtt_user = args[3]
        self.mqtt_pw   = args[4]
        self.dev_name  = args[5].replace(' ', '').lower()
        self.disp_name = args[5]
        self.client_id = args[6] or "cm4_monitor"
        self.fan_min   = float(args[7])
        self.fan_max   = float(args[8])
        self.interval  = int(args[9])
        
        # Sensor Toggles (Kommen als 'true'/'false' Strings von bashio)
        self.enabled_sensors = {
            "bat_v": args[10] == 'true',
            "bat_percent": args[11] == 'true',
            "bat_curr": args[12] == 'true',
            "fan_speed": args[13] == 'true'
        }

        # Hardware initialisieren
        self.usv = INA219(bus=10, addr=0x43)
        self.fan = RaspiCM4IOBoardFanSensor(busnum=10)
        
        self.client = mqtt.Client(self.client_id)
        self.client.username_pw_set(self.mqtt_user, self.mqtt_pw)
        self.client.on_connect = self.on_connect

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT verbunden. Sende Konfiguration...")
            self.send_discovery()
        else:
            logger.error(f"MQTT Verbindungsfehler: {rc}")

    def send_discovery(self):
        # Definition der möglichen Sensoren
        config_data = {
            "bat_v": {"name": "Battery Voltage", "unit": "V", "class": "voltage"},
            "bat_percent": {"name": "Battery", "unit": "%", "class": "battery"},
            "bat_curr": {"name": "Battery Current", "unit": "mA", "class": "current"},
            "fan_speed": {"name": "Fan Speed", "unit": "rpm", "icon": "mdi:fan"}
        }

        for key, info in config_data.items():
            if self.enabled_sensors.get(key):
                topic = f"homeassistant/sensor/{self.dev_name}/{key}/config"
                payload = {
                    "name": f"{self.disp_name} {info['name']}",
                    "state_topic": f"system-sensors/sensor/{self.dev_name}/state",
                    "unit_of_measurement": info.get("unit"),
                    "value_template": f"{{{{ value_json.{key} }}}}",
                    "unique_id": f"{self.dev_name}_{key}",
                    "device": {
                        "identifiers": [f"{self.dev_name}_sensor"],
                        "name": f"{self.disp_name} Sensors",
                        "model": "CM4 IO Board",
                        "manufacturer": "Raspberry Pi"
                    }
                }
                if "class" in info: payload["device_class"] = info["class"]
                if "icon" in info: payload["icon"] = info["icon"]
                
                self.client.publish(topic, json.dumps(payload), retain=True)

    def get_cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return round(float(f.read()) / 1000, 1)
        except: return 0

    def run(self):
        self.client.connect(self.mqtt_host, self.mqtt_port)
        self.client.loop_start()
        
        try:
            while True:
                cpu_temp = self.get_cpu_temp()
                
                # Lüftersteuerung (immer aktiv für Sicherheit)
                pwm = 30
                if cpu_temp > self.fan_min:
                    pwm = min(100, 30 + (cpu_temp - self.fan_min) * (70 / (self.fan_max - self.fan_min)))
                self.fan.set_fan_speed_percentage(int(pwm))

                # Daten sammeln
                payload = {}
                if self.enabled_sensors["bat_v"]:
                    payload["bat_v"] = round(self.usv.get_bus_voltage(), 3)
                if self.enabled_sensors["bat_percent"]:
                    v = self.usv.get_bus_voltage()
                    payload["bat_percent"] = round(max(0, min(100, (v - 3.0) / 1.2 * 100)), 1)
                if self.enabled_sensors["bat_curr"]:
                    payload["bat_curr"] = round(self.usv.get_current(), 1)
                if self.enabled_sensors["fan_speed"]:
                    payload["fan_speed"] = self.fan.fan_speed()
                
                if payload:
                    self.client.publish(f"system-sensors/sensor/{self.dev_name}/state", json.dumps(payload))
                
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.client.loop_stop()

if __name__ == "__main__":
    monitor = SystemMonitor(sys.argv)
    monitor.run()