# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

## [2.0.4] - 2026-09-15

### Geändert

- **Akkustrom mit Langzeitstatistik:** Die Discovery sendet für den Akkustrom `state_class: measurement`.
- **INA219-Konfiguration** `0x0EEF`: Verstärkung /2 (80 mV), wie im Code schon beschrieben, und je 32 Messungen für Bus- und Shunt-Spannung. Bisher stand `0x073F` im Register: Verstärkung /1 und für den Shunt eine einzelne Messung.
- README: Die Tabelle der Optionen nennt keine Vorgabewerte mehr, die stehen nur in der `config.yaml`. Zwei davon hatten ihr widersprochen (`fanmaxtemp`, `low_bat_warning`).

### Behoben

- **Akkustrom 2,25-fach zu hoch:** Das Kalibrierregister wurde byte-vertauscht geschrieben, im Chip stand `0xEC68` (60520) statt `0x68F4` (26868). Die Register werden jetzt mit dem höherwertigen Byte zuerst geschrieben und gelesen. Steht die Kalibrierung nicht mehr im Chip, etwa nach einem Reset, wird sie neu gesetzt und das im Log vermerkt.
- **Akkuspannung und Ladestand in groben Stufen:** Die Rundung auf 0,1 V aus 2.0.3 ist zurückgenommen. Die Spannung kommt mit drei Nachkommastellen. Der Ladestand wird aus der ungerundeten Spannung berechnet: Er springt nicht mehr in 8,3-%-Stufen und prellt nicht mehr im Minutentakt, wenn die Spannung nahe an einer Stufe liegt.
- **Totband beim Akkustrom:** Die Unterdrückung von Werten unter 5 mA aus 2.0.3 ist zurückgenommen. Das Rauschen glättet jetzt die Mittelung im Chip. Ob Home Assistant «am Netz» erkennt, entscheidet eine Grenze in Home Assistant.
- **Absturz beim Start:** Lag die CPU-Temperatur beim Start in der Hysterese-Zone knapp unter `fanmintemp`, brach die App mit `NameError` ab, und der Lüfter blieb ungeregelt.
- **Lesefehler als Nullwerte:** Scheitert das Lesen des INA219, meldet die App den Wert als unbekannt statt als 0 V, 0 % oder 0 mA.
- Spannung und Ladestand stammen aus derselben Messung.
- Negativer Strom wurde um ein LSB (0,15 mA) falsch umgerechnet.

Entity-IDs, `unique_id`s und die Schlüssel der MQTT-Nutzlast sind unverändert.

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

[2.0.4]: https://github.com/tsgwiro1/rwi_ha_apps/tree/cm4_sys_monitor/v2.0.4
