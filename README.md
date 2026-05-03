# 🛠️ RWI Home Assistant Add-ons

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Willkommen in meinem benutzerdefinierten Home Assistant Add-on Repository. Hier sammle und pflege ich selbst entwickelte Erweiterungen (Apps/Add-ons) für Home Assistant, die auf spezielle Hardware-Setups oder Automatisierungsbedürfnisse zugeschnitten sind.

## 📦 Repository in Home Assistant hinzufügen

Um die Add-ons aus diesem Repository in deinem Home Assistant zu nutzen, musst du diese URL als neue Quelle hinzufügen:

1. Gehe in Home Assistant zu **Einstellungen** -> **Add-ons**.
2. Klicke unten rechts auf den Button **Add-on Store**.
3. Klicke oben rechts auf die drei Punkte (⋮) und wähle **Repositories**.
4. Füge die URL dieses Repositories ein:
   `https://github.com/tsgwiro1/rwi_ha_apps`
5. Klicke auf **Hinzufügen** und lade die Seite neu. Die neuen Add-ons erscheinen nun ganz unten im Store.

---

## 🚀 Verfügbare Add-ons

Hier ist eine Übersicht der aktuell verfügbaren Add-ons in diesem Repository. Klicke auf den jeweiligen Namen, um zur ausführlichen Dokumentation zu gelangen.

### [🖥️ CM4 System Monitor](./cm4_sys_monitor)
Ein ressourcenschonendes, natives Add-on zur Überwachung eines Raspberry Pi Compute Module 4 (CM4) mit passendem IO-Board (z. B. Waveshare CM4-POE-UPS-BASE). 
* **USV-Überwachung:** Liest Spannung (V) und Strom (mA) über den I2C-Bus (INA219 Chip) aus.
* **Lüftersteuerung:** Steuert den angeschlossenen Lüfter temperaturgesteuert (EMC2301 Chip).
* **Auto-Discovery:** Alle Werte werden vollautomatisch als Entitäten via MQTT im Home Assistant angelegt.

---

### [☀️ PV Wärmepumpen Steuerung](./pv_wp_control)
Ein intelligentes Add-on zur PV-Überschusssteuerung einer Alpha Innotec Wärmepumpe (Luxtronik 2.1) über Modbus TCP.
* **PV-Überschusssteuerung:** Startet die Wärmepumpe automatisch bei Solarüberschuss und lädt den Kombispeicher über den Heizbetrieb.
* **Leistungsbegrenzung:** Dynamisches Soft Limit folgt dem PV-Überschuss in Echtzeit.
* **Kompressor-Überwachung:** Erkennt externe Starts/Stopps (Warmwasser, Abtauen, EVU-Sperre) und reagiert intelligent.
* **Auto-Discovery:** Alle Sensoren und Steuerelemente werden vollautomatisch als Entitäten via MQTT im Home Assistant angelegt.

---

## 📄 Lizenz

Alle Add-ons in diesem Repository stehen unter der [MIT-Lizenz](LICENSE), sofern im jeweiligen Unterordner nicht anders angegeben. Du kannst den Code gerne für deine eigenen Projekte nutzen, anpassen und weiterentwickeln.
