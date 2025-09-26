from enum import Enum

import pyglet

import tomllib
import sys

print(" _______  ___      __   __      ___  _______  __   __ ")
print("|       ||   |    |  | |  |    |   ||       ||  | |  |")
print("|    ___||   |    |  |_|  |    |   ||   _   ||  |_|  |")
print("|   |___ |   |    |       |    |   ||  | |  ||       |")
print("|    ___||   |___ |_     _| ___|   ||  |_|  ||_     _|")
print("|   |    |       |  |   |  |       ||       |  |   |  ")
print("|___|    |_______|  |___|  |_______||_______|  |___|  ")
print("                                                      ")
print("----------- TX To Joystick Input Converter -----------")


class Platform(Enum):
    LINUX = 1
    WINDOWS = 2


global platform
platform = Platform.WINDOWS

if sys.platform.startswith("win"):
    import vgamepad as vg
    platform = Platform.WINDOWS
    print("Detected OS: Windows")
else:
    import uinput
    platform = Platform.LINUX
    print("Detected OS: Linux")


class TXJoystickConverter:
    def __init__(self, verbose):
        self.verbose = verbose

        # Joysticks
        self.joystick = None
        self.virtual_joystick = None

        # Config
        self.joystick_index = 0
        self.input_x_settings = {}
        self.input_y_settings = {}
        self.input_rx_settings = {}
        self.input_ry_settings = {}

        # Parse config
        print("Parsing config...")
        try:
            self.parse_config()
        except Exception as e:
            exit(e)

        # Joysticks
        self.connect_joystick()
        self.create_virtual_joystick()

    def connect_joystick(self):
        print("Fetching connected joysticks...")
        joysticks = pyglet.input.get_joysticks()

        if not joysticks:
            exit("No joysticks found.")

        # Connect to the joystick
        self.joystick = joysticks[self.joystick_index]

        print("Found joystick '" + self.joystick.device.name + "'")
        self.joystick.open()

        print("Available axis for '" + self.joystick.device.name + "':")
        for control in self.joystick.device.get_controls():
            print(control.name, end=" ")
        print()

    def create_virtual_joystick(self):
        if platform == Platform.WINDOWS:
            self.virtual_joystick = vg.VX360Gamepad()
        else:
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
            self.virtual_joystick = uinput.Device(capabilities, name="Flyjoy")

    def clamp(self, number, min_num, max_num):
        return max(min_num, min(number, max_num))

    def expo(self, input_value, expo):
        return (1 - expo) * input_value + expo * (input_value ** 3)

    def do_linux_input(self, axis, input):
        final_input = int(((input / 2) + 0.5) * 255)
        self.virtual_joystick.emit(axis, final_input)

    def do_windows_input(self, side, x, y):
        final_x = int(x * 32767)
        final_y = int(y * 32767)

        if side == 0:
            self.virtual_joystick.left_joystick(
                x_value=final_x,
                y_value=final_y
            )
        else:
            self.virtual_joystick.right_joystick(
                x_value=final_x,
                y_value=final_y
            )

    def process_axis(self, axis_settings):
        # Get settings
        joystick_value = getattr(self.joystick, axis_settings['axis'])
        sensitivity = axis_settings['sensitivity']
        inverted = -1 if not axis_settings['inverted'] else 1
        exponent = self.clamp(axis_settings['expo'], 0, 1)

        # Get final input
        return self.expo(
            self.clamp(joystick_value * sensitivity, -1, 1) * inverted,
            exponent
        )

    def parse_config(self):

        with open("config.toml", "rb") as f:
            data = tomllib.load(f)

            self.joystick_index = data['joystick']['joystick_index']

            axis = data['axis']
            self.input_x_settings = axis['x']
            self.input_y_settings = axis['y']
            self.input_rx_settings = axis['rx']
            self.input_ry_settings = axis['ry']

            print("Successfully parsed config.")
            return
        print("Failed to parse config.")

    def update(self, dt):
        # Get TX inputs
        input_x = self.process_axis(self.input_x_settings)
        input_y = self.process_axis(self.input_y_settings)
        input_rx = self.process_axis(self.input_rx_settings)
        input_ry = self.process_axis(self.input_ry_settings)

        # Print info
        if self.verbose:
            print("x: {:5.2f}, y: {:5.2f}, rx: {:5.2f}, ry {:5.2f}"
                  .format(input_x, -input_y, input_rx, -input_ry), end="\r")
            sys.stdout.flush()

        # Simulate joystick inputs
        if platform == Platform.LINUX:
            self.do_linux_input(uinput.ABS_X, input_x)
            self.do_linux_input(uinput.ABS_Y, input_y)
            self.do_linux_input(uinput.ABS_RX, input_rx)
            self.do_linux_input(uinput.ABS_RY, input_ry)
        else:
            self.do_windows_input(0, input_x, input_y)
            self.do_windows_input(1, input_rx, input_ry)
            self.virtual_joystick.update()


if __name__ == "__main__":
    converter = TXJoystickConverter(verbose=False)
    pyglet.clock.schedule_interval(converter.update, 1/30)
    pyglet.app.run()
