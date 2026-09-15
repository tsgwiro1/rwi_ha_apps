# Treiber für den INA219, der den Akku des Waveshare CM4-POE-UPS-BASE misst.
#
# Herkunft: Kalibrierung, Strom-LSB und Umrechnung stammen aus der INA219-Demo
# von Waveshare zum Board, https://www.waveshare.com/wiki/CM4-POE-UPS-BASE

from smbus2 import SMBus
import logging

logger = logging.getLogger("usv_driver")

# Register des INA219
REG_CONFIG = 0x00
REG_BUSVOLTAGE = 0x02
REG_CURRENT = 0x04
REG_CALIBRATION = 0x05

# Kalibrierung für 16 V / 5 A an einem Shunt von 0,01 Ohm (Waveshare-Demo zum CM4-POE-UPS-BASE)
CALIBRATION = 26868
CURRENT_LSB_MA = 0.1524
BUS_VOLTAGE_LSB_V = 0.004

# Config: 16V Range, Gain /2 (80 mV), Bus- und Shunt-ADC 12 Bit mit 32 Samples, Continuous Mode
CONFIG = (0x0 << 13) | (0x1 << 11) | (0xD << 7) | (0xD << 3) | 0x7  # = 0x0EEF


class INA219:
    def __init__(self, bus, addr):
        self.addr = addr
        try:
            self.bus = SMBus(bus)
            self._write(REG_CALIBRATION, CALIBRATION)
            self._write(REG_CONFIG, CONFIG)
            logger.info(f"INA219 initialisiert (Kalibrierung: {self._read(REG_CALIBRATION):#06x}, "
                        f"Konfiguration: {self._read(REG_CONFIG):#06x})")
        except Exception as e:
            logger.error(f"Fehler bei der Initialisierung des INA219: {e}")
            self.bus = None

    def _read(self, reg):
        # Der INA219 sendet das höherwertige Byte zuerst
        data = self.bus.read_i2c_block_data(self.addr, reg, 2)
        return (data[0] << 8) | data[1]

    def _write(self, reg, value):
        # Höherwertiges Byte zuerst; write_word_data würde das niedere zuerst senden
        self.bus.write_i2c_block_data(self.addr, reg, [value >> 8, value & 0xFF])

    def _ensure_calibration(self):
        """Setzt Kalibrierung und Konfiguration neu, falls der Chip zurückgesetzt wurde."""
        cal = self._read(REG_CALIBRATION)
        if cal != CALIBRATION:
            logger.warning(f"INA219 Kalibrierung {cal:#06x} statt {CALIBRATION:#06x} gelesen – setze neu.")
            self._write(REG_CALIBRATION, CALIBRATION)
            self._write(REG_CONFIG, CONFIG)

    def get_bus_voltage(self):
        """Busspannung in V, None bei einem Lesefehler."""
        if not self.bus: return None
        try:
            self._ensure_calibration()
            # Die Spannung steht in den oberen 13 Bits
            return (self._read(REG_BUSVOLTAGE) >> 3) * BUS_VOLTAGE_LSB_V
        except Exception as e:
            logger.error(f"Fehler beim Auslesen der Bus-Spannung: {e}")
            return None

    def get_current(self):
        """Akkustrom in mA, positiv beim Entladen; None bei einem Lesefehler."""
        if not self.bus: return None
        try:
            self._ensure_calibration()
            val = self._read(REG_CURRENT)
            if val > 32767: val -= 65536
            return val * CURRENT_LSB_MA
        except Exception as e:
            logger.error(f"Fehler beim Auslesen des Stroms: {e}")
            return None
