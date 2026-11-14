# Round Touch Display (Raspberry Pi 5 + GC9A01 1.28")

A simple touch UI with 3 screens for the 240×240 round GC9A01 LCD with CST816S touch
(e.g. the Waveshare 1.28" Touch LCD).

- **Clock**: time, date and a ring that counts the seconds
- **System**: CPU load, CPU temperature and RAM use
- **Brightness**: tap – / + to change the backlight

**Swipe left/right** to change screens. The dots at the bottom show which screen you're on.

## Wiring

| Display | Pi 5 pin (GPIO) |
|---------|-----------------|
| VCC     | 3.3V (pin 1)    |
| GND     | GND (pin 6)     |
| DIN/MOSI| GPIO10 (pin 19) |
| CLK/SCK | GPIO11 (pin 23) |
| CS      | GPIO8 / CE0 (pin 24) |
| DC      | GPIO25 (pin 22) |
| RST     | GPIO27 (pin 13) |
| BL      | GPIO18 (pin 12) |
| TP_SDA  | GPIO2 (pin 3)   |
| TP_SCL  | GPIO3 (pin 5)   |
| TP_RST  | GPIO17 (pin 11) |
| TP_INT  | GPIO4 (pin 7), optional, not used |

If you wire it differently, change the pin numbers in `GC9A01(...)` and `CST816S(...)` in `app.py`.

## Setup (Raspberry Pi OS Bookworm)

```bash
sudo raspi-config nonint do_spi 0     # enable SPI
sudo raspi-config nonint do_i2c 0     # enable I2C
sudo apt install -y python3-spidev python3-smbus2 python3-pil python3-numpy python3-gpiozero python3-lgpio fonts-dejavu-core
sudo reboot
```

Check that the touch chip shows up at `15`: `i2cdetect -y 1`. It may only appear after you touch the screen.

## Run

```bash
python3 app.py
```

### Start on boot

```bash
sudo cp round-display.service /etc/systemd/system/
sudo sed -i "s|/home/pi/round-display|$PWD|; s|User=pi|User=$USER|" /etc/systemd/system/round-display.service
sudo systemctl enable --now round-display
```

## Troubleshooting

- **Image is mirrored or rotated:** change `rotation=` (0/90/180/270) in `app.py`.
- **Taps land in the wrong place:** set `flip_x`, `flip_y` or `swap_xy` on `CST816S(...)`.
- **Colours look inverted:** remove the `0x21` line in `gc9a01.py`.
- **Garbled image:** lower `speed_hz` in `gc9a01.py` (for example to `20_000_000`) and keep the SPI wires short.

## Adding a screen

Subclass `Screen` in `app.py`, write `draw(self, d)`, and optionally `tap(self, x, y)`, then add
it to the `screens` list.
