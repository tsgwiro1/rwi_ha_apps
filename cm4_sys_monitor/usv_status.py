import smbus
import logging

logger = logging.getLogger("usv_driver")

class INA219:
    def __init__(self, bus=10, addr=0x43, low_bat_warning=3.0):
        self.addr = addr
        self.low_bat_warning = low_bat_warning
        try:
            self.bus = smbus.SMBus(bus)
            # Kalibrierung für 16V / 5A (Werte aus deinem alten Code)
            self.bus.write_word_data(self.addr, 0x05, 0x68EC) # 26868 in hex (lsb swapped für smbus)
            # Config: 16V Range, Gain /2, 12-bit 32 samples
            self.bus.write_word_data(self.addr, 0x00, 0x3907) # 0x0739 swapped
        except Exception as e:
            logger.error(f"Fehler bei der Initialisierung des INA219: {e}")
            self.bus = None

    def get_bus_voltage(self):
        if not self.bus: return 0.0
        try:
            # Register 0x02: Bus Voltage
            raw = self.bus.read_word_data(self.addr, 0x02)
            # Swap bytes und schiebe um 3 Bits (INA219 Spezifikation)
            val = ((raw << 8) & 0xFF00) | (raw >> 8)
            voltage = (val >> 3) * 0.004
            
            if voltage < self.low_bat_warning:
                logger.warning(f"Kritische Batteriespannung detektiert: {voltage:.2f}V! (Schwelle: {self.low_bat_warning}V)")
                
            return voltage
        except Exception as e:
            logger.error(f"Fehler beim Auslesen der Bus-Spannung: {e}")
            return 0.0

    def get_current(self):
        if not self.bus: return 0.0
        try:
            # Register 0x04: Current
            raw = self.bus.read_word_data(self.addr, 0x04)
            val = ((raw << 8) & 0xFF00) | (raw >> 8)
            if val > 32767: val -= 65535
            return val * 0.1524
        except Exception as e:
            logger.error(f"Fehler beim Auslesen des Stroms: {e}")
            return 0.0