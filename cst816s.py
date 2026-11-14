"""Minimal CST816S capacitive touch driver (I2C addr 0x15)."""
import time

from gpiozero import DigitalOutputDevice
from smbus2 import SMBus

ADDR = 0x15


class CST816S:
    def __init__(self, bus=1, rst=17, flip_x=False, flip_y=False, swap_xy=False):
        self.flip_x, self.flip_y, self.swap_xy = flip_x, flip_y, swap_xy
        self.rst = DigitalOutputDevice(rst)
        self.rst.off(); time.sleep(0.01)
        self.rst.on(); time.sleep(0.05)
        self.bus = SMBus(bus)
        try:
            self.bus.write_byte_data(ADDR, 0xFE, 0x01)  # disable auto-sleep so polling keeps working
        except OSError:
            pass

    def read(self):
        """Return (x, y) if a finger is down, else None."""
        try:
            d = self.bus.read_i2c_block_data(ADDR, 0x01, 6)
        except OSError:
            return None
        if d[1] == 0:  # finger count
            return None
        x = ((d[2] & 0x0F) << 8) | d[3]
        y = ((d[4] & 0x0F) << 8) | d[5]
        if self.swap_xy:
            x, y = y, x
        if self.flip_x:
            x = 239 - x
        if self.flip_y:
            y = 239 - y
        return x, y

    def close(self):
        self.bus.close()
