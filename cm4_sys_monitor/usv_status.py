import smbus

class INA219:
    def __init__(self, bus=10, addr=0x43):
        self.bus = smbus.SMBus(bus)
        self.addr = addr
        # Kalibrierung für 16V / 5A (Werte aus deinem alten Code)
        self.bus.write_word_data(self.addr, 0x05, 0x68EC) # 26868 in hex (lsb swapped für smbus)
        # Config: 16V Range, Gain /2, 12-bit 32 samples
        self.bus.write_word_data(self.addr, 0x00, 0x3907) # 0x0739 swapped

    def get_bus_voltage(self):
        # Register 0x02: Bus Voltage
        raw = self.bus.read_word_data(self.addr, 0x02)
        # Swap bytes und schiebe um 3 Bits (INA219 Spezifikation)
        val = ((raw << 8) & 0xFF00) | (raw >> 8)
        return (val >> 3) * 0.004

    def get_current(self):
        # Register 0x04: Current
        raw = self.bus.read_word_data(self.addr, 0x04)
        val = ((raw << 8) & 0xFF00) | (raw >> 8)
        if val > 32767: val -= 65535
        return val * 0.1524