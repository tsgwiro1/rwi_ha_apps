"""Modbus TCP Client für Alpha Innotec Wärmepumpe."""

from pymodbus.client import ModbusTcpClient
import time


class ModbusClient:
    def __init__(self, config, log):
        self.config = config
        self.log = log
        self.client = None
        self._connected = False
        self._last_connect_attempt = 0
        self._connect()

    def _connect(self):
        try:
            self.client = ModbusTcpClient(
                self.config.wp_ip,
                port=self.config.wp_port,
                timeout=5
            )
            if self.client.connect():
                self._connected = True
                self.log.info(f"Modbus verbunden: {self.config.wp_ip}:{self.config.wp_port}")
            else:
                self._connected = False
                self.log.error("Modbus Verbindung fehlgeschlagen")
        except Exception as e:
            self._connected = False
            self.log.error(f"Modbus Fehler: {e}")

    def is_connected(self):
        return self._connected

    def _ensure_connected(self):
        if not self._connected:
            now = time.time()
            if now - self._last_connect_attempt >= self.config.modbus_retry_delay_s:
                self._last_connect_attempt = now
                self.log.info("Modbus Reconnect...")
                self._connect()
        return self._connected

    def disconnect(self):
        if self.client:
            self.client.close()
            self._connected = False

    def _read_input_register(self, address):
        try:
            r = self.client.read_input_registers(address, 1,
                                                  slave=self.config.wp_slave_id)
            if not r.isError():
                return r.registers[0]
        except Exception as e:
            self.log.debug(f"Modbus read IR{address} Fehler: {e}")
        return None

    def _read_input_register_signed(self, address):
        val = self._read_input_register(address)
        if val is not None and val > 32767:
            val -= 65536
        return val

    def read_all(self):
        if not self._ensure_connected():
            return None

        try:
            data = {}

            # RL extern (Speicherfühler) - IR10102
            val = self._read_input_register_signed(10102)
            data['rl_extern'] = val / 10 if val is not None else None

            # RL SOLL - IR10101
            val = self._read_input_register(10101)
            data['rl_soll'] = val / 10 if val is not None else None

            # RL IST - IR10100
            val = self._read_input_register(10100)
            data['rl_ist'] = val / 10 if val is not None else None

            # Vorlauf IST - IR10105
            val = self._read_input_register(10105)
            data['vl_ist'] = val / 10 if val is not None else None

            # Leistungsaufnahme - IR10301
            val = self._read_input_register(10301)
            data['leistung_kw'] = val / 10 if val is not None else 0

            # Heizleistung - IR10300
            val = self._read_input_register_signed(10300)
            data['heizleistung_kw'] = val / 10 if val is not None else 0

            # Betriebsart - IR10002
            val = self._read_input_register(10002)
            data['betriebsart'] = val if val is not None else 5

            # WP Status - IR10000
            val = self._read_input_register(10000)
            data['wp_status'] = val if val is not None else 0
            data['wp_running'] = bool(val & 1) if val is not None else False

            # Status Heizen - IR10003
            val = self._read_input_register(10003)
            data['status_heizen'] = val if val is not None else 0

            # COP berechnen
            if data['leistung_kw'] and data['leistung_kw'] > 0.2:
                data['cop'] = data['heizleistung_kw'] / data['leistung_kw']
            else:
                data['cop'] = 0

            # Validate
            if data['rl_extern'] is None:
                self.log.warning("Modbus: RL extern konnte nicht gelesen werden")
                self._connected = False
                return None

            return data

        except Exception as e:
            self.log.error(f"Modbus read_all Fehler: {e}")
            self._connected = False
            return None

    def write_fixwert(self, fixwert_celsius):
        """Fixwert OHNE Limit setzen (für Anlaufphase)."""
        if not self._ensure_connected():
            return False

        try:
            fixwert_reg = int(fixwert_celsius * 10)

            self.client.write_register(10065, 0, slave=self.config.wp_slave_id)
            time.sleep(1.0)
            self.client.write_register(10000, 1, slave=self.config.wp_slave_id)
            time.sleep(1.0)
            self.client.write_register(10001, fixwert_reg,
                                       slave=self.config.wp_slave_id)
            time.sleep(1.0)

            # Verify
            r = self.client.read_input_registers(10101, 1,
                                                 slave=self.config.wp_slave_id)
            if r and not r.isError():
                actual_soll = r.registers[0] / 10
                self.log.info(f"Modbus write verify: SOLL={actual_soll:.1f}°C "
                             f"(erwartet ~{fixwert_celsius:.1f}°C)")
                if actual_soll < 25:
                    self.log.warning("SOLL nicht übernommen!")
                    return False

            self.log.debug(f"Modbus write: Fixwert={fixwert_celsius:.1f}°C "
                          f"(HR10001={fixwert_reg}), KEIN Limit")
            return True

        except Exception as e:
            self.log.error(f"Modbus write_fixwert Fehler: {e}")
            self._connected = False
            return False

    def write_fixwert_with_limit(self, fixwert_celsius, limit_w):
        """Fixwert MIT Soft Limit setzen (für Betrieb)."""
        if not self._ensure_connected():
            return False

        try:
            fixwert_reg = int(fixwert_celsius * 10)
            limit_reg = int(limit_w / 100)

            if limit_reg < 1:
                limit_reg = 1

            self.client.write_register(10065, 0, slave=self.config.wp_slave_id)
            time.sleep(1.0)
            self.client.write_register(10000, 1, slave=self.config.wp_slave_id)
            time.sleep(1.0)
            self.client.write_register(10001, fixwert_reg,
                                       slave=self.config.wp_slave_id)
            time.sleep(1.0)
            self.client.write_register(10040, 1, slave=self.config.wp_slave_id)
            time.sleep(1.0)
            self.client.write_register(10041, limit_reg,
                                       slave=self.config.wp_slave_id)

            self.log.debug(f"Modbus write: Fixwert={fixwert_celsius:.1f}°C "
                          f"Limit={limit_w}W (HR10041={limit_reg})")
            return True

        except Exception as e:
            self.log.error(f"Modbus write_fixwert_with_limit Fehler: {e}")
            self._connected = False
            return False

    def write_reset(self):
        """Alle Register auf Default zurücksetzen."""
        if not self._ensure_connected():
            return False

        try:
            self.client.write_register(10000, 0, slave=self.config.wp_slave_id)
            time.sleep(1.0)
            self.client.write_register(10001, 0, slave=self.config.wp_slave_id)
            time.sleep(1.0)
            self.client.write_register(10040, 0, slave=self.config.wp_slave_id)
            time.sleep(1.0)
            self.client.write_register(10041, 300, slave=self.config.wp_slave_id)
            time.sleep(1.0)
            self.client.write_register(10065, 0, slave=self.config.wp_slave_id)

            self.log.info("Modbus Reset: Alle Register auf Default")
            return True

        except Exception as e:
            self.log.error(f"Modbus write_reset Fehler: {e}")
            self._connected = False
            return False
