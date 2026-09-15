#!/usr/bin/with-contenv bashio

APP_VERSION=$(bashio::addon.version)
export APP_VERSION

bashio::log.info "Starte CM4 System Monitor v${APP_VERSION}..."

# Die Optionen liest das Programm selbst aus /data/options.json.
# exec, damit das Signal beim Stoppen direkt beim Programm ankommt.
exec /opt/venv/bin/python3 /app/system_sensors.py
