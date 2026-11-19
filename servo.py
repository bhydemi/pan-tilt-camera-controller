from machine import Pin, PWM


class Servo:
    def __init__(self, pin: int, min=550, max=2400, freq=50):
        self.min = min
        self.max = max
        self.angle = 90

        self.pwm = PWM(Pin(pin))
        self.pwm.freq(freq)
        self._period_us = 1000000 // freq

        self.goto(self.angle)

    # Converts an angle (0-180) into the duty cycle needed for a 16-bit
    # PWM signal at the configured frequency, mapped between the servo's
    # min/max pulse widths.
    def _duty_for_angle(self, angle):
        pulse_us = self.min + (self.max - self.min) * angle / 180
        return int(pulse_us * 65535 / self._period_us)

    # Move the servo to the requested angle (clamped to 0-180).
    def goto(self, angle):
        self.angle = max(0, min(180, angle))
        self.pwm.duty_u16(self._duty_for_angle(self.angle))

    # Move the servo to the left, the requested amount of degrees.
    def left(self, angle):
        self.goto(self.angle - angle)

    # Move the servo to the right, the requested amount of degrees.
    def right(self, angle):
        self.goto(self.angle + angle)
