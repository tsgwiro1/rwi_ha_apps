"""Zustandsmaschine für PV-WP-Steuerung."""

import time
from enum import Enum


class State(Enum):
    AUS = "AUS"
    WARTEN = "WARTEN"
    ANLAUF = "ANLAUF"
    BETRIEB = "BETRIEB"
    ABREGELUNG = "ABREGELUNG"
    ABSCHALT = "ABSCHALT"


class StateMachine:
    def __init__(self, config, log):
        self.config = config
        self.log = log
        self.state = State.AUS
        self.active_limit_w = 0

        # Timing
        self._anlauf_start = 0
        self._betrieb_start = 0
        self._abregelung_start = 0
        self._last_stop_time = 0
        self._cooldown_s = 0
        self._shutdown_delay_s = 0

        # Kompressor-Tracking
        self._kompressor_was_running = False

        # Betriebsart-Tracking
        self._last_betriebsart = None
        self._extern_override_logged = False

        # Log-Spam Vermeidung (nur 1x pro Minute)
        self._last_notaus_log = 0
        self._last_cooldown_log = 0
        self._last_insufficient_delta_log = 0
        self._last_ext_running_log = 0
        self._safety_logged = False

    # === Properties ===

    @property
    def runtime_min(self):
        """Laufzeit seit Anlauf in Minuten."""
        if self.state in (State.ANLAUF, State.BETRIEB, State.ABREGELUNG):
            return int((time.time() - self._anlauf_start) / 60)
        return 0

    @property
    def cooldown_remaining_min(self):
        """Verbleibende Standzeit in Minuten."""
        if self._cooldown_s <= 0 or self._last_stop_time == 0:
            return 0
        elapsed = time.time() - self._last_stop_time
        remaining = self._cooldown_s - elapsed
        return max(0, int(remaining / 60))

    @property
    def abregelung_remaining_min(self):
        """Verbleibende Ausschaltverzögerung in Minuten."""
        if self.state != State.ABREGELUNG:
            return 0
        if self._shutdown_delay_s <= 0:
            return 0
        elapsed = time.time() - self._abregelung_start
        remaining = self._shutdown_delay_s - elapsed
        return max(0, int(remaining / 60))

    # === Private Helpers ===

    def _cooldown_active(self):
        """Ist die Schaltspielsperre noch aktiv?"""
        if self._last_stop_time == 0:
            return False
        elapsed = time.time() - self._last_stop_time
        return elapsed < self._cooldown_s

    def _kompressor_running(self, modbus_data):
        """Prüfe ob Kompressor tatsächlich läuft (>300W)."""
        if modbus_data is None:
            return False
        leistung_kw = modbus_data.get('leistung_kw', 0)
        return leistung_kw > 0.3

    def _start_cooldown(self, reason):
        """Cooldown starten nach Kompressor-Stopp."""
        self._last_stop_time = time.time()
        self.active_limit_w = 0
        self.log.info(f"Cooldown gestartet ({int(self._cooldown_s/60)} min): {reason}")

    def _log_cooldown_once(self, msg):
        """Cooldown-Meldung nur 1x pro Minute."""
        now = time.time()
        if now - self._last_cooldown_log >= 60:
            self._last_cooldown_log = now
            self.log.info(msg)

    def _log_once(self, attr, msg):
        """Meldung nur 1x pro Minute (generisch)."""
        now = time.time()
        last = getattr(self, attr, 0)
        if now - last >= 60:
            setattr(self, attr, now)
            self.log.info(msg)

    # === Public Methods ===

    def transition_to_aus(self):
        """Übergang zu AUS nach expliziter Abschaltung (Reset gesendet)."""
        self.state = State.AUS
        self._start_cooldown("Reset gesendet")

    def evaluate(self, inputs):
        """State Machine evaluieren – wird alle 15s aufgerufen."""
        modbus = inputs.get('modbus')
        pv_surplus = inputs.get('pv_surplus') or 0
        params = inputs.get('params', {})
        safety_ok = inputs.get('safety_ok', True)
        safety_msg = inputs.get('safety_msg', '')
        modbus_connected = inputs.get('modbus_connected', False)

        mode = params.get('mode', 'Aus')
        min_surplus = params.get('min_surplus', 800)
        max_temp = params.get('max_temperature', 55.0)
        shutdown_delay = params.get('shutdown_delay', 30)
        min_standzeit = params.get('min_standzeit', 25)
        min_power = params.get('min_power', 600)
        offset = params.get('offset', 5.0)

        # Effective cooldown (max aus technischem und User-Wert)
        self._cooldown_s = max(self.config.wp_min_standzeit_min,
                               min_standzeit) * 60
        self._shutdown_delay_s = shutdown_delay * 60

        # Get values from Modbus
        rl_extern = modbus.get('rl_extern', 99) if modbus else 99
        leistung_w = (modbus.get('leistung_kw', 0) * 1000) if modbus else 0
        kompressor_laeuft = self._kompressor_running(modbus)
        betriebsart = modbus.get('betriebsart', 5) if modbus else 5

        # ============================================================
        # EXTERNE ÜBERSTEUERUNG ERKENNEN (während BETRIEB/ABREGELUNG)
        # ============================================================
        if self.state in (State.BETRIEB, State.ABREGELUNG):
            if betriebsart == 1 and not self._extern_override_logged:
                self.log.warning(
                    f"Externe Übersteuerung: WP wechselt auf Warmwasser! "
                    f"PV-Steuerung pausiert bis WW fertig.")
                self._extern_override_logged = True
            elif betriebsart in (3, 4) and not self._extern_override_logged:
                ba_name = {3: "EVU-Sperre", 4: "Abtauen"}.get(
                    betriebsart, f"Modus {betriebsart}")
                self.log.warning(
                    f"Externe Übersteuerung: WP wechselt auf {ba_name}! "
                    f"PV-Steuerung pausiert.")
                self._extern_override_logged = True
            elif betriebsart in (0, 6):
                if self._extern_override_logged:
                    self.log.info(
                        f"Externe Übersteuerung beendet. "
                        f"WP zurück im Heiz-Modus. PV-Steuerung aktiv.")
                    self._extern_override_logged = False

        if self.state not in (State.BETRIEB, State.ABREGELUNG):
            self._extern_override_logged = False

        # ============================================================
        # KOMPRESSOR-ÜBERWACHUNG
        # ============================================================

        # Kompressor WAR an und ist JETZT aus → extern gestoppt
        if self._kompressor_was_running and not kompressor_laeuft:
            if self.state in (State.BETRIEB, State.ABREGELUNG):
                self.log.warning(
                    f"Kompressor extern gestoppt! "
                    f"Leistung={leistung_w:.0f}W, RL_ext={rl_extern:.1f}°C, "
                    f"Betriebsart={betriebsart}. → WARTEN (Cooldown)")
                self.state = State.WARTEN
                self._start_cooldown("Kompressor extern gestoppt")
                self._kompressor_was_running = False
                return

        # Kompressor war AUS und ist JETZT an → extern gestartet
        if not self._kompressor_was_running and kompressor_laeuft:
            if self.state in (State.AUS, State.WARTEN):
                self.log.info(
                    f"Kompressor extern gestartet! "
                    f"Leistung={leistung_w:.0f}W, Betriebsart={betriebsart}.")

        # Update Tracking
        self._kompressor_was_running = kompressor_laeuft

        # ============================================================
        # SAFETY OVERRIDE
        # ============================================================
        if not safety_ok:
            if self.state in (State.ANLAUF, State.BETRIEB, State.ABREGELUNG):
                self.log.error(f"SAFETY: {safety_msg} → ABSCHALT")
                self.state = State.ABSCHALT
                return
            else:
                # Nur einmal loggen (nicht wiederholt)
                if not self._safety_logged:
                    self.log.warning(f"SAFETY: {safety_msg} (kein Start möglich)")
                    self._safety_logged = True
                return
        else:
            # Safety wieder ok → Reset Flag
            if self._safety_logged:
                self.log.info("SAFETY: Temperatur wieder im Normalbereich")
                self._safety_logged = False

        # ============================================================
        # MODE = AUS → Sofort abschalten
        # ============================================================
        if mode == 'Aus':
            if self.state in (State.ANLAUF, State.BETRIEB, State.ABREGELUNG):
                self.log.info("Mode → Aus: ABSCHALT eingeleitet")
                self.state = State.ABSCHALT
            elif self.state == State.WARTEN:
                self.log.info("Mode → Aus")
                self.state = State.AUS
            return

        # ============================================================
        # STATE TRANSITIONS
        # ============================================================

        if self.state == State.AUS:
            if mode == 'Sofort':
                if self._cooldown_active():
                    self._log_cooldown_once(
                        f"Sofort: Cooldown noch {self.cooldown_remaining_min} min")
                elif rl_extern >= max_temp:
                    self._log_once('_last_insufficient_delta_log',
                        f"Sofort: Max Temperatur erreicht "
                        f"({rl_extern:.1f}°C >= {max_temp:.1f}°C)")
                elif kompressor_laeuft:
                    self._log_once('_last_ext_running_log',
                        f"Sofort: Kompressor läuft extern "
                        f"(Betriebsart={betriebsart}). Warte bis frei.")
                else:
                    self.log.info("Mode=Sofort → ANLAUF")
                    self.state = State.ANLAUF
                    self._anlauf_start = time.time()
            elif mode == 'PV Überschuss':
                self.log.info("Mode=PV Überschuss → WARTEN")
                self.state = State.WARTEN

        # ----------------------------------------------------------
        elif self.state == State.WARTEN:
            # Cooldown aktiv?
            if self._cooldown_active():
                self._log_cooldown_once(
                    f"WARTEN: Cooldown noch {self.cooldown_remaining_min} min")
                return

            # Speicher voll?
            if rl_extern >= max_temp:
                self._log_once('_last_insufficient_delta_log',
                    f"WARTEN: Speicher voll "
                    f"({rl_extern:.1f}°C >= {max_temp:.1f}°C)")
                return

            # Modbus nicht verbunden?
            if not modbus_connected:
                self.log.debug("WARTEN: Kein Modbus")
                return

            # Genug Delta?
            available_delta = max_temp - rl_extern
            if available_delta < offset:
                self._log_once('_last_insufficient_delta_log',
                    f"WARTEN: Kein Start - zu wenig Spielraum. "
                    f"Delta={available_delta:.1f}K < Offset={offset:.1f}K "
                    f"(RL_ext={rl_extern:.1f}°C, Max={max_temp:.1f}°C)")
                return

            # Kompressor läuft extern?
            if kompressor_laeuft:
                if betriebsart == 1:
                    # Warmwasser → nicht stören
                    self._log_once('_last_ext_running_log',
                        f"WARTEN: WP im Warmwasser-Modus "
                        f"(Leistung={leistung_w:.0f}W). Warte bis fertig.")
                    return

                elif betriebsart in (0, 6):
                    # Heiz-Modus → übernehmen wenn unser Limit höher
                    if mode == 'Sofort':
                        our_limit = 10000
                    else:
                        our_limit = max(int(pv_surplus), min_power)

                    if our_limit >= leistung_w:
                        self.log.info(
                            f"WP heizt extern ({leistung_w:.0f}W). "
                            f"Unser Limit={our_limit}W >= aktuelle Leistung "
                            f"→ ÜBERNEHME (direkt BETRIEB)")
                        self.state = State.BETRIEB
                        self._betrieb_start = time.time()
                        self._anlauf_start = time.time()
                        self._kompressor_was_running = True
                        self.active_limit_w = our_limit
                        return
                    else:
                        self._log_once('_last_ext_running_log',
                            f"WARTEN: WP heizt extern ({leistung_w:.0f}W). "
                            f"Unser Limit={our_limit}W zu tief → warte.")
                        return

                else:
                    # Abtauen, EVU-Sperre, etc.
                    self._log_once('_last_ext_running_log',
                        f"WARTEN: WP in Betriebsart {betriebsart} "
                        f"(Leistung={leistung_w:.0f}W). Warte.")
                    return

            # === Alle Bedingungen erfüllt → Start ===
            if mode == 'Sofort':
                self.log.info("Sofort → ANLAUF")
                self.state = State.ANLAUF
                self._anlauf_start = time.time()
            elif pv_surplus >= min_surplus:
                self.log.info(
                    f"Start: PV={pv_surplus}W >= {min_surplus}W, "
                    f"RL_ext={rl_extern:.1f}°C, "
                    f"Delta={available_delta:.1f}K → ANLAUF")
                self.state = State.ANLAUF
                self._anlauf_start = time.time()

        # ----------------------------------------------------------
        elif self.state == State.ANLAUF:
            elapsed = time.time() - self._anlauf_start

            if kompressor_laeuft:
                self.log.info(
                    f"Kompressor gestartet! "
                    f"Leistung={leistung_w:.0f}W nach {int(elapsed)}s → BETRIEB")
                self.state = State.BETRIEB
                self._betrieb_start = time.time()
            elif elapsed > self.config.startup_no_limit_s:
                self.log.error(
                    f"ANLAUF FEHLGESCHLAGEN: Kompressor nicht gestartet "
                    f"nach {int(elapsed)}s. "
                    f"Leistung={leistung_w:.0f}W (erwartet >300W). "
                    f"Mögliche Ursachen: WP-interne Schaltspielsperre, "
                    f"Störung, EVU-Sperre. → ABSCHALT")
                self.state = State.ABSCHALT

        # ----------------------------------------------------------
        elif self.state == State.BETRIEB:
            # Max Temperatur?
            if rl_extern >= max_temp:
                self.log.info(
                    f"Max Temperatur erreicht: "
                    f"{rl_extern:.1f}°C >= {max_temp:.1f}°C → ABSCHALT")
                self.state = State.ABSCHALT
                return

            # PV unter Minimum? (nur im PV-Modus)
            if mode == 'PV Überschuss' and pv_surplus < min_surplus:
                self.state = State.ABREGELUNG
                self._abregelung_start = time.time()
                self.log.info(
                    f"PV unter Minimum: {pv_surplus}W < {min_surplus}W "
                    f"→ ABREGELUNG (Verzögerung {shutdown_delay} min)")

            # Limit nachführen
            if mode == 'Sofort':
                self.active_limit_w = 10000
            else:
                self.active_limit_w = max(int(pv_surplus), min_power)

        # ----------------------------------------------------------
        elif self.state == State.ABREGELUNG:
            elapsed_min = (time.time() - self._abregelung_start) / 60

            # Max Temperatur?
            if rl_extern >= max_temp:
                self.log.info(
                    f"Max Temperatur in ABREGELUNG: "
                    f"{rl_extern:.1f}°C >= {max_temp:.1f}°C → ABSCHALT")
                self.state = State.ABSCHALT
                return

            # PV erholt?
            if pv_surplus >= min_surplus:
                self.log.info(
                    f"PV erholt: {pv_surplus}W >= {min_surplus}W "
                    f"(nach {elapsed_min:.1f} min) → BETRIEB")
                self.state = State.BETRIEB
                return

            # Timer abgelaufen?
            if elapsed_min >= shutdown_delay:
                self.log.info(
                    f"Ausschaltverzögerung abgelaufen "
                    f"({shutdown_delay} min) → ABSCHALT")
                self.state = State.ABSCHALT
                return

            # Limit nachführen (PV oder Minimum)
            self.active_limit_w = max(int(pv_surplus), min_power)

        # ----------------------------------------------------------
        elif self.state == State.ABSCHALT:
            # Reset wird im main loop gesendet
            pass
