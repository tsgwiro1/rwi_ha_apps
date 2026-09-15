# Offene Punkte «CM4 System Monitor»

Posteingang dieser App. Einträge werden angefügt; erledigt meldet, wer an der
App arbeitet.

---

## 2026-09-15 – aus dem HA-Chat «SysMon»: zwei Fehler in `usv_status.py`

Gefunden bei einem Test mit abgeschaltetem PoE am HA-Board (Akkubetrieb ab
12:26). Beide Programme – diese App auf dem HA-Board und `system_sensor` auf
timbuktu – lesen denselben INA219 (Bus 10, Adresse 0x43) auf baugleichen
Waveshare CM4-POE-UPS-BASE-Boards und nehmen einen Shunt von 0,01 Ω an.

### 1. Kalibrierregister byte-vertauscht → Strom 2,25-fach zu hoch

`usv_status.py` Zeile 14:

```python
self.bus.write_word_data(self.addr, 0x05, 0x68EC) # 26868 in hex (lsb swapped für smbus)
```

smbus sendet das niedere Byte zuerst, der INA219 liest das erste Byte als
höheres. Im Register landet deshalb **0xEC68 = 60520**, nicht 26868. Bei der
Konfiguration in Zeile 16 (`0x3F07` → Register 0x073F) ist die Vertauschung
richtig bedacht, hier nicht. Ausserdem ist 26868 hexadezimal 0x68F4, nicht
0x68EC.

Belegt am 2026-09-15 durch Zurücklesen am laufenden Board:

| Register | gelesen | erwartet |
| :--- | :--- | :--- |
| 0x05 Kalibrierung | 0xEC68 (60520) | 0x68F4 (26868) |
| 0x00 Konfiguration | 0x073F | 0x073F |

Stromregister ÷ Shunt-Register = 14,78 (= 60520/4096) statt 6,56. Gegenprobe
über die kalibrierungsfreie Shunt-Spannung: 5,1 mV bzw. 7,4 mV an 0,01 Ω =
510 bzw. 740 mA; die App meldete 1148 bzw. 1673 mA. system_sensor auf timbuktu
schreibt 26868 korrekt (MSB zuerst über `write_i2c_block_data`).

**Korrektur:** `0x68EC` → `0xF468`. Danach am Board das Register 0x05
zurücklesen (muss 0x68F4 ergeben).

### 2. Spannung auf 0,1 V gerundet

`usv_status.py` Zeile 33: `return round(voltage, 1)`.

Die Nutzlast rundet in `system_sensors.py` Zeile 156 ohnehin auf drei Stellen;
diese Rundung ist überflüssig und macht die Spannung für HA unbrauchbar: Am
Chip 4,060–4,080 V, gesendet `4.1`. Der Ladestand (`system_sensors.py`
Zeile 160 ff.) rechnet aus demselben gerundeten Wert und springt in
8,3-%-Stufen (91,7 → 83,3 …) – eine Prozentgrenze wie «unter 20 %» in der
HA-Abschaltautomation greift dadurch erst bei 16,7 %.

**Korrektur:** `return voltage`.

### Nach der Korrektur in HA

- SysMon-View: Stromring (`sensor.ha_system_sensors_cm4_sys_mon_battery_current`)
  zeigt dann den echten Strom; Skala ±1200 mA passt.
- `automation.system_shutdown_on_critical_battery_level` erneut prüfen.

### Nachgeprüft 12:43–12:44: die Spannungsmessung selbst ist in Ordnung

Weil HA über 17 Minuten Akkubetrieb unverändert `4.1` / `91.7` zeigte, wurde
geprüft, ob noch ein dritter Fehler dahintersteckt. Ergebnis: nein.

- Statusbits im Busspannungsregister: `CNVR=1`, `OVF=0` – jede Wandlung gültig,
  kein Überlauf.
- Die Spannung folgt der Last: 4,060 V bei 748–801 mA, 4,076 V bei 491 mA
  (Strom aus der Shunt-Spannung an 0,01 Ω). Das ergibt einen Innenwiderstand
  von rund 60 mΩ und eine Ruhespannung von rund 4,10 V.
- Vergleich mit dem baugleichen Board timbuktu am selben Tag: am PoE 4,172 V,
  bei 0,69 A 4,116 V (56 mV Einbruch, ~80 mΩ), in den ersten 40 Minuten nur
  auf 4,064 V gefallen.

Echte Werte 4,060–4,080 V ergeben mit `round(voltage, 1)` alle `4.1`. Die
Anzeige springt erst unter rund 4,05 V auf `4.0` / `83.3`. Behoben ist das mit
Punkt 2 oben.

---

## 2026-09-15, 13:50 – aus dem HA-Chat «SysMon»: Akkuwerte so liefern wie system_sensor auf timbuktu

**Auftrag von Roger.** Punkt 2 oben (Rundung) ist nicht nur ungenau, er macht
die Werte unbrauchbar: Nahe an einer Rundungsgrenze prellt die Anzeige.

### Belegt: Prellen zwischen zwei Rundungsstufen

HA-Board auf Akku (PoE aus seit 12:26). Erst nach rund einer Stunde fiel die
echte Spannung in die Nähe von 4,05 V – ab da sprangen beide Werte im Minutentakt
hin und her. Aus der HA-Historie, nur die Wechsel:

| Zeit | `bat_v` | `bat_percent` |
| :--- | :--- | :--- |
| bis 13:27 | 4.1 | 91.7 |
| 13:27:42 | 4.0 | 83.3 |
| 13:28:42 | 4.1 | 91.7 |
| 13:34:42 | 4.0 | 83.3 |
| 13:35:42 | 4.1 | 91.7 |
| 13:39:42 | 4.0 | 83.3 |
| 13:40:42 | 4.1 | 91.7 |
| 13:43:42 | 4.0 | 83.3 |
| 13:44:42 | 4.1 | 91.7 |
| 13:47:42 | 4.0 | 83.3 |

Zehn Wechsel in 20 Minuten, der Ladestand springt dabei jedes Mal um 8,4
Prozentpunkte. Die Spannung schwankt unter wechselnder Last ohnehin um
±15 mV (am Chip gemessen: 4,060 V bei 0,8 A, 4,076 V bei 0,5 A) – jede Stufe
der Rundung wird darum mehrfach überschritten, bevor der Akku sie endgültig
unterschreitet. Die Rundung glättet also nichts, sie verstärkt das Rauschen
auf 0,1 V bzw. 8,3 %.

### Ziel: dieselbe Datenqualität wie system_sensor

Referenz ist `~/repos/system_sensor` (läuft auf timbuktu, baugleiches Board,
derselbe INA219), beschrieben in dessen `docs/home-assistant.md` und
`docs/entscheidungen.md`, Abschnitt «Genauigkeit der Akkuwerte».

| Wert | system_sensor (Soll) | diese App (Ist) |
| :--- | :--- | :--- |
| `bat_v` | ungerundet, 3 Nachkommastellen (4 mV Auflösung des INA219) | auf 0,1 V gerundet (`usv_status.py` Z. 33) |
| `bat_percent` | aus der **ungerundeten** Spannung, 1 Nachkommastelle, linear 3,0 V = 0 % … 4,2 V = 100 % | aus der gerundeten Spannung → 8,3-%-Stufen |
| `bat_curr` | Kalibrierung 26868, 0,1 mA, **ohne Totband**, positiv = Entladen | Kalibrierung byte-vertauscht (Punkt 1), Werte unter 5 mA auf 0 gesetzt |
| `state_class` | `measurement` nur für Akkustrom (und Temperatur) | keine |

Konkret:

1. `usv_status.py` Z. 14: Kalibrierung richtig schreiben (Punkt 1 oben).
2. `usv_status.py` Z. 33: `return voltage` statt `round(voltage, 1)`. Die
   Nutzlast rundet in `system_sensors.py` Z. 156 bereits auf drei Stellen.
3. `usv_status.py` Totband entfernen (`if abs(current) < 5.0: return 0.0`) –
   system_sensor meldet am PoE ehrlich −1,1 mA. Ob HA «am Netz» erkennt,
   entscheidet dort eine eigene Grenze (100 mA), nicht die App.
4. Discovery für `bat_curr` mit `"state_class": "measurement"` senden.
5. **Nicht ändern:** `devicename` (`cm4_sys_mon`), die `unique_id`s
   (`cm4_sys_mon_bat_v`, `…_bat_percent`, `…_bat_curr`) und die Schlüssel der
   Nutzlast. Daran hängen in HA die Entity-IDs
   `sensor.ha_system_sensors_cm4_sys_mon_battery{,_voltage,_current}` – und an
   denen die SysMon-View, `custom_templates/usv.jinja`,
   `sensor.ha_usv_zustand` und die Abschaltautomation.

### Prüfen nach dem Einspielen

- Register 0x05 am Board zurücklesen: 0x68F4.
- In HA: Spannung mit drei Nachkommastellen, am PoE Strom nahe 0 bzw. leicht
  negativ, auf Akku Strom = Shunt-Spannung ÷ 0,01 Ω (heute ~0,5–0,8 A statt der
  gemeldeten 1,1–2,2 A).
- Die Versionsnummer an allen Stellen nachziehen (`config.yaml`, CHANGELOG,
  Tag) – Regel im globalen `CLAUDE.md`.

---

## 2026-09-15 – aus dem HA-Chat «SysMon»: Projektstand gegenüber system_sensor (unverbindlich)

**Auftrag von Roger:** unverbindlich ansehen, was beim Container
`~/repos/system_sensor` (Version 1.0.0/1.1.0 vom 2026-09-15) an Dokumentation,
Abhängigkeiten, Lizenz und Versionierung verbessert wurde, und was davon hier
fehlt. Nur gelesen, nichts geändert. Die installierte Kopie auf HA
(`/addons/cm4_sys_monitor/`) ist am 2026-09-15 identisch mit dem Repo – veraltet
ist das Projekt, nicht die Installation.

Vorbild zum Nachlesen: system_sensor `CHANGELOG.md` Abschnitt `[1.0.0]`,
`README.md`, `docs/`.

### Sicherheit – zuerst ansehen

- **Commit `66782b5` (2026-04-22, «Release v2.0.2»)**: In
  `cm4_sys_monitor/config.yaml` steht bei `password` ein 9-stelliger Wert, der
  keine Schema-Typangabe (`str`, `password?`) ist. Nicht angesehen. Roger prüft
  selbst: `git show 66782b5 -- cm4_sys_monitor/config.yaml`. Ist es ein echtes
  Passwort, hilft kein späterer Commit – das Repo ist öffentlich; dann das
  Passwort am Broker ändern. (`hostname` im selben Commit ist nur
  `core-mosquitto`.)
- Die App läuft auf HA mit `log_level: debug` (seit der Fehlersuche) und schreibt
  jede Minute die ganze Nutzlast ins Log. Nach Abschluss auf `info` zurück – das
  ist eine Einstellung in HA, nicht im Repo.
- `privileged: SYS_ADMIN` und Zugriff auf `/dev/i2c-*` – system_sensor nennt so
  etwas in einem Abschnitt «Haftung»; hier fehlt er.

### Dokumentation

| Thema | system_sensor | CM4 System Monitor |
| :--- | :--- | :--- |
| README | gegliedert: Problem, Lösung, was es leistet und was nicht, Aufbau, Schnellstart, Sensoren, Herkunft, Messwerte, Haftung, Lizenz | 62 Zeilen: Features, Voraussetzungen, Installation, Konfiguration, Logs, Lizenz |
| Vertiefung | `docs/installation.md`, `betrieb.md`, `home-assistant.md`, `entscheidungen.md` | keine |
| Messgenauigkeit | dokumentiert («Genauigkeit der Akkuwerte», Messtabelle PoE an/aus) | keine |
| Doku-Tab in HA | – (kein Add-on) | fehlt: kein `DOCS.md`, HA meldet `documentation: false` |

Konkrete Widersprüche im jetzigen README:

- Konfigurationstabelle nennt andere Vorgaben als `config.yaml`:
  `fanmaxtemp` **55** (config: 60), `low_bat_warning` **3.0** (config: 2.5).
  «Ein Wert, eine Stelle»: Vorgaben nur in `config.yaml`, das README verweist.
- `CHANGELOG [2.0.3]` führt die Rundung auf 0,1 V als Verbesserung und das
  5-mA-Totband als Fehlerbehebung – beides wird mit den Punkten oben
  zurückgenommen und muss dort als «Fixed» stehen.
- Home Assistant nennt Add-ons seit 2026.2 «Apps»; README und Beschreibung
  sprechen durchgehend von Add-ons.

### Abhängigkeiten

- `Dockerfile`: `FROM ghcr.io/home-assistant/${BUILD_ARCH}-base:latest` – das
  Basis-Image ist nicht festgelegt, jeder Neubau kann ein anderes ziehen. Üblich
  für HA-Apps ist ein `build.yaml` mit fester Base-Version; fehlt hier.
- `apk add python3 py3-paho-mqtt py3-yaml py3-smbus` ohne Versionen. Der Code
  nutzt `mqtt.Client(self.client_id)` – die Aufrufform von paho-mqtt 1.x.
  system_sensor ist auf paho-mqtt 2 mit Callback-API Version 2 umgestellt und
  begrenzt jede Abhängigkeit auf ihre Hauptversion
  (`paho-mqtt>=2.1,<3` usw.). Zu prüfen, welche paho-Version das Base-Image
  heute liefert.
- Uneinheitlich im selben Repo: `pv_wp_control` pinnt seine pip-Pakete fest
  (`paho-mqtt==1.6.1` …), die CM4-App gar nicht.

### Lizenz und Herkunft

- `LICENSE` (Repo-Wurzel) nennt nur «Copyright (c) 2026 Roger Widmer».
  `fan.py` verweist zweimal auf einen «Original-Code», `usv_status.py` folgt mit
  Kalibrierung 16 V/5 A und LSB 0,1524 mA erkennbar der INA219-Demo von Waveshare
  zum CM4-POE-UPS-BASE. Bei system_sensor war genau das der Fall: Der
  ursprüngliche MIT-Copyright-Hinweis war ersetzt worden und wurde in 1.0.0
  wiederhergestellt, dazu ein README-Abschnitt «Herkunft». Hier klären, woher
  `fan.py`, `usv_status.py` und `system_sensors.py` ursprünglich stammen, und die
  Hinweise ergänzen.

### Versionierung

- **Keine Git-Tags** im ganzen Repo – weder `2.0.3` (CM4) noch `1.0.11`
  (PV-WP). Nach der globalen Regel gehören Badge, CHANGELOG und Tag zusammen.
  Da das Repo zwei Apps mit eigenen Versionen enthält: Tags mit Präfix, z. B.
  `cm4_sys_monitor-v2.0.3`.
- `CHANGELOG.md`: kein Verweis auf Keep a Changelog / Semantic Versioning, kein
  `[Unreleased]`, keine Link-Fussnoten; Überschriften gemischt («Added» in 2.0.3,
  «Hinzugefügt» in 2.0.2); `[1.2.31]` ohne Datum.
- README-Badge `Version: 2.0.3` ohne Link.

### Home Assistant / MQTT

- Discovery ohne `default_entity_id`: Die Entity-IDs hängen am Anzeigenamen.
  system_sensor gibt sie fest vor.
- Keine Verfügbarkeit (`availability_topic` / Last Will): Fällt die App aus,
  hält HA die letzten Werte, statt `unavailable` zu zeigen.
- Gerät ohne `sw_version`; die Entitäten heissen englisch mit Gerätenamen
  («cm4_sys_mon Battery Voltage»). system_sensor: kurze deutsche Namen,
  Version als Firmware auf der Geräteseite, abgeschaltete Sensoren werden per
  leerer retained Nachricht aus HA entfernt.
- Bei allen Umbauten: `unique_id`s und `devicename` unverändert lassen (siehe
  Abschnitt oben), sonst brechen in HA View, Vorlagen und Abschaltautomation.

**Nachtrag 2026-09-15, 15:05 – Entwarnung zu «Sicherheit – zuerst ansehen»:**
Roger hat Commit `66782b5` angesehen. Der Wert bei `password` ist nur ein
Platzhalter, kein echtes Passwort. Kein Handlungsbedarf.

**Nachtrag 2026-09-15, 15:10 – Korrektur zu «Nach der Korrektur in HA»:** Der
Stromring der SysMon-View steht inzwischen fest auf ±2300 mA, weil der
Ladestrom nach dem Wiedereinschalten von PoE rund 2 A erreicht (timbuktu
−2226 mA). Nach der Korrektur der App ist dort **nichts** umzustellen.

---

## 2026-09-15 – aus dem Common-Chat: Repo-Konventionen entschieden

Betrifft den Abschnitt «Versionierung» oben. Die repo-weiten Regeln stehen
jetzt in `CLAUDE.md` im Repo-Wurzelordner, hier nur der Hinweis:

- **Tag-Schema ist `cm4_sys_monitor/v2.0.3`**, mit Schrägstrich wie im
  ESPHome-Repo – nicht `cm4_sys_monitor-v2.0.3`. Rückwirkend gesetzt für
  2.0.0 bis 2.0.3.
- Commit-Messages `cm4_sys_monitor: V2.0.4 – Kurzbeschreibung`.
- Neue CHANGELOG-Abschnitte nach Keep a Changelog mit deutschen Rubriken und
  Link-Fussnote `[2.0.4]: https://github.com/tsgwiro1/rwi_ha_apps/tree/cm4_sys_monitor/v2.0.4`.
- Die Widersprüche README ↔ `config.yaml` (`fanmaxtemp`, `low_bat_warning`)
  fallen unter die neue Regel «Ein Wert, eine Stelle»; ein Hook legt sie vor
  jedem Commit mit README, `config.yaml` oder Python-Code zur Prüfung vor.
- Diese Datei gehört ins Repo und wird von diesem Chat mit der App committet.

---

## 2026-09-15, 17:20 – Erledigt mit V2.0.4 (App-Chat)

Umgesetzt und auf HA eingespielt, Neubau 17:16:

- **Zwei Fehler in `usv_status.py`**, Punkte 1 und 2: Die Register werden
  jetzt mit dem höherwertigen Byte zuerst geschrieben. Die Spannung wird nicht
  mehr gerundet.
- **Akkuwerte wie system_sensor**, Punkte 1 bis 5: Das Totband ist entfernt,
  `bat_curr` sendet `state_class: measurement`. `devicename`, `unique_id`s und
  die Schlüssel der Nutzlast sind unverändert. Zusätzlich übernommen:
  INA219-Konfiguration `0x0EEF` wie system_sensor (Verstärkung /2, je 32
  Messungen).
- **Widersprüche README ↔ `config.yaml`**: Das README nennt keine Vorgaben mehr.
- Nebenbei behoben: Absturz beim Start in der Hysterese-Zone des Lüfters.
  Lesefehler werden als unbekannt statt als 0 gemeldet.

Geprüft nach dem Einspielen, am PoE:

| Prüfung | Ergebnis |
| :--- | :--- |
| Register 0x05 / 0x00 zurückgelesen | `0x68F4` / `0x0EEF` |
| Spannung in HA | `4.176` (vorher `4.2`) |
| Ladestand in HA | `98.0` (vorher `100`) |
| Strom in HA | −2,3 / −1,1 mA; Shunt −10 µV = −1 mA (vorher `0.0` durch das Totband) |
| `sensor.ha_usv_zustand` | bleibt `Netz` |
| Lüfter über 4 Durchläufe | App läuft, PWM folgt der CPU-Temperatur (46–49 °C) |

**Nachgeprüft 17:28 auf Akku** (PoE aus, Roger):

| Zeit | Shunt ÷ 0,01 Ω | Stromregister | Bus |
| :--- | :--- | :--- | :--- |
| 17:28:29 | 760,0 mA | 759,7 mA | 4,108 V |
| 17:28:30 | 571,0 mA | 570,9 mA | 4,120 V |
| 17:28:31 | 525,0 mA | 524,9 mA | 4,124 V |
| 17:28:33 | 718,0 mA | 717,8 mA | 4,112 V |

In HA ab 17:27:40: `bat_curr` 569.8, `bat_v` 4.124, `bat_percent` 93.7,
`sensor.ha_usv_zustand` `Akku`. Die Spannung folgt der Last in mV-Schritten,
statt auf `4.1` stehen zu bleiben. Mit v2.0.3 wären es 1280–1710 mA gewesen.

**Noch offen:** Die Punkte aus «Projektstand gegenüber system_sensor» (Doku,
Abhängigkeiten, Herkunft, Verfügbarkeit) folgen in V2.1.0 und einem
Doku-Commit.

---

## 2026-09-15, 17:55 – Entscheidungen für V2.1.0 (App-Chat, Roger)

Aus der Gesamtanalyse vom selben Tag, Phase 2:

1. **Abhängigkeiten:** venv mit pip, jede Abhängigkeit auf ihre Hauptversion
   begrenzt (`paho-mqtt>=2.1,<3`, `smbus2`), wie system_sensor. Der Code wird
   auf paho 2 mit Callback-API Version 2 umgestellt. Heute liefert das
   Base-Image paho 1.6.1 unter Alpine 3.23.3.
2. **Lüfter beim Beenden der App:** auf 100 % setzen.
3. **`low_bat_warning`:** offen, Erklärung angefragt.
4. **`cpu_temp`:** eigene Entität mit `state_class: measurement`.
5. **Herkunft `fan.py`:** Roger hält den Code für eigenen. Die Hinweise auf
   einen «Original-Code» stammen aus der ersten Fassung (d6f268c) und meinen
   vermutlich die eigenen Skripte von 1.2.31. Noch zu bestätigen.

Übrige Punkte für V2.1.0 laut Analyse:
- Optionen aus `/data/options.json` statt 16 Argumenten. Heute steht das
  Passwort in `ps`, und die Client-ID heisst `null`.
- Verfügbarkeit mit Last Will; Discovery erneut senden, wenn HA neu startet.
- `sw_version`, `default_entity_id`, abgeschaltete Sensoren aus HA entfernen.
- `translations/de.yaml`; Base-Image festlegen; `config.yaml` bereinigen
  (`device_tree`, `/dev/i2c-1`, `amd64`, `SYS_ADMIN` nur mit Test).

**Nachtrag 18:40 – entschieden (Roger):**
- **Zu 3, `low_bat_warning`:** Option und Warnung werden entfernt. Die Grenze für
  den Akkubetrieb steht nur in HA (`input_number.usv_abschalten_unter`).
- **Zu 4, `cpu_temp`:** doch weglassen, auch in der Nutzlast. Die CPU-Temperatur
  liefert die Integration System Monitor (`sensor.processor_temperature`), die
  App liefert nichts doppelt.
- **Zu 5, Herkunft:** `fan.py` ist eigener Code. `usv_status.py` bekommt einen
  Herkunftshinweis auf die INA219-Demo von Waveshare. Woher die alten Skripte
  von 1.2.31 im Einzelnen stammen, lässt sich nicht mehr nachvollziehen.

---

## 2026-09-15, 18:50 – V2.1.0 eingespielt und geprüft (App-Chat)

Neubau um 18:43, HA auf Akku seit 17:27.

| Prüfung | Ergebnis |
| :--- | :--- |
| Image, Pakete | Alpine 3.24.1, paho-mqtt 2.1.0, smbus2 0.6.1 im venv |
| Ohne `SYS_ADMIN` | Container nicht privilegiert, keine zusätzlichen Rechte; I2C funktioniert (Kalibrierung `0x68F4`, Konfiguration `0x0EEF`) |
| Prozessliste | `python3 /app/system_sensors.py` ohne Argumente, kein Passwort |
| `low_bat_warning` | Supervisor: «Option 'low_bat_warning' does not exist in the schema», verworfen; die App startet |
| Gerät in HA | Firmware 2.1.0; Name und Entitätsnamen aus HA unverändert |
| Übersetzungen | de und en geladen |
| Stopp um 18:43:50 | Log «Monitor wird beendet» und «Lüfter auf 100%»; EMC2301-Register 255, 8292 rpm; 4 Entitäten `unavailable`, `sensor.ha_usv_zustand` `unknown` |
| Start um 18:44:25 | Werte wieder da, USV `Akku`; Lüfter regelt über 3 Min. (Register 61→53 bei 45,8–46,3 °C) |
| Abschaltautomation | Auslöser `akku` um 18:45:25, `failed_conditions` (Ladestand 85 %) |

**Offen – kurzes Flackern beim Update:** Um 18:43:13 gingen die Entitäten für
etwa 30 ms auf `unavailable` und `sensor.ha_usv_zustand` auf `unknown`.
Ursache: `on_connect` sendet zuerst die Discovery, die jetzt ein
`availability_topic` enthält, und erst danach `online`. Das tritt nur auf, wenn
sich die Discovery ändert, also bei einem Update, nicht bei einem gewöhnlichen
Neustart. Behebung: `online` vor der Discovery senden.

**Nachtrag 19:00 – Flackern behoben:** `on_connect` sendet jetzt zuerst
`online`, dann die Discovery. Eingespielt als Neubau von 2.1.0 um 18:56. Beim
Stopp um 18:56:46 lief der Lüfter auf 100 %, und die Entitäten gingen
`unavailable`. Beim Start um 18:56:53 kamen die Werte direkt zurück, ohne
Zwischenstand. Der eigentliche Fall, eine geänderte Discovery, liess sich dabei
nicht nachstellen, weil die Discovery gleich blieb. Die Reihenfolge ist im
Offline-Test geprüft. Die Update-Anzeige in HA stand nach dem Update auf 2.1.0
auf «2.0.4 installiert». Das lag an HA Core, nicht an der App: Der Supervisor
meldete durchgehend 2.1.0. Um 19:00 zeigte HA wieder richtig `off`, 2.1.0.

---

## 2026-09-15, 19:15 – Doku nach system_sensor (App-Chat, ohne Versionssprung)

Erledigt aus «Projektstand gegenüber system_sensor», Abschnitte Dokumentation,
Lizenz und Herkunft sowie Versionierung:

- **README** neu gegliedert: Haftungsausschluss, Problem, Lösung, was die App
  leistet und was nicht, Aufbau, Installation, Sensoren, Dokumentation,
  Herkunft, Lizenz. «App» statt «Add-on». Keine Vorgabewerte.
- **`DOCS.md`** neu, erscheint in HA im Reiter Dokumentation: Funktionsprinzip,
  Optionen, Lüfterregelung, MQTT und Entitäten, Genauigkeit der Akkuwerte mit
  Messtabelle, Datenlast (gemessen), Fehlerbehebung, bekannte Punkte, Herkunft.
- **CHANGELOG**: Verweis auf Keep a Changelog und SemVer, `[Unreleased]`,
  deutsche Rubriken auch in 2.0.3, Link-Fussnoten für alle getaggten Versionen.
  Zurückgenommene Punkte aus 2.0.2 und 2.0.3 sind markiert.

Die Abhängigkeiten und HA/MQTT sind mit V2.1.0 erledigt. Damit ist der ganze
Abschnitt abgearbeitet. Hinweis: `default_entity_id` wirkt nur für neu angelegte
Entitäten. Die bestehenden Entity-IDs in HA bleiben, wie gewollt.

---

## 2026-09-15 – aus dem Chat pv_wp_control: Base-Image `base` statt `aarch64-base`

Bei der Plattform-Analyse für `pv_wp_control` gefunden. Kein Fehler, cm4 baut
und läuft; eine Empfehlung zur Angleichung.

Die HA-Entwicklerdoku (Apps → Configuration) sagt seit Supervisor 2026.04:
`BUILD_FROM` wird nicht mehr übergeben, `build.yaml` wird nicht mehr gelesen,
Base-Images direkt per `FROM` setzen, und zwar das Multi-Arch-Image
`ghcr.io/home-assistant/base` mit festem Tag. cm4 nutzt
`ghcr.io/home-assistant/aarch64-base:3.24` mit `ARG BUILD_ARCH`.

- Auf GHCR gibt es für beide Images dieselben Tags (`3.24`, `3.24-2026.06.0`,
  `3.24-2026.06.1`, `3.24-2026.08.0`); das gebaute cm4-Image trägt
  `io.hass.base.version=2026.08.0`, `alpine:3.24`.
- Umstellung: `FROM ghcr.io/home-assistant/base:3.24`, `ARG BUILD_ARCH`
  streichen. Inhaltlich dasselbe Image, also Patch-Version.
- `pv_wp_control` stellt in V1.3.0 genau so um (Dockerfile dort als Vergleich).

## 2026-09-15 – aus dem Chat pv_wp_control: relative Links in README/DOCS brechen in HA

Bei `pv_wp_control` im HA-Systemlog gefunden:
`Failed to to call /addons/LICENSE/info - App LICENSE does not exist`.
HA zeigt README bzw. DOCS im Reiter der App und behandelt relative Links als
App-Seiten – ein Klick auf `../LICENSE` ruft `/addons/LICENSE/info` auf.
`pv_wp_control` hat in V1.3.0 auf absolute GitHub-Links umgestellt
(`https://github.com/tsgwiro1/rwi_ha_apps/blob/main/…`).

In cm4 betroffen (Stand 2026-09-15):

- `README.md` Z. 3 und 141: `CHANGELOG.md`
- `README.md` Z. 4 und 152: `../LICENSE`
- `README.md` Z. 114: `../README.md#repository-in-home-assistant-hinzufügen`
- `README.md` Z. 118, 140: `DOCS.md`; Z. 148: `DOCS.md#9-herkunft`
- `DOCS.md` Z. 5: `README.md`; Z. 44: `config.yaml`

Reine Doku, Version bleibt.

---

## 2026-09-15 21:05 – Notiz cm4-Chat: beide Aufträge mit V2.1.1 erledigt

- **Base-Image:** `FROM ghcr.io/home-assistant/base:3.24`, ohne `ARG BUILD_ARCH`.
  Das gebaute Image trägt `alpine:3.24`, `io.hass.base.version=2026.08.0`,
  Alpine 3.24.1, paho-mqtt 2.1.0, smbus2 0.6.1 – wie unter 2.1.0.
- **Links:** Alle Links auf andere Dateien in README und DOCS zeigen auf GitHub
  (`blob/main`). Anker innerhalb derselben Seite bleiben relativ, wie bei
  `pv_wp_control`. Im Reiter der App geprüft.
- Die Links sind mit in V2.1.1 statt in einem eigenen Doku-Commit, weil das
  Badge ohnehin die neue Version bekam.
- **Test auf HA:** Update auf 2.1.1, Log sauber (INA219 `0x68f4`/`0x0eef`, MQTT
  verbunden), vier Entitäten mit Werten, Lüfter regelt nach dem Start
  (46,7 °C → Register 86). Die erste Drehzahl nach dem Update zeigt noch
  Volllast vom Stoppen (8273 rpm), die nächste 3070 rpm.
- Wie bei 2.1.0 hing die Update-Entität in HA Core nach dem Update noch auf der
  alten Version, der Supervisor meldete bereits 2.1.1.
