# CM4 System Monitor – Dokumentation

Was die App tut, wie sie einzurichten ist und worauf man sich bei den Werten
verlassen kann. Überblick, Haftung und Installation stehen im
[README](https://github.com/tsgwiro1/rwi_ha_apps/blob/main/cm4_sys_monitor/README.md).

In diesem Dokument steht `<devicename>` für die Option `devicename` und
`<gerät>` für denselben Namen, kleingeschrieben und ohne Leerzeichen.

---

## Inhalt

1. [Funktionsprinzip](#1-funktionsprinzip)
2. [Optionen](#2-optionen)
3. [Lüfterregelung](#3-lüfterregelung)
4. [Home Assistant und MQTT](#4-home-assistant-und-mqtt)
5. [Genauigkeit der Akkuwerte](#5-genauigkeit-der-akkuwerte)
6. [Datenlast](#6-datenlast)
7. [Fehlerbehebung](#7-fehlerbehebung)
8. [Bekannte Punkte](#8-bekannte-punkte)
9. [Herkunft](#9-herkunft)

---

## 1. Funktionsprinzip

* **Eine Schleife, ein Takt.** Je Intervall liest die App die CPU-Temperatur,
  stellt den Lüfter nach, liest Akku und Drehzahl und sendet alle Werte als
  **eine** MQTT-Meldung.
* **Die Regelung hängt nicht am Broker.** Die Verbindung zum Broker läuft im
  Hintergrund und wird bei einem Abbruch neu aufgebaut. Der Lüfter wird auch
  dann geregelt, wenn der Broker nicht erreichbar ist.
* **Nur MQTT.** Die App spricht nicht mit der API von Home Assistant und liest
  keine Entitäten. Ihre Optionen liest sie aus `/data/options.json`.
* **Sicher beim Beenden.** Wird die App gestoppt, aktualisiert oder bricht sie
  mit einem Fehler ab, setzt sie den Lüfter auf volle Leistung und meldet sich
  bei Home Assistant ab.

---

## 2. Optionen

Vorgabewerte und erlaubte Bereiche stehen in der [`config.yaml`](https://github.com/tsgwiro1/rwi_ha_apps/blob/main/cm4_sys_monitor/config.yaml)
und erscheinen im Reiter **Konfiguration**.

| Gruppe | Option | Bedeutung |
| :--- | :--- | :--- |
| MQTT | `hostname`, `port` | Adresse und Port des Brokers |
| | `username`, `password` | Zugang zum Broker |
| | `clientid` | Optional. Leer lässt die App eine zufällige ID verwenden. |
| Gerät | `devicename` | Name des Geräts. Geht in jede `unique_id`, jede Entity-ID und jedes Topic ein. |
| Messung | `interval` | Sekunden zwischen zwei Durchläufen der Schleife |
| Lüfter | `fanmintemp` | Ab dieser CPU-Temperatur läuft der Lüfter mit Mindestlast |
| | `fanmaxtemp` | Ab dieser CPU-Temperatur läuft er voll |
| | `fan_hysteresis` | So weit unter `fanmintemp` schaltet er wieder ab |
| Sensoren | `bat_v`, `bat_percent`, `bat_curr`, `fan_speed` | Sensor senden oder aus Home Assistant entfernen |
| Log | `log_level` | `info` im Betrieb, `debug` für die Fehlersuche |

> ⚠️ **`devicename` nach der Einrichtung nicht mehr ändern.** Home Assistant legt
> sonst ein neues Gerät mit neuen Entitäten an; die alten bleiben zurück, und
> Automationen, Vorlagen und Dashboards zeigen ins Leere.

**Sensor abschalten:** Die App sendet dann eine leere Discovery-Nachricht, und
Home Assistant entfernt die Entität. Wird der Sensor wieder eingeschaltet, legt
Home Assistant ihn neu an – von Hand gesetzte Namen oder Icons sind dann weg.

---

## 3. Lüfterregelung

Die Regelung arbeitet mit der CPU-Temperatur aus
`/sys/class/thermal/thermal_zone0` und kennt vier Bereiche:

| CPU-Temperatur | Lüfter |
| :--- | :--- |
| unter `fanmintemp` − `fan_hysteresis` | aus |
| von `fanmintemp` − `fan_hysteresis` bis `fanmintemp` | bleibt, wie er war: läuft er, dann mit Mindestlast; steht er, bleibt er aus |
| von `fanmintemp` bis `fanmaxtemp` | linear von Mindestlast bis voll |
| ab `fanmaxtemp` | voll |

**Anlaufhilfe:** Soll der Lüfter anlaufen und dreht er noch nicht, läuft er
kurz voll, bevor er auf die berechnete Last geht. Dreht er schon, entfällt das.

**Voll, ohne zu rechnen,** läuft er in drei Fällen:

* die App wird beendet – beim Stoppen, bei einem Update, bei einem Neustart,
* die App bricht mit einem unerwarteten Fehler ab,
* die CPU-Temperatur ist nicht lesbar.

Mindestlast, Anlaufdauer und die Drehzahl, unter der der Lüfter als stehend
gilt, sind feste Werte: `FAN_MIN_PERCENT`, `FAN_KICKSTART_S` und
`FAN_STALL_RPM` in `system_sensors.py`.

> **Zum Watchdog:** Stürzt die App ab, bleibt der Lüfter auf voller Leistung
> stehen – laut, aber sicher. Mit eingeschaltetem **Watchdog** startet Home
> Assistant die App neu, und die Regelung läuft wieder.

---

## 4. Home Assistant und MQTT

### Topics

```
homeassistant/sensor/<gerät>/<schlüssel>/config   Discovery je Sensor, retained
system-sensors/sensor/<gerät>/state               Messwerte als JSON, je Intervall
system-sensors/sensor/<gerät>/availability        online / offline, retained
homeassistant/status                              abonniert
```

* **Beim Verbinden** meldet die App zuerst `online` und sendet dann die
  Discovery: für eingeschaltete Sensoren die Konfiguration, für abgeschaltete
  eine leere Nachricht.
* **Startet Home Assistant neu,** meldet es `online` auf `homeassistant/status`.
  Die App sendet die Discovery dann erneut.
* **Verfügbarkeit:** Beim Beenden meldet die App `offline`. Reisst die
  Verbindung ab, meldet der Broker `offline` an ihrer Stelle (Last Will). In
  beiden Fällen zeigen die Entitäten «nicht verfügbar».

### Messwerte

Eine Meldung auf dem `state`-Topic enthält die Schlüssel der eingeschalteten
Sensoren, zum Beispiel:

```json
{"bat_v": 4.124, "bat_percent": 93.7, "bat_curr": 569.8, "fan_speed": 2132}
```

Scheitert das Lesen eines Werts, steht dort `null`, und Home Assistant zeigt
«unbekannt» – nie eine erfundene 0.

### Das Gerät

| Feld | Wert |
| :--- | :--- |
| Name | `<devicename> Sensors` |
| Hersteller | Raspberry Pi |
| Modell | CM4 IO Board |
| Firmware | Version der App |
| Kennung | `<gerät>_sensor` |

### Entitäten

| Schlüssel | `unique_id` | Entity-ID bei Neuanlage | Name | Einheit, Klasse | `state_class` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `bat_v` | `<gerät>_bat_v` | `sensor.<gerät>_battery_voltage` | `<devicename> Battery Voltage` | V, `voltage` | – |
| `bat_percent` | `<gerät>_bat_percent` | `sensor.<gerät>_battery` | `<devicename> Battery` | %, `battery` | – |
| `bat_curr` | `<gerät>_bat_curr` | `sensor.<gerät>_battery_current` | `<devicename> Battery Current` | mA, `current` | `measurement` |
| `fan_speed` | `<gerät>_fan_speed` | `sensor.<gerät>_fan_speed` | `<devicename> Fan Speed` | rpm, Icon `mdi:fan` | – |

Die Entity-ID gibt die Discovery nur beim ersten Anlegen vor. Eine bestehende
Entität behält ihre ID, auch eine in Home Assistant umbenannte.

### Vom Gerät konsumiert

Nur `homeassistant/status`. Die App liest keine Entitäten und ruft keine
Dienste auf.

---

## 5. Genauigkeit der Akkuwerte

**Spannung:** Der INA219 misst die Busspannung in festen Schritten
(`BUS_VOLTAGE_LSB_V` in `usv_status.py`). Gesendet wird sie ungerundet mit drei
Nachkommastellen. Sie folgt der Last: Unter Last sinkt sie, beim Laden hebt der
Lader sie an.

**Strom:** Gemessen über einem Shunt von 0,01 Ω, aufgelöst in Schritten von
`CURRENT_LSB_MA`. Der Chip mittelt dabei über mehrere Wandlungen (`CONFIG` in
`usv_status.py`). **Positiv heisst Entladen, negativ Laden.** Kleine Werte werden
nicht unterdrückt: Am PoE mit vollem Akku liegt der Strom bei wenigen Milliampere
um null.

**Ladestand:** Eine lineare Umrechnung der Spannung zwischen `BAT_EMPTY_V` (0 %)
und `BAT_FULL_V` (100 %) in `system_sensors.py`. Weil die Spannung von der Last
abhängt, springt der Ladestand beim Umschalten zwischen PoE und Akku um mehrere
Prozentpunkte, ohne dass sich an der Ladung etwas geändert hat. Eine
Restlaufzeit lässt sich daraus nicht ablesen.

**Ob der Rechner auf Akku läuft,** zeigt der Strom zuverlässiger als der
Ladestand: Auf Akku liegt er bei mehreren hundert Milliampere, am PoE nahe null
oder negativ.

**Kalibrierung:** Die App prüft sie vor jeder Messung. Hat der Chip sie
verloren, etwa nach einem kurzen Spannungseinbruch, setzt sie sie neu und
vermerkt das im Log.

### Gemessen

Eine Installation am 2026-09-15, Home Assistant auf dem CM4 dieses Boards:

| Zustand | Spannung | Strom | Ladestand |
| :--- | :--- | :--- | :--- |
| am PoE, Akku voll | 4,176 V | −1 bis −2 mA | 98 % |
| PoE aus, erste Minuten | 4,108–4,124 V | +525 bis +760 mA | 94 % |
| nach 75 Minuten auf Akku | 4,052–4,064 V | +509 bis +571 mA | 88–89 % |
| dasselbe, Lüfter voll nach einem Neustart der App | 4,028 V | +982 mA | 86 % |

Zur Gegenprobe wurde der Strom aus der Shunt-Spannung nachgerechnet
(Shunt-Spannung ÷ 0,01 Ω). Die Abweichung zum gemeldeten Strom lag unter 0,5 mA.

---

## 6. Datenlast

Die App sendet eine MQTT-Meldung je Intervall. Das ist nicht automatisch eine
Datenbankzeile: Home Assistant schreibt nur, wenn sich der Zustand einer Entität
ändert.

Gemessen am 2026-09-15 über 106 Minuten, darin PoE und Akku sowie drei Neustarts
der App:

| Entität | Zustandswechsel |
| :--- | ---: |
| Lüfterdrehzahl | 109 |
| Akkustrom | 104 |
| Ladestand | 56 |
| Akkuspannung | 55 |

Akkustrom und Drehzahl ändern sich also praktisch bei jeder Meldung, Spannung und
Ladestand etwa bei jeder zweiten. Eine Langzeitstatistik führt Home Assistant nur
für den Akkustrom. Wer die Last senken will, erhöht `interval` oder schaltet
`fan_speed` ab.

Die App selbst, gemessen mit 2.1.0: rund 0,02 % CPU, 16 MB Arbeitsspeicher, ein
Image von 109 MB.

---

## 7. Fehlerbehebung

Für Einzelheiten `log_level` auf `debug` stellen: Das Log zeigt dann jede
Regelentscheidung und jede gesendete Nutzlast. Danach wieder auf `info`.

| Meldung im Log | Bedeutung |
| :--- | :--- |
| `INA219 initialisiert (Kalibrierung: 0x68f4, Konfiguration: 0x0eef)` | Normaler Start |
| `Fehler bei der Initialisierung des INA219: …` | Bus oder Chip nicht erreichbar. Die Akkuwerte bleiben «unbekannt», der Lüfter wird weiter geregelt. |
| `INA219 Kalibrierung … statt 0x68f4 gelesen – setze neu.` | Der Chip hat seine Einstellung verloren und sie neu erhalten. Einzeln unbedenklich. |
| `Fehler beim Auslesen der Bus-Spannung` / `des Stroms` | Einzelner Lesefehler, der Wert ist für diesen Durchlauf «unbekannt» |
| `MQTT Verbindungsfehler: …` | Der Broker lehnt ab, meist falscher Benutzer oder falsches Passwort |
| `Keine CPU-Temperatur – Lüfter auf 100%.` | Die Temperatur war nicht lesbar |
| `Fehler beim Setzen der Lüftergeschwindigkeit` / `beim Auslesen der RPM` | Lüfterregler nicht erreichbar |
| `Monitor wird beendet...`, danach `Lüfter auf 100%.` | Normales Beenden |

Im Log des Supervisors kann nach einem Update stehen: `Option '…' does not exist
in the schema`. Die gespeicherten Optionen enthalten dann noch eine entfernte
Option. Einmal im Reiter **Konfiguration** speichern, dann ist sie weg.

---

## 8. Bekannte Punkte

* **Nur dieses Board.** Bus und Adressen sind feste Werte: `I2C_BUS`,
  `INA219_ADDR` und `EMC2301_ADDR` in `system_sensors.py`.
* **Keine Abschaltung bei leerem Akku.** Das gehört in eine Automation in Home
  Assistant.
* **Kein Puffer ohne Broker.** Was während eines Ausfalls gemessen wird, geht
  verloren. Ein nicht erreichbarer Broker erscheint nicht im Log; die App
  versucht es still weiter, die Entitäten zeigen «nicht verfügbar».
* **Nach einem Neustart des Boards** regelt niemand den Lüfter, bis die App
  gestartet ist.
* **Drehzahl:** Die Umrechnung aus dem Zählerstand des EMC2301 enthält einen
  Korrekturfaktor (`TACH_CORRECTION` in `fan.py`), der nicht nachgemessen ist.
* **Modell fest eingetragen.** Die Geräteseite zeigt immer «CM4 IO Board»; das
  tatsächliche Modell ist im Container nicht lesbar.
* **Englische Entitätsnamen** aus der Discovery. In Home Assistant umbenennen
  ist möglich und bleibt erhalten.
* **Links in dieser Datei** funktionieren auf GitHub, im Reiter
  **Dokumentation** von Home Assistant nicht.

---

## 9. Herkunft

| Datei | Herkunft |
| :--- | :--- |
| `usv_status.py` | Kalibrierung, Strom-LSB und Umrechnung aus der INA219-Demo von Waveshare zum [CM4-POE-UPS-BASE](https://www.waveshare.com/wiki/CM4-POE-UPS-BASE). Registerzugriff, Prüfung der Kalibrierung und Fehlerbehandlung eigen. |
| `fan.py` | eigen |
| `system_sensors.py` | eigen. Das Topic-Schema `system-sensors/sensor/<gerät>/…` entspricht dem von [Sennevds/system_sensors](https://github.com/Sennevds/system_sensors). |
| `Dockerfile`, `run.sh`, `config.yaml`, `translations/` | eigen |

Die Version 1.2.31 bestand aus Skripten verschiedener Herkunft, die sich nicht
mehr im Einzelnen zurückverfolgen lassen. Mit 2.0.0 wurde die App neu
geschrieben.
