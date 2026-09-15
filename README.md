# RWI Home Assistant Apps

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-App-41bdf5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)

Selbst entwickelte Apps für Home Assistant, zugeschnitten auf die eigene
Hardware und Haustechnik. Home Assistant nennt Add-ons seit Version 2026.2
«Apps»; gemeint ist dasselbe.

---

## ⚠️ Haftungsausschluss (Disclaimer)

Alle Inhalte dieses Repositorys sind private Projekte. Die Verwendung erfolgt
ausdrücklich **auf eigene Gefahr**. Es wird keinerlei Haftung für Schäden an
Geräten, Haustechnik oder Daten übernommen. Die Apps greifen direkt auf
Hardware zu – I²C-Bus des Rechners, Modbus der Wärmepumpe – und laufen dafür
teils mit erweiterten Rechten.

---

## Repository in Home Assistant hinzufügen

1. In Home Assistant **Einstellungen → Apps** öffnen und in den App-Store
   wechseln.
2. Oben rechts über die drei Punkte (⋮) **Repositories** wählen.
3. Diese Adresse eintragen: `https://github.com/tsgwiro1/rwi_ha_apps`
4. Hinzufügen und die Seite neu laden. Die Apps erscheinen im Store unter dem
   Namen dieses Repositorys.

---

## Repository-Struktur

Monorepo: Jede App hat ihren eigenen Ordner mit README, CHANGELOG und eigener
Version.

| Ordner / App | Kurzbeschreibung | Status / Version |
| :--- | :--- | :--- |
| [**`cm4_sys_monitor`**](./cm4_sys_monitor) | Überwachung eines Raspberry Pi Compute Module 4 auf dem Waveshare CM4-POE-UPS-BASE. Liest Akkuspannung und -strom über den INA219, steuert den Lüfter temperaturabhängig über den EMC2301 und legt alle Werte per MQTT-Discovery als Entitäten in Home Assistant an. | v2.1.0 (Aktiv) |
| [**`pv_wp_control`**](./pv_wp_control) | PV-Überschusssteuerung für eine Alpha-Innotec-Wärmepumpe (Luxtronik 2.1) über Modbus TCP. Startet die Wärmepumpe bei Solarüberschuss, führt die Leistungsbegrenzung dem Überschuss nach, erkennt fremde Starts und Stopps (Warmwasser, Abtauen, EVU-Sperre) und stellt Sensoren und Bedienelemente per MQTT-Discovery bereit. | v1.0.12 (Aktiv) |

---

## Lizenz

Alle Apps stehen unter der [MIT-Lizenz](LICENSE), sofern im jeweiligen Ordner
nicht anders angegeben.
