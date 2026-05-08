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

        # Safety
        self._safety_logged = False

        # Reset-Flag + Verifizierung
        self._reset_required = False
        self._reset_sent_time = 0
        self._reset_verified = True

        # Fehlstart-Tracking
        self._failed_starts = 0

        # PV-Hysterese (ABREGELUNG → BETRIEB)
        self._pv_recovered_count = 0

        # Start-Hysterese (WARTEN → ANLAUF)
        self._pv_start_time = 0
        self._min_start_duration_s = 600

        # Abregelungs-Tracking (für Zusammenfassung)
        self._abregelung_count = 0
        self._abregelung_total_s = 0
        self._abregelung_current_start = 0

        # Logging-Optimierung
        self._wait_reason = None
        self._wait_reason_time = 0
        self._heartbeat_interval = 3600
        self._cooldown_logged = False

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

    @property
    def pv_stable_remaining_min(self):
        """Verbleibende Zeit bis Start-Hysterese erfüllt."""
        if self.state != State.WARTEN or self._pv_start_time == 0:
            return 0
        elapsed = time.time() - self._pv_start_time
        remaining = self._min_start_duration_s - elapsed
        return max(0, int(remaining / 60))

    @property
    def reset_required(self):
        """Einmaliger Reset-Trigger. Wird nach Abfrage zurückgesetzt."""
        if self._reset_required:
            self._reset_required = False
            return True
        return False

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

    def _request_reset(self, reason):
        """Reset anfordern – Register müssen zurückgesetzt werden."""
        self._reset_required = True
        self._reset_sent_time = time.time()
        self._reset_verified = False
        self.log.info(f"Reset angefordert: {reason}")

    def _start_cooldown(self, reason):
        """Cooldown starten nach Kompressor-Stopp."""
        self._last_stop_time = time.time()
        self.active_limit_w = 0
        self._cooldown_logged = False

    def _log_wait(self, reason, details):
        """WARTEN-Log: Grund-Wechsel auf INFO, Heartbeat auf DEBUG."""
        now = time.time()
        if reason != self._wait_reason:
            self.log.info(f"WARTEN: {reason} ({details})")
            self._wait_reason = reason
            self._wait_reason_time = now
        elif now - self._wait_reason_time >= self._heartbeat_interval:
            self.log.debug(f"WARTEN: (weiterhin) {reason} ({details})")
            self._wait_reason_time = now

    def _log_betrieb_summary(self):
        """Zusammenfassung des Betriebszyklus loggen."""
        runtime = self.runtime_min
        if self._abregelung_count > 0:
            if self._abregelung_current_start > 0:
                self._abregelung_total_s += (
                    time.time() - self._abregelung_current_start)
            abregel_min = int(self._abregelung_total_s / 60)
            self.log.info(
                f"Zyklus-Ende: Laufzeit={runtime} min, "
                f"Abregelungen={self._abregelung_count} "
                f"(total {abregel_min} min)")
        else:
            self.log.info(f"Zyklus-Ende: Laufzeit={runtime} min")

    def _reset_betrieb_tracking(self):
        """Reset aller Betriebszyklus-Tracker."""
        self._abregelung_count = 0
        self._abregelung_total_s = 0
        self._abregelung_current_start = 0

    def _reset_wait_logging(self):
        """Reset Wait-Logging bei State-Wechsel."""
        self._wait_reason = None
        self._wait_reason_time = 0
        self._cooldown_logged = False
        self._pv_recovered_count = 0
        self._pv_start_time = 0

    # === Public Methods ===

    def transition_to_aus(self):
        """Übergang zu AUS nach expliziter Abschaltung (Reset gesendet)."""
        self.state = State.AUS
        self._start_cooldown("Reset gesendet")
        self._reset_wait_logging()
        self._reset_betrieb_tracking()
        # Verifizierung starten: Kompressor muss nach Reset stoppen
        self._reset_sent_time = time.time()
        self._reset_verified = False

    def evaluate(self, inputs):
        """State Machine evaluieren – wird alle 15s aufgerufen."""
        modbus = inputs.get('modbus')
        pv_surplus = inputs.get('pv_surplus') or 0
        battery_soc = inputs.get('battery_soc')
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
        min_start_duration = params.get('min_start_duration', 10)
        min_battery_soc = params.get('min_battery_soc', 0)

        # Start-Hysterese Dauer in Sekunden
        self._min_start_duration_s = min_start_duration * 60

        # Effective cooldown (max aus technischem und User-Wert)
        base_cooldown = max(self.config.wp_min_standzeit_min,
                            min_standzeit) * 60
        multiplier = min(self._failed_starts + 1, 3)
        self._cooldown_s = base_cooldown * multiplier
        self._shutdown_delay_s = shutdown_delay * 60

        # Get values from Modbus
        rl_extern = modbus.get('rl_extern', 99) if modbus else 99
        leistung_w = (modbus.get('leistung_kw', 0) * 1000) if modbus else 0
        kompressor_laeuft = self._kompressor_running(modbus)
        betriebsart = modbus.get('betriebsart', 5) if modbus else 5

        # ============================================================
        # RESET-VERIFIZIERUNG (Kompressor muss nach Reset stoppen)
        # ============================================================
        if not self._reset_verified and self._reset_sent_time > 0:
            elapsed = time.time() - self._reset_sent_time
            if elapsed > 120:
                if kompressor_laeuft:
                    self.log.warning(
                        f"Reset-Verifizierung: Kompressor läuft noch "
                        f"{int(elapsed)}s nach Reset! "
                        f"Leistung={leistung_w:.0f}W, "
                        f"Betriebsart={betriebsart}")
                else:
                    self.log.debug(
                        "Reset-Verifizierung OK: Kompressor gestoppt")
                self._reset_verified = True

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
                self._log_betrieb_summary()
                self.log.warning(
                    f"Kompressor extern gestoppt! "
                    f"Leistung={leistung_w:.0f}W, RL_ext={rl_extern:.1f}°C, "
                    f"Betriebsart={betriebsart}. → WARTEN (Cooldown)")
                self._request_reset("Kompressor extern gestoppt")
                self.state = State.WARTEN
                self._start_cooldown("Kompressor extern gestoppt")
                self._kompressor_was_running = False
                self._reset_wait_logging()
                self._reset_betrieb_tracking()
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
                self.log.critical(f"NOTAUS: {safety_msg} → ABSCHALT")
                self.state = State.ABSCHALT
                return
            else:
                if not self._safety_logged:
                    self.log.warning(
                        f"SAFETY: {safety_msg} (kein Start möglich)")
                    self._safety_logged = True
                return
        else:
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
                self._request_reset("Mode=Aus (defensiv)")
                self.log.info("Mode → Aus")
                self.state = State.AUS
                self._reset_wait_logging()
            return

        # ============================================================
        # STATE TRANSITIONS
        # ============================================================

        if self.state == State.AUS:
            if mode == 'Sofort':
                if self._cooldown_active():
                    self._log_wait("Cooldown",
                        f"noch {self.cooldown_remaining_min} min")
                elif rl_extern >= max_temp:
                    self._log_wait("Max Temperatur",
                        f"{rl_extern:.1f}°C >= {max_temp:.1f}°C")
                elif kompressor_laeuft:
                    self._log_wait("Kompressor extern",
                        f"Betriebsart={betriebsart}, warte bis frei")
                elif betriebsart in (3, 4):
                    ba_name = {3: "EVU-Sperre", 4: "Abtauen"}.get(
                        betriebsart, f"Modus {betriebsart}")
                    self._log_wait(f"{ba_name} aktiv",
                        "kein Start möglich, warte auf Freigabe")
                else:
                    self.log.info("Mode=Sofort → ANLAUF")
                    self.state = State.ANLAUF
                    self._anlauf_start = time.time()
                    self._reset_wait_logging()
                    self._reset_betrieb_tracking()
            elif mode == 'PV Überschuss':
                self.log.info("Mode=PV Überschuss → WARTEN")
                self.state = State.WARTEN
                self._reset_wait_logging()

        # ----------------------------------------------------------
        elif self.state == State.WARTEN:
            # Cooldown aktiv?
            if self._cooldown_active():
                if not self._cooldown_logged:
                    cooldown_min = int(self._cooldown_s / 60)
                    if self._failed_starts > 0:
                        self.log.info(
                            f"WARTEN: Cooldown aktiv "
                            f"({cooldown_min} min, "
                            f"nach {self._failed_starts} Fehlstart(s))")
                    else:
                        self.log.info(
                            f"WARTEN: Cooldown aktiv ({cooldown_min} min)")
                    self._cooldown_logged = True
                return

            # Cooldown gerade abgelaufen?
            if self._cooldown_logged:
                self.log.info("WARTEN: Cooldown beendet")
                self._cooldown_logged = False
                self._wait_reason = None

            # Modbus nicht verbunden? (PRIORITÄT vor Speicher-voll!)
            if not modbus_connected:
                self._log_wait("Kein Modbus", "warte auf Verbindung")
                self._pv_start_time = 0
                return

            # EVU-Sperre / Abtauen? (Kompressor steht, WP blockiert)
            if not kompressor_laeuft and betriebsart in (3, 4):
                ba_name = {3: "EVU-Sperre", 4: "Abtauen"}.get(
                    betriebsart, f"Modus {betriebsart}")
                self._log_wait(f"{ba_name} aktiv",
                    "kein Start möglich, warte auf Freigabe")
                self._pv_start_time = 0
                return

            # Speicher voll?
            if rl_extern >= max_temp:
                self._log_wait("Speicher voll",
                    f"{rl_extern:.1f}°C >= {max_temp:.1f}°C")
                self._pv_start_time = 0
                return

            # Genug Delta?
            available_delta = max_temp - rl_extern
            if available_delta < offset:
                self._log_wait("Zu wenig Spielraum",
                    f"Delta={available_delta:.1f}K < Offset={offset:.1f}K, "
                    f"RL_ext={rl_extern:.1f}°C")
                self._pv_start_time = 0
                return

            # Batterie-SOC zu tief?
            if min_battery_soc > 0 and battery_soc is not None:
                if battery_soc < min_battery_soc:
                    self._log_wait("Batterie zu tief",
                        f"SOC={battery_soc}% < {min_battery_soc}%")
                    self._pv_start_time = 0
                    return

            # Kompressor läuft extern?
            if kompressor_laeuft:
                if betriebsart == 1:
                    self._log_wait("WP im Warmwasser-Modus",
                        f"Leistung={leistung_w:.0f}W, warte bis fertig")
                    self._pv_start_time = 0
                    return

                elif betriebsart in (0, 6):
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
                        self._failed_starts = 0
                        self._reset_wait_logging()
                        self._reset_betrieb_tracking()
                        return
                    else:
                        self._log_wait("WP extern, Limit zu tief",
                            f"WP={leistung_w:.0f}W, unser Limit={our_limit}W")
                        self._pv_start_time = 0
                        return

                else:
                    self._log_wait(f"WP in Betriebsart {betriebsart}",
                        f"Leistung={leistung_w:.0f}W, warte")
                    self._pv_start_time = 0
                    return

            # === Alle Grundbedingungen erfüllt → PV prüfen ===
            if mode == 'Sofort':
                self.log.info("Sofort → ANLAUF")
                self.state = State.ANLAUF
                self._anlauf_start = time.time()
                self._reset_wait_logging()
                self._reset_betrieb_tracking()

            elif pv_surplus >= min_surplus:
                # Start-Hysterese: PV muss min_start_duration stabil sein
                if self._pv_start_time == 0:
                    self._pv_start_time = time.time()
                    self.log.info(
                        f"WARTEN: PV={pv_surplus:.0f}W >= {min_surplus}W "
                        f"– Stabilisierung läuft "
                        f"({min_start_duration} min)")

                elapsed = time.time() - self._pv_start_time
                if elapsed >= self._min_start_duration_s:
                    self.log.info(
                        f"Start: PV={pv_surplus:.0f}W >= {min_surplus}W "
                        f"(stabil seit {int(elapsed/60)} min), "
                        f"RL_ext={rl_extern:.1f}°C, "
                        f"Delta={available_delta:.1f}K → ANLAUF")
                    self.state = State.ANLAUF
                    self._anlauf_start = time.time()
                    self._reset_wait_logging()
                    self._reset_betrieb_tracking()
            else:
                if self._pv_start_time != 0:
                    self.log.debug(
                        f"WARTEN: PV-Stabilisierung abgebrochen "
                        f"(PV={pv_surplus:.0f}W < {min_surplus}W)")
                    self._pv_start_time = 0
                self._log_wait("PV zu tief",
                    f"{pv_surplus:.0f}W < {min_surplus}W")

        # ----------------------------------------------------------
        elif self.state == State.ANLAUF:
            elapsed = time.time() - self._anlauf_start

            if kompressor_laeuft:
                self.log.info(
                    f"Kompressor gestartet! "
                    f"Leistung={leistung_w:.0f}W nach {int(elapsed)}s → BETRIEB")
                self.state = State.BETRIEB
                self._betrieb_start = time.time()
                self._failed_starts = 0
            elif elapsed > self.config.startup_no_limit_s:
                self._failed_starts += 1
                next_cooldown_min = int(
                    self._cooldown_s * min(self._failed_starts + 1, 3) / 60)
                self.log.error(
                    f"ANLAUF FEHLGESCHLAGEN: Kompressor nicht gestartet "
                    f"nach {int(elapsed)}s. "
                    f"Leistung={leistung_w:.0f}W (erwartet >300W). "
                    f"Fehlstarts={self._failed_starts}, "
                    f"nächster Cooldown={next_cooldown_min} min. "
                    f"Mögliche Ursachen: WP-interne Schaltspielsperre, "
                    f"Störung, EVU-Sperre. → ABSCHALT")
                self.state = State.ABSCHALT

        # ----------------------------------------------------------
        elif self.state == State.BETRIEB:
            # Max Temperatur?
            if rl_extern >= max_temp:
                self._log_betrieb_summary()
                self.log.info(
                    f"Max Temperatur erreicht: "
                    f"{rl_extern:.1f}°C >= {max_temp:.1f}°C → ABSCHALT")
                self.state = State.ABSCHALT
                return

            # PV unter Minimum? (nur im PV-Modus)
            if mode == 'PV Überschuss' and pv_surplus < min_surplus:
                self.state = State.ABREGELUNG
                self._abregelung_start = time.time()
                self._abregelung_current_start = time.time()
                self._abregelung_count += 1
                self._pv_recovered_count = 0
                if self._abregelung_count == 1:
                    self.log.info(
                        f"PV unter Minimum: {pv_surplus}W < {min_surplus}W "
                        f"→ ABREGELUNG (Verzögerung {shutdown_delay} min)")
                else:
                    self.log.debug(
                        f"PV unter Minimum: {pv_surplus}W < {min_surplus}W "
                        f"→ ABREGELUNG (#{self._abregelung_count})")

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
                self._log_betrieb_summary()
                self.log.info(
                    f"Max Temperatur in ABREGELUNG: "
                    f"{rl_extern:.1f}°C >= {max_temp:.1f}°C → ABSCHALT")
                self.state = State.ABSCHALT
                return

            # PV erholt? (mit Hysterese: 2 Zyklen = 30s stabil)
            if pv_surplus >= min_surplus:
                self._pv_recovered_count += 1
                if self._pv_recovered_count >= 2:
                    if self._abregelung_current_start > 0:
                        self._abregelung_total_s += (
                            time.time() - self._abregelung_current_start)
                        self._abregelung_current_start = 0
                    self.log.debug(
                        f"PV erholt: {pv_surplus}W >= {min_surplus}W "
                        f"(nach {elapsed_min:.1f} min) → BETRIEB")
                    self.state = State.BETRIEB
                    self._pv_recovered_count = 0
                    return
            else:
                self._pv_recovered_count = 0

            # Timer abgelaufen?
            if elapsed_min >= shutdown_delay:
                self._log_betrieb_summary()
                self.log.info(
                    f"Ausschaltverzögerung abgelaufen "
                    f"({shutdown_delay} min) → ABSCHALT")
                self.state = State.ABSCHALT
                return

            # Limit nachführen (PV oder Minimum)
            self.active_limit_w = max(int(pv_surplus), min_power)

        # ----------------------------------------------------------
        elif self.state == State.ABSCHALT:
            pass
