# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

## [2.0.3] - 2026-05-05
### Added
- **MQTT Debugging:** Der komplette Payload der Sensordaten wird im Debug-Modus nun übersichtlich im Log ausgegeben, um die Fehlersuche zu erleichtern.

### Changed
- **Dynamische Versionierung:** Das Startskript (`run.sh`) nutzt nun die native `bashio::addon.version` API, um die Add-on-Version dynamisch aus der Konfiguration auszulesen (verhindert hartcodierte Versionstexte im Log).
- **Spannungs-Rundung:** Die Batteriespannung (Bus Voltage) wird vor dem Senden an MQTT auf eine Nachkommastelle gerundet (z. B. 4.2 V statt 4.152 V) für eine aufgeräumtere Dashboard-Anzeige.

### Fixed
- **Rauschunterdrückung (Batteriestrom):** Ein Deadband-Filter (Totzone) wurde in der `usv_status.py` integriert. Physisches Grundrauschen / 1-Bit-Jitter des Wandlers unter 5 mA wird nun ignoriert und sauber als `0.0 mA` ausgegeben.
- **Eingefrorene Batterie-Werte:** Ein Fehler wurde korrigiert, bei dem der INA219-Chip nach dem Start im "Triggered Mode" feststeckte. Das I2C-Register (`0x00`) steht nun auf `0x3F07` (Continuous Mode).

## [2.0.2] - 2026-04-22
### Hinzugefügt
- Dynamisches Loglevel (INFO/DEBUG) über HA-Konfiguration einstellbar.
- Konfigurierbare Hysterese für den Lüfter (Standard: 2.0°C).
- Konfigurierbare Batterie-Warnschwelle (`low_bat_warning`).
- Ausführliches Logging in allen Hardware-Treibern.

### Geändert
- **Intelligenter Kickstart:** Erfolgt nur noch, wenn der Lüfter physisch steht (RPM < 50).
- Umbenennung interner Variablen für bessere Lesbarkeit.

## [2.0.1] - 2026-04-20
### Geändert
- **Optimierte Lüftersteuerung:** Der Lüfter schaltet sich nun komplett ab (0 % PWM), solange die CPU-Temperatur unterhalb der konfigurierten `fanmintemp` liegt.
- **Kickstart-Funktion:** Um die mechanische Trägheit (das Losbrechmoment) zu überwinden, startet der Lüfter aus dem Stillstand nun mit einem kurzen Kickstart (100 % für 0,5 Sekunden), bevor er auf die Zielgeschwindigkeit regelt.
- **Angepasste Mindestdrehzahl:** Der Regelbereich beginnt nun bei schonenden 20 % statt 30 %, um das System bei leichter Last noch leiser zu machen.

## [2.0.0] - 2026-04-20
### Hinzugefügt
- Native Home Assistant UI-Konfiguration: Sensoren können nun direkt über die Add-on Optionen an- und abgeschaltet werden (Wegfall der `settings.yaml`).
- Vollständige Docker-Integration mit automatischem Base-Image-Support für ARM64.

### Geändert
- **Komplettes Rewrite der Architektur:** Das Add-on nutzt nun keine fehleranfälligen Subprozesse mehr, sondern hält die MQTT-Verbindung dauerhaft offen.
- Wechsel auf native Alpine Linux `smbus` Pakete für direktere I2C Kommunikation.
- Deutliche Reduzierung der CPU-Auslastung durch optimierte Python-Schleifen.

### Entfernt
- Veraltete `i2c_pkg` Bibliotheken und externe Adafruit-Abhängigkeiten komplett entfernt, um das Add-on schlanker und sicherer zu machen.

## [1.2.31] - Ältere Version
- Initiale Version (Lokales Add-on basierend auf separaten Skripten).