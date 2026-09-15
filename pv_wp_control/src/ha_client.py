"""Home Assistant REST API Client."""

import time
import requests

from config import HA_URL

# Timeout je Abfrage an die HA-API
HTTP_TIMEOUT_S = 5
# Solange HA nicht erreichbar ist, so oft ein Lebenszeichen im Log
LEBENSZEICHEN_S = 300


class HAClient:
    def __init__(self, config, log):
        self.config = config
        self.log = log
        self._last_value = None
        self._last_battery_soc = None
        self._last_success = time.time()
        self._consecutive_errors = 0
        self._unavailable_since = None
        self._last_lebenszeichen = 0

    def is_connected(self):
        """Prüfe ob HA-Daten aktuell sind."""
        elapsed = time.time() - self._last_success
        timeout = self.config.ha_connection_timeout_min * 60
        return elapsed < timeout

    def _handle_api_error(self, context, status_code=None, exception=None):
        """Zentrale Fehlerbehandlung mit Eskalations-Logik."""
        self._consecutive_errors += 1
        now = time.time()

        if self._unavailable_since is None:
            self._unavailable_since = now
            self._last_lebenszeichen = now

        if self._consecutive_errors == 1:
            # Erste Meldung als WARNING
            if status_code:
                self.log.warning(
                    f"HA nicht erreichbar (HTTP {status_code}) "
                    f"– warte auf Verfügbarkeit...")
            else:
                self.log.warning(
                    f"HA nicht erreichbar ({exception}) "
                    f"– warte auf Verfügbarkeit...")
        elif now - self._last_lebenszeichen >= LEBENSZEICHEN_S:
            self._last_lebenszeichen = now
            elapsed = int((now - self._unavailable_since) / 60)
            self.log.info(
                f"HA weiterhin nicht erreichbar seit {elapsed} min "
                f"(Errors: {self._consecutive_errors})")
        else:
            self.log.debug(
                f"HA API Fehler ({context}): "
                f"{status_code or exception} "
                f"(Errors: {self._consecutive_errors})")

    def _handle_api_success(self):
        """Recovery-Meldung nach Fehlern."""
        if self._consecutive_errors > 0:
            elapsed = int((time.time() - self._unavailable_since) / 60)
            self.log.info(
                f"HA wieder erreichbar nach {elapsed} min "
                f"({self._consecutive_errors} Fehler)")
        self._consecutive_errors = 0
        self._unavailable_since = None
        self._last_success = time.time()

    def get_pv_surplus(self):
        """PV Überschuss aus HA Entity lesen."""
        entity_id = self.config.ha_entity_pv_surplus
        url = f"{HA_URL}/states/{entity_id}"

        headers = {
            'Authorization': f'Bearer {self.config.ha_token}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_S)

            if response.status_code == 200:
                data = response.json()
                state = data.get('state', 'unavailable')

                if state in ('unavailable', 'unknown', 'None'):
                    self.log.debug(f"HA Entity {entity_id} = {state}")
                    return self._last_value

                value = float(state)
                self._last_value = value
                self._handle_api_success()
                return value

            else:
                self._handle_api_error("PV", status_code=response.status_code)
                return self._last_value

        except requests.exceptions.ConnectionError:
            self._handle_api_error("PV", exception="ConnectionError")
            return self._last_value

        except (ValueError, TypeError) as e:
            self.log.warning(f"HA Entity Wert ungültig: {e}")
            return self._last_value

        except Exception as e:
            self._handle_api_error("PV", exception=e)
            return self._last_value

    def get_battery_soc(self):
        """Batterie-SOC aus HA Entity lesen. Gibt int (0-100) oder None."""
        entity_id = self.config.ha_entity_battery_soc
        if not entity_id:
            return None

        url = f"{HA_URL}/states/{entity_id}"

        headers = {
            'Authorization': f'Bearer {self.config.ha_token}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_S)

            if response.status_code == 200:
                data = response.json()
                state = data.get('state', 'unavailable')

                if state in ('unavailable', 'unknown', 'None'):
                    self.log.debug(f"HA Entity {entity_id} = {state}")
                    return self._last_battery_soc

                value = int(float(state))
                self._last_battery_soc = value
                # Kein _handle_api_success() hier – wird bereits in get_pv_surplus() gemacht
                return value

            else:
                self._handle_api_error("SOC", status_code=response.status_code)
                return self._last_battery_soc

        except (ValueError, TypeError) as e:
            self.log.warning(
                f"HA Battery SOC Wert ungültig: {e} "
                f"(Entity: {entity_id})")
            return self._last_battery_soc

        except Exception as e:
            self._handle_api_error("SOC", exception=e)
            return self._last_battery_soc
