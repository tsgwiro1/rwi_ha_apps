# CM4 System Monitor für Home Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version: 2.0.2](https://img.shields.io/badge/Version-2.0.2-blue.svg)]()

Dieses Home Assistant Add-on überwacht die Hardware eines Raspberry Pi Compute Module 4 (CM4) in Kombination mit einem IO-Board (z. B. Waveshare CM4-POE-UPS-BASE). Es liest Sensordaten via I2C aus, steuert den Lüfter intelligent und sendet alle relevanten Statusdaten (Batteriespannung, Strom, Lüfter-RPM) per MQTT an Home Assistant.

Dank MQTT Auto-Discovery werden alle Sensoren in Home Assistant automatisch als Geräte angelegt – es ist kein manuelles YAML-Schreiben in der Home Assistant Konfiguration nötig!

## 🌟 Features

- **USV Überwachung:** Auslesen des INA219 Chips für Batteriespannung (V), aktuellen Stromverbrauch (mA) und errechneten Batteriestand (%).
- **Intelligente Lüftersteuerung:** Automatische, stufenlose Anpassung der Geschwindigkeit (EMC2301 Chip). Inklusive intelligenter Kickstart-Funktion (nur bei Stillstand) und konfigurierbarer Hysterese, um ständiges Ein- und Ausschalten zu verhindern.
- **Ressourcenschonend:** Komplett natives Alpine-Linux Docker Image mit direkter I2C-Ansprache via `smbus` (ohne teure Subprozesse).
- **Home Assistant UI:** Alle Sensoren und Parameter können bequem über die Add-on Optionen konfiguriert werden.

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
| `hostname` | String | Die IP-Adresse oder Hostname deines MQTT Brokers. | `core-mosquitto` |
| `port` | Integer | Der Port deines MQTT Brokers. | `1883` |
| `username` | String | Der Benutzername für den MQTT Broker. | - |
| `password` | String | Das Passwort für den MQTT Broker. | - |
| `devicename` | String | Interner Name für das MQTT Gerät. | `CM4 System Monitor` |
| `clientid` | String | Eindeutige MQTT Client ID. | `cm4_monitor` |
| `fanmintemp` | Integer | CPU Temp (°C), ab der der Lüfter anläuft (Minimaldrehzahl 20%). | `45` |
| `fanmaxtemp` | Integer | CPU Temp (°C), bei der der Lüfter auf 100% dreht. | `55` |
| `interval` | Integer | Zeit in Sekunden zwischen den Sensor-Updates. | `60` |
| `bat_v`, `bat_percent`... | Boolean | Schalter zum Aktivieren/Deaktivieren einzelner Sensoren. | `true` |
| `log_level` | Dropdown | Detailgrad der Protokolle. `info` für Normalbetrieb, `debug` für detaillierte Fehlersuche und Live-Analyse. | `info` |
| `low_bat_warning` | Float | Spannung (V), ab der eine Batteriewarnung ins Protokoll geschrieben wird. | `3.0` |
| `fan_hysteresis` | Float | Pufferzone in °C. Verhindert, dass der Lüfter an der Temperaturgrenze ständig an- und ausgeht. | `2.0` |

Speichere die Konfiguration, aktiviere "Beim Booten starten" (Start on boot) sowie "Watchdog" und starte das Add-on!

## 🐞 Fehlerbehebung / Logs

Wenn sich das System unerwartet verhält oder keine Daten ankommen:
1. Stelle den `log_level` in der Konfiguration auf `debug` und starte das Add-on neu.
2. Prüfe den Reiter **Protokolle**. Dort siehst du nun jeden einzelnen Entscheidungsschritt des Skripts (z. B. warum der Lüfter gerade läuft oder nicht) sowie detaillierte I2C- und MQTT-Meldungen.
3. Vergiss nicht, das Loglevel nach der Fehlersuche wieder auf `info` zurückzustellen, um das System zu entlasten.

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe die Datei `LICENSE` für weitere Details.