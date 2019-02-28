
import os
import logging

logger = logging.getLogger('photobooth.button')

DEFAULT_TTY = '/dev/ttyUSB0'


class Button(object):
    def __init__(self, tty=DEFAULT_TTY):
        self.pressed = False
        self.tty = tty
        self.port = None

        if os.path.exists(self.tty):
            import serial
            self.port = serial.Serial(self.tty, 9600)
            self.port.setDTR() #level=True)

    def is_pressed(self):
        if self.port:
            currently_pressed = self.port.getCD()
            if currently_pressed and not self.pressed:
                logger.info("Button press detected")
                self.pressed = True
                return True
            elif not currently_pressed:
                self.pressed = False
        return False
