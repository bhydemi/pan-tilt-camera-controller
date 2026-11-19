from machine import ADC, Pin, Timer


class Joystick:
    # ESP32 ADC readings run 0-4095; treat the middle band around the
    # center value as "no movement" so small analog jitter is ignored.
    CENTER = 2047
    DEADZONE = 1200

    LEFT = "L"
    RIGHT = "R"
    UP = "U"
    DOWN = "D"
    MIDDLE = "M"

    _MODES = ("polling", "interrupt")

    def __init__(self, xAxis: int, yAxis: int, mode: str = "polling"):
        if mode not in self._MODES:
            raise ValueError("mode must be one of {}".format(self._MODES))

        self.x_axis = ADC(Pin(xAxis))
        self.x_axis.atten(ADC.ATTN_11DB)

        self.y_axis = ADC(Pin(yAxis))
        self.y_axis.atten(ADC.ATTN_11DB)

        self.mode = mode
        self._state = self.MIDDLE
        self._timer = None

        if self.mode == "interrupt":
            self._timer = Timer(0)
            self._timer.init(period=100, mode=Timer.PERIODIC, callback=self._on_timer)

    # Timer callback: runs on every tick when in interrupt mode and
    # refreshes the cached joystick reading in the background.
    def _on_timer(self, timer):
        self._state = self._sample()

    def _sample(self):
        dx = self.x_axis.read() - self.CENTER
        dy = self.y_axis.read() - self.CENTER

        if abs(dx) < self.DEADZONE and abs(dy) < self.DEADZONE:
            return self.MIDDLE

        # A diagonal push deflects both axes past the dead zone at once;
        # report whichever axis moved further so the dominant direction
        # wins instead of always favoring the horizontal axis.
        if abs(dx) >= abs(dy):
            return self.LEFT if dx < 0 else self.RIGHT
        return self.DOWN if dy < 0 else self.UP

    # Returns 'M' if the joystick is in the middle, or 'L', 'R', 'U', 'D'
    # if it is pushed left, right, up or down. In polling mode this reads
    # the ADC pins directly; in interrupt mode it returns the last value
    # captured by the timer callback.
    def read(self):
        if self.mode == "interrupt":
            return self._state
        return self._sample()
