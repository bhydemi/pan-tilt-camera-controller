# Pan & Tilt Camera Controller (ESP32 + MicroPython + Wokwi)

By Abdulhakeem Omotolani Yaqoob

Dual-camera pan/tilt controller. A slide switch picks which camera (and its
LED indicator) is active, a joystick drives that camera's pan/tilt servos,
and the joystick's push button opens a serial-terminal prompt to change how
many degrees each joystick nudge moves the servos (the "gain").

## Block diagram

```
                 +------------------------+
                 |                        |
   Joystick ---->|  HORZ (ADC, GPIO34)    |
  (pan/tilt) --->|  VERT (ADC, GPIO35)    |
   button   ---->|  SEL  (GPIO32)         |
                 |                        |
 Slide switch -->|  GPIO33                |----> LED1 (GPIO25) "Camera 1 active"
 (camera select) |                        |----> LED2 (GPIO26) "Camera 2 active"
                 |          ESP32         |
                 |      (MicroPython)     |----> Servo: Camera 1 Pan  (GPIO13)
                 |                        |----> Servo: Camera 1 Tilt (GPIO12)
                 |                        |----> Servo: Camera 2 Pan  (GPIO14)
                 |                        |----> Servo: Camera 2 Tilt (GPIO27)
                 |                        |
                 |     UART0 (USB) <----- |----- Serial terminal (gain input)
                 +------------------------+
```

## Pin map

| Signal                     | ESP32 pin |
|----------------------------|-----------|
| Joystick horizontal (VRx)  | GPIO34 (ADC, input-only) |
| Joystick vertical (VRy)    | GPIO35 (ADC, input-only) |
| Joystick push button (SW)  | GPIO32 |
| Slide switch (common)      | GPIO33 |
| LED 1 — Camera 1 selected  | GPIO25 |
| LED 2 — Camera 2 selected  | GPIO26 |
| Camera 1 — Pan servo       | GPIO13 |
| Camera 1 — Tilt servo      | GPIO12 |
| Camera 2 — Pan servo       | GPIO14 |
| Camera 2 — Tilt servo      | GPIO27 |

Slide switch wiring: left terminal -> V+, right terminal -> GND, common ->
GPIO33 (so the pin reads `1` with the switch left, `0` with it right).

## Files

- `joystick.py` — `Joystick` class owning only the two analog axes (`xAxis`,
  `yAxis`, `mode`) — no button pin, matching the official starter template.
  `read()` returns one of the class constants `Joystick.LEFT`/`RIGHT`/`UP`/
  `DOWN`/`MIDDLE` (`'L'`/`'R'`/`'U'`/`'D'`/`'M'`). A diagonal push reports
  whichever axis is deflected further from center, rather than always
  favoring the horizontal axis. Supports `mode="polling"` (reads the ADC
  pins directly on every call) and `mode="interrupt"` (a periodic
  `machine.Timer` callback samples the ADC in the background; `read()` just
  returns the last cached value) — an unrecognized mode raises `ValueError`
  instead of silently falling back to polling.
- `servo.py` — `Servo` class wrapping `machine.PWM`. `goto(angle)` moves to an
  absolute angle (0-180, clamped); `left(angle)`/`right(angle)` move relative
  to the current position.
- `main.py` — wires everything together: defines and reads the joystick's
  push-button `Pin` directly (per the project's requirement that the button
  live in `main.py`, not inside `Joystick`), reads the slide switch to pick
  a camera (as one `CAMERAS` record holding its pan servo, tilt servo and
  LED) and lights its LED, reads the joystick to drive that camera's two
  servos, and opens a serial prompt for a 1-10 gain value when the button is
  pressed. The prompt reads stdin non-blockingly (via `select.poll`), so
  camera selection and LEDs keep updating live while the user is typing a
  gain value instead of the whole loop freezing until Enter is pressed.
- `diagram.json` — Wokwi wiring diagram for an ESP32 DevKit-C V4 with the
  joystick, slide switch, two LEDs (with current-limiting resistors) and the
  four servos already connected per the pin map above.

## Setting it up in Wokwi

1. Go to [wokwi.com](https://wokwi.com), create a **new project**, and choose
   the **MicroPython ESP32** template.
2. Replace the generated `diagram.json` with the one in this folder (use the
   "..." menu on the diagram editor, or paste its contents into the diagram
   JSON view).
3. Replace `main.py` with the one here, and add `joystick.py` and `servo.py`
   as new files in the project (use the "+" / "New file" button in the
   Wokwi file explorer) with the contents from this folder.
4. Click the green **Run** (▶) button.

## Testing checklist

- **Polling mode**: with `Joystick(..., mode="polling")`, pushing the
  joystick left/right/up/down should print/move immediately; releasing to
  center should stop movement.
- **Slide switch + LEDs**: flipping the switch should instantly swap which
  LED is lit and which pair of servos the joystick now drives.
- **Servos**: each camera's pan servo should sweep horizontally and tilt
  servo vertically, independent of the other camera's servos.
- **Gain prompt**: press the joystick button — the serial terminal should
  print a prompt. Typing `10` and pressing Enter should make subsequent
  joystick movements visibly faster than the default gain of `1`. Typing
  `0`, `11`, `-1`, `a`, or `&` should each print an error and ask again
  without touching the stored gain. While the prompt is open, flipping the
  slide switch should still swap the active LED immediately — the loop
  should never freeze waiting for the gain input.
- **Diagonal pushes**: pushing the joystick diagonally (e.g. up-and-left)
  should move whichever of pan/tilt corresponds to the axis pushed further,
  not silently default to pan every time.
- **Interrupt mode**: switch `main.py` to `mode="interrupt"` (already the
  default above) — behavior should be unchanged from polling mode, just
  sampled via the timer callback instead of inline in the loop.

## Notes / design choices

- The joystick's raw ADC readings (0-4095) are bucketed around a center
  value with a dead zone (`Joystick.CENTER` / `Joystick.DEADZONE`), so minor
  analog noise near the middle position doesn't register as movement. On a
  diagonal push, the axis with the larger deviation from center wins, since
  `read()` can only report one direction at a time.
- `Servo` pulse widths default to `550`-`2400` µs (Wokwi's simulated servo
  defaults) and are converted to a 16-bit duty cycle at the configured PWM
  frequency (50 Hz by default), with the PWM period derived from that
  frequency rather than a separate hardcoded constant.
- The gain button press is edge-detected in `main.py` (`button_was_pressed`)
  so holding the button down doesn't repeatedly reopen the prompt.
- The gain prompt (`start_gain_prompt()` / `poll_gain_prompt()`) reads stdin
  one byte at a time via `select.poll(0)`, which never blocks — it only
  consumes bytes that are already waiting, so `main.py`'s loop keeps running
  select_camera()/move_camera() every iteration even while a gain value is
  being typed.
- `CAMERAS` is a 2-entry list (one record per camera: pan servo, tilt servo,
  LED) indexed by the slide switch reading, and `MOVE_MAP` maps each
  joystick direction to a `(servo, method)` pair — avoiding the need to
  edit three separate places in lockstep to add a camera or direction.
