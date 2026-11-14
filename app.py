#!/usr/bin/env python3
"""Round touchscreen UI for Raspberry Pi 5 + GC9A01 + CST816S.

Swipe left/right to change screens. Tap to interact.
"""
import time
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from cst816s import CST816S
from gc9a01 import GC9A01

W = H = 240
CX = CY = 120
BG = (10, 12, 20)
FG = (235, 238, 245)
DIM = (90, 96, 115)
ACCENT = (64, 156, 255)
WARN = (255, 140, 60)

# Touch tuning
SWIPE_MIN = 50   # px of horizontal travel to count as a swipe
TAP_MAX = 20     # px of travel allowed for a tap
POLL = 0.02      # s between touch polls


def font(size, bold=True):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)
    except OSError:
        return ImageFont.load_default(size=size)


F_HUGE, F_BIG, F_MED, F_SMALL = font(56), font(36), font(22), font(14, bold=False)


def ring(d, frac, color, width=10, inset=6):
    box = (inset, inset, W - inset, H - inset)
    d.arc(box, 0, 360, fill=(30, 34, 48), width=width)
    if frac > 0:
        d.arc(box, -90, -90 + 360 * min(frac, 1.0), fill=color, width=width)


def text(d, xy, s, f, fill=FG):
    d.text(xy, s, font=f, fill=fill, anchor="mm")


# ---------------------------------------------------------------- screens
class Screen:
    interval = 1.0  # seconds between automatic redraws

    def draw(self, d): ...

    def tap(self, x, y):
        return False  # return True if a redraw is needed


class ClockScreen(Screen):
    interval = 0.5

    def draw(self, d):
        now = datetime.now()
        ring(d, now.second / 60, ACCENT, width=6, inset=4)
        text(d, (CX, CY - 10), now.strftime("%H:%M"), F_HUGE)
        text(d, (CX, CY + 40), now.strftime("%a %d %b"), F_MED, DIM)


class StatsScreen(Screen):
    interval = 2.0

    def __init__(self):
        self._prev = self._cpu_times()

    @staticmethod
    def _cpu_times():
        with open("/proc/stat") as f:
            v = list(map(int, f.readline().split()[1:]))
        idle = v[3] + v[4]
        return idle, sum(v)

    def _cpu(self):
        idle, total = self._cpu_times()
        pi, pt = self._prev
        self._prev = (idle, total)
        dt = total - pt
        return 0.0 if dt == 0 else 1 - (idle - pi) / dt

    @staticmethod
    def _temp():
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return int(f.read()) / 1000
        except OSError:
            return 0.0

    @staticmethod
    def _mem():
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":")
                info[k] = int(v.split()[0])
        return 1 - info["MemAvailable"] / info["MemTotal"]

    def draw(self, d):
        cpu, temp, mem = self._cpu(), self._temp(), self._mem()
        ring(d, cpu, WARN if cpu > 0.8 else ACCENT)
        text(d, (CX, 62), "CPU", F_SMALL, DIM)
        text(d, (CX, 92), f"{cpu * 100:.0f}%", F_BIG)
        text(d, (CX - 45, 140), "TEMP", F_SMALL, DIM)
        text(d, (CX - 45, 162), f"{temp:.0f}°", F_MED, WARN if temp > 70 else FG)
        text(d, (CX + 45, 140), "RAM", F_SMALL, DIM)
        text(d, (CX + 45, 162), f"{mem * 100:.0f}%", F_MED)


class BrightnessScreen(Screen):
    interval = 60

    def __init__(self, lcd):
        self.lcd = lcd
        self.level = 10  # 1..10

    def draw(self, d):
        ring(d, self.level / 10, ACCENT)
        text(d, (CX, 60), "BRIGHTNESS", F_SMALL, DIM)
        text(d, (CX, CY), f"{self.level * 10}%", F_BIG)
        for cx, sym in ((75, "-"), (165, "+")):
            d.ellipse((cx - 26, CY + 24, cx + 26, CY + 76), outline=ACCENT, width=3)
            text(d, (cx, CY + 48), sym, F_BIG, ACCENT)

    def tap(self, x, y):
        if y < CY + 10:
            return False
        self.level = max(1, self.level - 1) if x < CX else min(10, self.level + 1)
        self.lcd.brightness(self.level / 10)
        return True


# ---------------------------------------------------------------- main loop
def main():
    lcd = GC9A01(rotation=0)
    touch = CST816S()  # set flip_x/flip_y/swap_xy here if taps land in the wrong spot
    screens = [ClockScreen(), StatsScreen(), BrightnessScreen(lcd)]
    idx = 0
    dirty = True
    last_draw = 0.0
    start = last = None

    try:
        while True:
            # --- input
            p = touch.read()
            if p and start is None:
                start = last = p
            elif p:
                last = p
            elif start is not None:  # finger lifted
                dx, dy = last[0] - start[0], last[1] - start[1]
                if abs(dx) > SWIPE_MIN and abs(dx) > abs(dy):
                    idx = (idx + (1 if dx < 0 else -1)) % len(screens)
                    dirty = True
                elif abs(dx) < TAP_MAX and abs(dy) < TAP_MAX:
                    dirty |= screens[idx].tap(*start)
                start = last = None

            # --- render
            now = time.monotonic()
            if dirty or now - last_draw >= screens[idx].interval:
                img = Image.new("RGB", (W, H), BG)
                d = ImageDraw.Draw(img)
                screens[idx].draw(d)
                for i in range(len(screens)):  # page dots
                    x = CX + (i - (len(screens) - 1) / 2) * 14
                    d.ellipse((x - 3, 218, x + 3, 224), fill=FG if i == idx else DIM)
                lcd.show(img)
                last_draw, dirty = now, False

            time.sleep(POLL)
    except KeyboardInterrupt:
        pass
    finally:
        lcd.close()
        touch.close()


if __name__ == "__main__":
    main()
