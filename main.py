import sys

try:
    import select
except ImportError:
    import uselect as select

from machine import Pin
from time import sleep_ms

from joystick import Joystick
from servo import Servo

# --- Pin map -----------------------------------------------------------
# Joystick
JOYSTICK_HORZ_PIN = 34
JOYSTICK_VERT_PIN = 35
JOYSTICK_BUTTON_PIN = 32

# Camera select
SLIDE_SWITCH_PIN = 33
LED_CAMERA_1_PIN = 25
LED_CAMERA_2_PIN = 26

# Servos: pan/tilt pair per camera
CAMERA_1_PAN_PIN = 13
CAMERA_1_TILT_PIN = 12
CAMERA_2_PAN_PIN = 14
CAMERA_2_TILT_PIN = 27

MIN_GAIN = 1
MAX_GAIN = 10
DEFAULT_GAIN = 1
LOOP_DELAY_MS = 50

joystick = Joystick(
    xAxis=JOYSTICK_HORZ_PIN,
    yAxis=JOYSTICK_VERT_PIN,
    mode="interrupt",
)

# The joystick's push button is wired and read here in main.py (Joystick
# only owns the two analog axes), so pressing it can open the gain prompt.
joystick_button = Pin(JOYSTICK_BUTTON_PIN, Pin.IN, Pin.PULL_UP)

camera_select = Pin(SLIDE_SWITCH_PIN, Pin.IN, Pin.PULL_UP)

# Each camera is one record of its pan/tilt servos and status LED, indexed
# by camera_select's reading (0 = camera 1, 1 = camera 2), instead of two
# parallel sets of variables kept in sync by hand.
CAMERAS = [
    {
        "pan": Servo(CAMERA_1_PAN_PIN),
        "tilt": Servo(CAMERA_1_TILT_PIN),
        "led": Pin(LED_CAMERA_1_PIN, Pin.OUT),
    },
    {
        "pan": Servo(CAMERA_2_PAN_PIN),
        "tilt": Servo(CAMERA_2_TILT_PIN),
        "led": Pin(LED_CAMERA_2_PIN, Pin.OUT),
    },
]

# Maps a joystick direction to which servo it drives and which way.
MOVE_MAP = {
    Joystick.LEFT: ("pan", "left"),
    Joystick.RIGHT: ("pan", "right"),
    Joystick.UP: ("tilt", "right"),
    Joystick.DOWN: ("tilt", "left"),
}

gain = DEFAULT_GAIN
button_was_pressed = False

# Non-blocking gain prompt state. A plain input() would block the whole
# control loop (camera selection, LEDs, servos) until Enter was pressed,
# so instead we poll stdin a byte at a time and keep looping normally
# while a digit string is being typed.
_stdin_poller = select.poll()
_stdin_poller.register(sys.stdin, select.POLLIN)
gain_prompt_active = False
_gain_input_buffer = ""


def select_camera():
    """Reads the slide switch, lights the active camera's LED, and
    returns that camera's CAMERAS record."""
    active_index = 0 if camera_select.value() == 1 else 1
    for index, camera in enumerate(CAMERAS):
        camera["led"].value(index == active_index)
    return CAMERAS[active_index]


def start_gain_prompt():
    global gain_prompt_active, _gain_input_buffer
    gain_prompt_active = True
    _gain_input_buffer = ""
    print("Enter joystick gain ({}-{}): ".format(MIN_GAIN, MAX_GAIN))


def try_set_gain(raw):
    """Validates a raw gain string and applies it. Returns True on
    success, False (after printing why) on an invalid value."""
    global gain
    try:
        value = int(raw)
    except ValueError:
        print("Invalid gain '{}', please enter a whole number.".format(raw))
        return False

    if MIN_GAIN <= value <= MAX_GAIN:
        gain = value
        print("Gain set to {}".format(gain))
        return True

    print("Invalid gain {}, must be between {} and {}.".format(value, MIN_GAIN, MAX_GAIN))
    return False


def poll_gain_prompt():
    """Non-blocking: consumes whatever input is currently waiting and,
    once a full line has been typed, validates it. Returns immediately if
    nothing is available yet, so the rest of the control loop keeps running
    while the user is typing."""
    global gain_prompt_active, _gain_input_buffer

    while _stdin_poller.poll(0):
        ch = sys.stdin.read(1)
        if ch not in ("\n", "\r"):
            _gain_input_buffer += ch
            continue

        raw = _gain_input_buffer
        _gain_input_buffer = ""
        if raw == "":
            continue  # ignore a stray \r\n pair

        if try_set_gain(raw):
            gain_prompt_active = False
            return
        print("Enter joystick gain ({}-{}): ".format(MIN_GAIN, MAX_GAIN))


def move_camera(camera, direction, gain_value):
    if direction == Joystick.MIDDLE:
        return
    servo_key, method = MOVE_MAP[direction]
    getattr(camera[servo_key], method)(gain_value)


while True:
    active_camera = select_camera()

    # Read the joystick button here in main.py and only trigger the gain
    # prompt on the press edge, so holding the button down doesn't re-open
    # the prompt every loop iteration.
    button_is_pressed = joystick_button.value() == 0
    if button_is_pressed and not button_was_pressed and not gain_prompt_active:
        start_gain_prompt()
    button_was_pressed = button_is_pressed

    if gain_prompt_active:
        poll_gain_prompt()
    else:
        move_camera(active_camera, joystick.read(), gain)

    sleep_ms(LOOP_DELAY_MS)
