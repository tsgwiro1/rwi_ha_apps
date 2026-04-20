# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

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