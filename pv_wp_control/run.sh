#!/usr/bin/with-contenv bashio

bashio::log.info "Starte PV-WP-Control..."

# Die Optionen liest das Programm selbst aus /data/options.json.
# exec, damit das Signal beim Stoppen direkt beim Programm ankommt.
exec python3 /app/main.py
