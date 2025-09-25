from enum import Enum

import pyglet

import sys
import time

print(" _______  ___      __   __      ___  _______  __   __ ")
print("|       ||   |    |  | |  |    |   ||       ||  | |  |")
print("|    ___||   |    |  |_|  |    |   ||   _   ||  |_|  |")
print("|   |___ |   |    |       |    |   ||  | |  ||       |")
print("|    ___||   |___ |_     _| ___|   ||  |_|  ||_     _|")
print("|   |    |       |  |   |  |       ||       |  |   |  ")
print("|___|    |_______|  |___|  |_______||_______|  |___|  ")
print("                                                      ")
print("----------- TX To Joystick Input Converter -----------")

# -----------------
# User parameters |
# -----------------
# Configure those
EXPO_FACTOR = 1
SENSITIVITY = 1.5
# -----------------


class Platform(Enum):
    LINUX = 1
    WINDOWS = 2


platform = Platform.WINDOWS

if sys.platform.startswith("win"):
    # Windows
    import vgamepad as vg
    platform = Platform.WINDOWS

    print("Detected OS: Windows")
else:
    # Linux
    import uinput
    platform = Platform.LINUX

    print("Detected OS: Linux")


def create_windows_joystick():
    global virtual_joystick_windows
    virtual_joystick_windows = vg.VX360Gamepad()


def create_linux_joystick():
    global virtual_joystick_linux

    capabilities = [
        # Axes
        uinput.ABS_X + (0, 255, 0, 0),
        uinput.ABS_Y + (0, 255, 0, 0),
        uinput.ABS_RX + (0, 255, 0, 0),
        uinput.ABS_RY + (0, 255, 0, 0),
        uinput.ABS_Z + (0, 255, 0, 0),   # L trigger
        uinput.ABS_RZ + (0, 255, 0, 0),  # R trigger
        # Buttons
        uinput.BTN_A,
        uinput.BTN_B,
        uinput.BTN_X,
        uinput.BTN_Y,
        uinput.BTN_TL,  # L bumper
        uinput.BTN_TR,  # R bumper
    ]

    virtual_joystick_linux = uinput.Device(capabilities, name="Flyjoy")


def clamp(number, min_num, max_num):
    return max(min_num, min(number, max_num))


def expo(input_value):
    return (1 - EXPO_FACTOR) * input_value + EXPO_FACTOR * (input_value ** 3)


def do_linux_input(axis, input):
    final_input = int(((input / 2) + 0.5) * 255)
    virtual_joystick_linux.emit(axis, final_input)


def do_windows_input(side, x, y):
    final_x = int(x * 32767)
    final_y = int(y * 32767)

    if side == 0:
        virtual_joystick_windows.left_joystick(
            x_value=final_x,
            y_value=final_y
        )
    else:
        virtual_joystick_windows.right_joystick(
            x_value=final_x,
            y_value=final_y
        )


# Get joysticks
print("Fetching connected joysticks...")
joysticks = pyglet.input.get_joysticks()

if not joysticks:
    exit("No joysticks found.")

# Connect to the joystick
# TODO: multiple joysticks
print("Found joystick")

joystick = joysticks[0]
joystick.open()

# Create virtual joystick
if platform == Platform.LINUX:
    create_linux_joystick()
else:
    create_windows_joystick()

while True:
    # Listen to joystick events
    pyglet.app.platform_event_loop.step(0.01)
    pyglet.clock.tick()

    # Get TX inputs
    input_x = expo(-clamp(joystick.x * SENSITIVITY, -1, 1))
    input_y = expo(-clamp(joystick.z * SENSITIVITY, -1, 1))
    input_rx = expo(-clamp(joystick.ry * SENSITIVITY, -1, 1))
    input_ry = expo(clamp(joystick.y * SENSITIVITY, -1, 1))

    # Print info
    print("x: {:5.2f}, y: {:5.2f}, rx: {:5.2f}, ry {:5.2f}"
          .format(input_x, -input_y, input_rx, -input_ry))

    # Simulate joystick inputs
    if platform == Platform.LINUX:
        do_linux_input(uinput.ABS_X, input_x)
        do_linux_input(uinput.ABS_Y, input_y)
        do_linux_input(uinput.ABS_RX, input_rx)
        do_linux_input(uinput.ABS_RY, input_ry)
    else:
        do_windows_input(0, input_x, input_y)
        do_windows_input(1, input_rx, input_ry)
        virtual_joystick_windows.update()

    time.sleep(1/30)
