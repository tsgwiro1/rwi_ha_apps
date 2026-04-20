# CM4 System Monitor für Home Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version: 2.0.0](https://img.shields.io/badge/Version-2.0.0-blue.svg)]()

Dieses Home Assistant Add-on überwacht die Hardware eines Raspberry Pi Compute Module 4 (CM4) in Kombination mit einem IO-Board (z. B. Waveshare CM4-POE-UPS-BASE). Es liest Sensordaten via I2C aus, steuert den Lüfter temperaturbasiert und sendet alle relevanten Statusdaten (Batteriespannung, Strom, Lüfter-RPM) per MQTT an Home Assistant.

Dank MQTT Auto-Discovery werden alle Sensoren in Home Assistant automatisch als Geräte angelegt – es ist kein manuelles YAML-Schreiben in der Home Assistant Konfiguration nötig!

## 🌟 Features

- **USV Überwachung:** Auslesen des INA219 Chips für Batteriespannung (V), aktuellen Stromverbrauch (mA) und errechneten Batteriestand (%).
- **Lüftersteuerung:** Automatische, stufenlose Anpassung der Lüftergeschwindigkeit (EMC2301 Chip) basierend auf der aktuellen CPU-Temperatur.
- **Ressourcenschonend:** Komplett natives Alpine-Linux Docker Image mit direkter I2C-Ansprache via `smbus` (ohne teure Subprozesse).
- **Home Assistant UI:** Alle Sensoren können direkt in der Add-on Konfigurationsoberfläche einzeln aktiviert oder deaktiviert werden.

## 🛠️ Voraussetzungen

1. **Hardware:** Ein Raspberry Pi CM4 mit entsprechendem IO-Board (mit INA219 und EMC2301 Chips auf dem I2C Bus).
2. **I2C Aktivierung:** Der I2C-Bus muss im Home Assistant OS (Host-System) aktiviert sein.
3. **MQTT Broker:** Ein laufender MQTT Broker (z. B. das offizielle Mosquitto Add-on) im Home Assistant.

## 📦 Installation

1. Navigiere in Home Assistant zu **Einstellungen** -> **Add-ons**.
2. Klicke unten rechts auf **Add-on Store**.
3. Klicke oben rechts auf die drei Punkte (⋮) und wähle **Repositories**.
4. Füge die URL dieses Repositories hinzu: `https://github.com/tsgwiro1/rwi_ha_apps`
5. Schließe das Fenster und lade die Seite neu.
6. Scrolle nach unten zur neuen Kategorie und installiere den **CM4 System Monitor**.

## ⚙️ Konfiguration

Nach der Installation musst du das Add-on im Reiter **Konfiguration** anpassen:

| Option | Typ | Beschreibung | Standardwert |
| :--- | :--- | :--- | :--- |
| `hostname` | String | Die IP-Adresse oder der Hostname deines MQTT Brokers (z.B. `core-mosquitto`). | - |
| `port` | Integer | Der Port deines MQTT Brokers. | `1883` |
| `username` | String | Der Benutzername für den MQTT Broker. | - |
| `password` | String | Das Passwort für den MQTT Broker. | - |
| `interval` | Integer | Zeit in Sekunden zwischen den Sensor-Updates. | `60` |
| `devicename` | String | Interner Name für das MQTT Gerät. | `cm4_sys_mon` |
| `clientid` | String | Eindeutige MQTT Client ID. | - |
| `fanmintemp` | Integer | CPU Temperatur (°C), ab der der Lüfter anläuft. | `35` |
| `fanmaxtemp` | Integer | CPU Temperatur (°C), bei der der Lüfter auf 100% dreht. | `50` |
| `bat_v`, `bat_percent`, etc. | Boolean | Schalter zum Aktivieren/Deaktivieren einzelner Sensoren. | `true` |

Speichere die Konfiguration, aktiviere "Beim Booten starten" (Start on boot) sowie "Watchdog" und starte das Add-on!

## 🐞 Fehlerbehebung / Logs

Wenn keine Daten in Home Assistant ankommen:
1. Prüfe den Reiter **Protokolle** im Add-on. Steht dort `MQTT verbunden`? Falls nein, prüfe deine MQTT-Zugangsdaten.
2. Tauchen I2C-Fehler im Log auf? Stelle sicher, dass I2C in deinem Host-System korrekt aktiviert ist und die Hardware-Adressen (Standard: Bus 10, Addr 0x43 & 0x2f) stimmen.

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe die Datei `LICENSE` für weitere Details.