#!/usr/bin/env python

import piggyphoto, pygame
import os, sys
import time, datetime
import StringIO
from subprocess import call
import argparse
import threading

import logging

logger = logging.getLogger('photobooth')

file_log_handler = logging.FileHandler('photobooth.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_log_handler.setFormatter(formatter)
logger.addHandler(file_log_handler)

stdout_log_handler = logging.StreamHandler(sys.stdout)
stdout_log_handler.setLevel(logging.WARN)
logger.addHandler(stdout_log_handler)

logger.setLevel(logging.DEBUG)

try:
    import requests
except ImportError:
    requests = None

CAPTURE_SHUTTER_SPEED = '1/200'
DEFAULT_PREVIEW_SHUTTER_SPEED = '1'

CAPTURE_APERTURE = '8'
DEFAULT_PREVIEW_APERTURE = '1.8'

#PHOTO_API_KEY = '''***REMOVED***'''
PHOTO_API_KEY = '''***REMOVED***'''

TTY = '/dev/ttyUSB0'

PADDING_PERCENT = 1

class Camera(object):
    def __init__(self):
        self.camera = piggyphoto.camera()
        self.reset_settings()

        #self.camera.config.main.actions.autofocusdrive=True
        #self.camera.config.main.actions.manualfocusdrive=2
        #qq self.camera.leave_locked()

    def reset_settings(self):
        con = self.camera.config
        con.main.capturesettings.autoexposuremode.value = 'AV'
        self.camera.config = con
        #self.camera.config.main.capturesettings.shutterspeed.value = DEFAULT_PREVIEW_SHUTTER_SPEED
        #self.camera.config.main.capturesettings.aperture.value = DEFAULT_PREVIEW_APERTURE

    def set_settings_for_capture(self):
        con = self.camera.config
        con.main.capturesettings.autoexposuremode.value = 'Manual'
        self.camera.config = con
        #self.camera.config.main.capturesettings.shutterspeed.value = CAPTURE_SHUTTER_SPEED
        #self.camera.config.main.capturesettings.aperture.value = CAPTURE_APERTURE

    def capture_preview(self):
        if not self.camera:
            self.camera = piggyphoto.camera()
            logging.debug("Created new camera")
        return pygame.image.load(StringIO.StringIO(self.camera.capture_preview().get_data()))

    def capture_image(self, image_path):
        del self.camera
        self.camera = piggyphoto.camera()

        self.set_settings_for_capture()
        self.camera.capture_image(image_path)
        self.reset_settings()

    def sleep(self):
        del self.camera
        self.camera = None


class WebcamCamera():
    def __init__(self):
        import pygame.camera
        pygame.camera.init()
        self.camera = pygame.camera.Camera("/dev/video0",(640,480))
        self.camera.start()

    def capture_preview(self):
        return self.camera.get_image()

    def capture_image(self, image_path):
        time.sleep(0.5)
        pygame.image.save(self.capture_preview(), image_path)

    def sleep(self):
        logging.info("Sleep!")

class DebugCamera():
    def capture_preview(self):
        with open('preview.jpg', 'rb') as img:
            return pygame.image.load(StringIO.StringIO(img.read()))

    def capture_image(self, image_path):
        time.sleep(0.5)
        logging.info("Captured an image: %s", image_path)

    def sleep(self):
        logging.info("Sleep!")

class PhotoBooth(object):
    def __init__(self, image_dest, fullscreen, debug, webcam, printing, upload_to):
        self.debug = debug
        if debug:
            self.camera = DebugCamera()
        elif webcam:
            self.camera = WebcamCamera()
        else:
            self.camera = Camera()

        if self.debug:
            self.count_down_time = 1
            self.image_display_time = 3
            self.montage_display_time = 8
            self.idle_time = 30

        else:
            self.count_down_time = 4
            self.image_display_time = 3
            self.montage_display_time = 15
            self.idle_time = 120


        self.printing = printing
        self.upload_to = upload_to
        self.output_dir = image_dest
        self.size = None
        self.fullscreen = fullscreen
        self.events = []
        self.current_session = None

    def capture_preview(self):
        picture = self.camera.capture_preview()

        if self.size:
            picture = pygame.transform.scale(picture, self.size)
        picture = pygame.transform.flip(picture, True, False)
        return picture

    def display_preview(self):
        picture = self.capture_preview()
        self.main_surface.blit(picture, (0, 0))

    def display_image(self, image_name):
        picture = self.load_image(image_name)
        picture = pygame.transform.scale(picture, self.size)
        self.main_surface.blit(picture, (0, 0))

    def start(self):
        pygame.init()
        pygame.mouse.set_visible(False)

        self.clock = pygame.time.Clock()

        self.add_button_listener()

        if self.fullscreen:
            pygame.display.set_mode((0,0), pygame.FULLSCREEN)
        else:
            raise Exception("I've broken non fullscreen for now")
            preview = self.capture_preview()
            pygame.display.set_mode(preview.get_size())

        self.main_surface = pygame.display.get_surface()

        self.size = self.main_surface.get_size()

        while self.main_loop():
            pass
        self.camera.sleep()

    def main_loop(self):
        pygame.event.clear()
        self.clock.tick(25)
        if len(self.events) > 10:
            self.events = self.events[:10]
        pygame.display.flip()

        button_press = self.space_pressed() or self.button.is_pressed()

        if self.current_session:
            if self.current_session.do_frame(button_press):
                # Start a new session
                self.current_session = PhotoSession(self)
            if self.current_session.idle():
                self.current_session = None
                self.camera.sleep()
        elif button_press:
            # Start a new session
            self.current_session = PhotoSession(self)
        else:
            self.wait()

        return self.check_for_quit_event()

    def idle_timeout(self):
        return False

    def wait(self):
        self.main_surface.fill((0,0,0))
        self.render_text_centred('Press the button to start!')

    def render_text_centred(self, *text_lines):
        location = self.main_surface.get_rect()
        font = pygame.font.SysFont(pygame.font.get_default_font(), 142)
        rendered_lines = [font.render(text, 1, (210, 210, 210)) for text in text_lines]
        line_height = font.get_linesize()
        middle_line = len(text_lines) / 2.0 - 0.5

        for i, line in enumerate(rendered_lines):
            line_pos = line.get_rect()
            lines_to_shift = i - middle_line
            line_pos.centerx = location.centerx
            line_pos.centery = location.centery + lines_to_shift * line_height
            self.main_surface.blit(line, line_pos)

    def capture_image(self, file_name):
        file_path = os.path.join(self.output_dir, file_name)
        logger.info("Capturing image to: %s", file_path)
        self.camera.capture_image(file_path)
        if self.upload_to:
            UploadThread(self.upload_to, file_path).start()

    def display_camera_arrow(self, clear_screen=False):
        if clear_screen:
            self.main_surface.fill((0,0,0))
        arrow = pygame.Surface((300, 300), flags=pygame.SRCALPHA)
        pygame.draw.polygon(arrow, (255, 255, 255), ((100, 0), (200, 0), (200, 200), (300, 200), (150, 300), (0, 200), (100, 200)))
        arrow = pygame.transform.flip(arrow, False, True) # qq sort the coords out instead
        x = (self.size[0] - 300) / 2
        self.main_surface.blit(arrow, (x, 20))

    def load_image(self, file_name):
        if self.debug:
            image_path = "test.jpg"
        else:
            image_path = os.path.join(self.output_dir, file_name)
        return pygame.image.load(image_path)

    def save(self, out_name, images):
        logging.info("Saving image: %s", out_name)
        out_path = os.path.join(self.output_dir, out_name)
        first_size = self.load_image(images[0]).get_size()
        padding_pxls = int(PADDING_PERCENT / 100.0 * first_size[0])
        logger.debug("Padding: %s", padding_pxls)
        
        size = ((first_size[0] - padding_pxls)/2, (first_size[1] - padding_pxls)/2)
        logger.debug("Image size: %s", size)

        combined = pygame.Surface(first_size)
        combined.fill((255,255,255))
        for count, image_name in enumerate(images):
            image = self.load_image(image_name)
            image = pygame.transform.scale(image, size)
            x_pos = (size[0] + padding_pxls) * (count % 2)
            y_pos = (size[1] + padding_pxls) * (1 if count > 1 else 0)
            combined.blit(image, (x_pos, y_pos))
        if self.debug:
            logging.info("Would save image to: %s", out_path)
        else:
            pygame.image.save(combined, out_path)

        if self.printing:
            printing_cmd = ["lpr", "-P", "MG6200USB", "-#", str(self.printing), out_path]
            if self.debug:
                logging.info(' '.join(printing_cmd))
            else:
                call(printing_cmd)

    def add_button_listener(self):
        self.button = Button(TTY)

    def check_key_event(self, *keys):
        self.events += pygame.event.get(pygame.KEYUP)
        for event in self.events:
            if event.dict['key'] in keys:
                self.events = []
                return True
        return False

    def space_pressed(self):
        return self.check_key_event(pygame.K_SPACE)

    def check_for_quit_event(self):
        return not self.check_key_event(pygame.K_q, pygame.K_ESCAPE) \
            and not pygame.event.peek(pygame.QUIT)


class PhotoSession(object):
    def __init__(self, booth):
        self.booth = booth

        self.timer = -1
        self.photo_count = 1
        self.capture_start = None
        self.display_timer = -1
        self.montage_timer = -1
        self.montage_displayed = False
        self.finished = False
        self.saved_image = False
        self.take_picture = False
        self.session_start = time.time()

    def do_frame(self, button_pressed):
        if self.montage_timer > 0:
            self.display_montage()
        elif self.display_timer > 0:
            if time.time() - self.display_timer < self.booth.image_display_time:
                # still displaying last image
                pass
            else:
                logging.debug("finished displaying last image")
                self.timer = time.time() + self.booth.count_down_time + 1
                self.display_timer = -1
        else:
            self.booth.display_preview()
            if not self.capture_start:
                self.booth.render_text_centred("Push when ready!")

            if self.timer > 0:
                self.do_countdown()

        if button_pressed and not self.capture_start:
            self.timer = time.time() + self.booth.count_down_time + 1
            self.capture_start = datetime.datetime.now()

        return self.finished

    def idle(self):
        return not self.capture_start and time.time() - self.session_start > self.booth.idle_time

    def do_countdown(self):
        time_remaining = self.timer - time.time()

        if self.take_picture:
            self.take_picture = False
            image_name = self.get_image_name(self.photo_count)
            self.booth.capture_image(image_name)
            if self.booth.image_display_time > 0:
                self.display_timer = time.time()
                self.booth.display_image(image_name)
            if self.photo_count == 4:
                self.timer = -1
                self.photo_count = 1
                self.montage_timer = time.time() + self.booth.image_display_time
            else:
                self.timer = time.time() + self.booth.count_down_time + 1
                self.photo_count += 1
        elif time_remaining <= 0:
            self.booth.display_camera_arrow(True)
            self.take_picture = True
        else:
            lines = [u'Taking picture %d of 4 in:' % self.photo_count, str(int(time_remaining))]
            if time_remaining < 2.5 and int(time_remaining * 2) % 2 == 0:
                lines = ["Look at the camera!", ""] + lines
            elif time_remaining < 2.5:
                lines = ["", ""] + lines
                self.booth.display_camera_arrow()
            else:
                lines = ["", ""] + lines
            self.booth.render_text_centred(*lines)

    def display_montage(self):
        if not self.montage_displayed:
            for im in range(1, 5):
                image = self.booth.load_image(self.get_image_name(im))
                size = (self.booth.size[0]/2, self.booth.size[1]/2)
                image = pygame.transform.scale(image, size)
                x_pos = size[0] * ((im - 1) % 2)
                y_pos = size[1] * (1 if im > 2 else 0)
                self.booth.main_surface.blit(image, (x_pos, y_pos))
            self.montage_displayed = True
        elif not self.saved_image:
            self.booth.save(self.get_image_name('combined'), [self.get_image_name(im) for im in range(1,5)])
            self.saved_image = True

        if time.time() - self.montage_timer > self.booth.montage_display_time:
            self.montage_timer = -1
            self.montage_displayed = False
            self.finished = True

    def get_image_name(self, count):
        return self.capture_start.strftime('%Y-%m-%d-%H%M%S') + '-' + str(count) + '.jpg'

class Button(object):
    def __init__(self, tty):
        self.pressed = False
        self.tty = tty
        self.port = None

        if os.path.exists(TTY):
            import serial
            self.port = serial.Serial(self.tty, 0)
            self.port.setDTR(level=True)

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

class UploadThread(threading.Thread):
    def __init__(self, url, file_path):
        super(UploadThread, self).__init__()
        self.url = url
        self.file_path = file_path

    def run(self):
        logger.info("Uploading to website: %s", self.file_path)
        with open(self.file_path, 'rb') as f:
            files = {'Filedata': f}
            headers = {'X-API-TOKEN': PHOTO_API_KEY}
            try:
                r = requests.post(self.url, files=files, headers=headers)
                r.raise_for_status()
                logger.info("Uploaded %s successfully", self.file_path)
            except Exception as e:
                logger.exception("Failed to upload %s. ", self.file_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("save_to", help="Location to save images")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--debug", help="Don't require a real camera to be attached", action="store_true")
    group.add_argument("-w", "--webcam", help="Use a webcam to capture images", action="store_true")
    parser.add_argument("--nofullscreen", help="Don't use fullscreen mode", action="store_true")
    parser.add_argument("-p", "--printing", help="Set number of copies to print", type=int, default=0)
    parser.add_argument("-u", "--upload_to", help="Url to upload images to")
    args = parser.parse_args()

    logger.info("Args were: %s", args)

    if args.upload_to and not requests:
        print "Failed to find requests library, which is required for uploads."
        logger.error("Failed to find requests library.")
        sys.exit(-1)

    booth = PhotoBooth(args.save_to, fullscreen=(not args.nofullscreen), debug=args.debug, webcam=args.webcam, printing=args.printing, upload_to=args.upload_to)
    try:
        booth.start()
    except Exception:
        logger.exception("Unhandled exception!")

    logger.info("Fin!")

# TODO
# Investigate leave locked
# Reinit the camera, or exit it when on black screen
# Focusing?

