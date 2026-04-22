#!/usr/bin/env python3
import sys
import time
import json
import logging
import paho.mqtt.client as mqtt
from usv_status import INA219
from fan import RaspiCM4IOBoardFanSensor

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("system_sensors")

class SystemMonitor:
    def __init__(self, args):
        # Mapping der Argumente aus der run.sh
        # args[0] ist der Skriptname, daher beginnen wir bei 1
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
        
        # Sensor-Schalter (kommen als 'true'/'false' Strings von bashio)
        self.enabled_sensors = {
            "bat_v": args[10] == 'true',
            "bat_percent": args[11] == 'true',
            "bat_curr": args[12] == 'true',
            "fan_speed": args[13] == 'true'
        }

        # NEU: Konfigurierbare Werte übernehmen
        log_level_str = args[14].upper()
        self.low_bat_warning = float(args[15])
        self.fan_hysteresis = float(args[16])

        # Logging-Level dynamisch anwenden
        numeric_level = getattr(logging, log_level_str, logging.INFO)
        logger.setLevel(numeric_level)
        logger.info(f"Monitor gestartet. Loglevel: {log_level_str}")

        # Hardware initialisieren
        # USV auf Bus 10, Adresse 0x43 (mit neuer Warnschwelle)
        self.usv = INA219(bus=10, addr=0x43, low_bat_warning=self.low_bat_warning)
        # Lüfter auf Bus 10, Adresse 0x2f (wird in fan.py definiert)
        self.fan = RaspiCM4IOBoardFanSensor(busnum=10)
        
        # Zustandsspeicher für den Lüfter-Kickstart
        self.fan_is_on = False
        
        # MQTT Client einrichten
        self.client = mqtt.Client(self.client_id)
        self.client.username_pw_set(self.mqtt_user, self.mqtt_pw)
        self.client.on_connect = self.on_connect

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT verbunden. Sende Discovery-Konfiguration...")
            self.send_discovery()
        else:
            logger.error(f"MQTT Verbindungsfehler mit Code: {rc}")

    def send_discovery(self):
        """Sendet die Home Assistant Discovery Payloads für aktivierte Sensoren."""
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
        """Liest die aktuelle CPU-Temperatur aus dem System."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return round(float(f.read()) / 1000, 1)
        except Exception as e:
            logger.error(f"Fehler beim Lesen der CPU Temperatur: {e}")
            return 0

    def run(self):
        """Hauptschleife des Monitors."""
        logger.info(f"Verbinde mit MQTT Broker {self.mqtt_host}...")
        self.client.connect(self.mqtt_host, self.mqtt_port)
        self.client.loop_start()
        
        try:
            while True:
                cpu_temp = self.get_cpu_temp()
                current_rpm = self.fan.fan_speed() # NEU: Für Kickstart-Check
                
                logger.debug(f"Gelesen: CPU Temp = {cpu_temp}°C | Fan RPM = {current_rpm}")
                
                # --- Hysterese & intelligente Kickstart Logik ---
                if cpu_temp < (self.fan_min - self.fan_hysteresis):
                    logger.debug(f"Status: Temperatur deutlich unter Minimum ({self.fan_min - self.fan_hysteresis}°C)")
                    pwm = 0
                    if self.fan_is_on:
                        logger.debug("Aktion: Lüfter war an -> schalte komplett ab (0%).")
                        self.fan.set_fan_speed_percentage(0)
                        self.fan_is_on = False
                        
                elif cpu_temp >= self.fan_min:
                    logger.debug(f"Status: Temperatur über Minimum ({self.fan_min}°C). Berechne Last...")
                    if cpu_temp >= self.fan_max:
                        pwm = 100
                    else:
                        pwm = 20 + (cpu_temp - self.fan_min) * (80 / (self.fan_max - self.fan_min))
                    
                    if not self.fan_is_on:
                        if current_rpm < 50:
                            logger.debug("Entscheidung: Lüfter steht (RPM < 50). Führe KICKSTART aus (100% für 0.5s).")
                            self.fan.set_fan_speed_percentage(100)
                            time.sleep(0.5)
                        else:
                            logger.debug(f"Entscheidung: Überspringe Kickstart, Lüfter dreht bereits mit {current_rpm} RPM.")
                        self.fan_is_on = True
                    
                    self.fan.set_fan_speed_percentage(int(pwm))
                    
                else:
                    logger.debug("Status: Temperatur in der Hysterese-Zone.")
                    if self.fan_is_on:
                        logger.debug("Aktion: Lüfter war an -> lasse ihn auf Minimalstufe (20%) weiterlaufen.")
                        self.fan.set_fan_speed_percentage(20)

                # --- Sensordaten sammeln ---
                payload = {}
                # Die Hardware-Abfragen erfolgen direkt über die importierten Klassen
                if self.enabled_sensors["bat_v"]:
                    payload["bat_v"] = round(self.usv.get_bus_voltage(), 3)
                
                if self.enabled_sensors["bat_percent"]:
                    v = self.usv.get_bus_voltage()
                    # Einfache Annahme: 3.0V = 0%, 4.2V = 100% (muss ggf. kalibriert werden)
                    p = max(0, min(100, (v - 3.0) / 1.2 * 100))
                    payload["bat_percent"] = round(p, 1)
                
                if self.enabled_sensors["bat_curr"]:
                    payload["bat_curr"] = round(self.usv.get_current(), 1)
                
                if self.enabled_sensors["fan_speed"]:
                    payload["fan_speed"] = self.fan.fan_speed()
                
                # Immer mitsenden
                payload["cpu_temp"] = cpu_temp

                # Daten via MQTT publizieren
                if payload:
                    self.client.publish(
                        f"system-sensors/sensor/{self.dev_name}/state", 
                        json.dumps(payload)
                    )
                
                # Warten bis zum nächsten Intervall
                time.sleep(self.interval)

        except KeyboardInterrupt:
            logger.info("Monitor wird beendet...")
            self.client.loop_stop()
            self.client.disconnect()

if __name__ == "__main__":
    # NEU: Wir erwarten nun 17 Argumente (Skriptname + 16 Variablen)
    if len(sys.argv) < 17:
        logger.error("Ungültige Anzahl an Argumenten übergeben.")
        sys.exit(1)
        
    monitor = SystemMonitor(sys.argv)
    monitor.run()