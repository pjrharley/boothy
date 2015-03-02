#!/usr/bin/env python

import pygame
import os
import sys
import time
import datetime
from subprocess import call
import argparse
import logging

from cameras import DebugCamera, WebcamCamera, Camera
from button import Button

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
    from upload import upload_image_async
except ImportError:
    upload_image_async = None

PADDING_PERCENT = 1.5
PRINT_IMAGE_SIZE = None # "3498x2478"

class PhotoBooth(object):
    def __init__(self, image_dest, fullscreen, debug, webcam, print_count, printer, upload_to):
        self.debug = debug
        if debug:
            self.camera = DebugCamera()
        elif webcam:
            self.camera = WebcamCamera()
        else:
            self.camera = Camera()

        if self.debug:
            self.count_down_time = 2
            self.image_display_time = 3
            self.montage_display_time = 8
            self.idle_time = 30

        else:
            self.count_down_time = 5
            self.image_display_time = 3
            self.montage_display_time = 15
            self.idle_time = 240


        self.print_count = print_count
        self.printer = printer
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
            info = pygame.display.Info()
            pygame.display.set_mode((info.current_w/2, info.current_h/2))

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
            self.current_session.do_frame(button_press)
            if self.current_session.idle():
                self.current_session = None
                self.camera.sleep()
            elif self.current_session.finished():
                # Start a new session
                self.current_session = PhotoSession(self)
        elif button_press:
            # Start a new session
            self.current_session = PhotoSession(self)
        else:
            self.wait()

        return self.check_for_quit_event()

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

    def render_text_bottom(self, text, size=142):
        location = self.main_surface.get_rect()
        font = pygame.font.SysFont(pygame.font.get_default_font(), size)
        line = font.render(text, 1, (210, 210, 210))
        line_height = font.get_linesize()
        
        line_pos = line.get_rect()
        line_pos.centerx = location.centerx
        line_pos.centery = location.height - 2 * line_height
        self.main_surface.blit(line, line_pos)


    def capture_image(self, file_name):
        file_path = os.path.join(self.output_dir, file_name)
        logger.info("Capturing image to: %s", file_path)
        self.camera.capture_image(file_path)
        if self.upload_to:
            upload_image_async(self.upload_to, file_path)

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

    def save_and_print_combined(self, out_name, images):
        logger.info("Saving image: %s", out_name)
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

        logger.info("Save image to: %s", out_path)
        if not self.debug:
            pygame.image.save(combined, out_path)

        if self.print_count:
            if PRINT_IMAGE_SIZE:
                print_dir = os.path.join(self.output_dir, 'to_print')
                print_path = os.path.join(print_dir, out_name)
                convert_cmd = ['convert', out_path, '-resize', PRINT_IMAGE_SIZE + '^', '-gravity', 'center', '-extent', PRINT_IMAGE_SIZE, print_path]

                logger.info(' '.join(convert_cmd))
                if not self.debug:
                    if not os.path.exists(print_dir):
                        os.makedirs(print_dir)
                    call(convert_cmd)
            else:
                print_path = out_path
            self.print_image(print_path)

    def print_image(self, image_path):
        printing_cmd = ["lpr"]
        if self.printer:
            printing_cmd += ["-P", self.printer]
        printing_cmd += ["-#", str(self.print_count), image_path]

        logger.info(' '.join(printing_cmd))
        if not self.debug:
            call(printing_cmd)

    def add_button_listener(self):
        self.button = Button()

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


class SessionState(object):
    def __init__(self, session):
        self.session = session

    def run(self):
        raise NotImplementedError("Run not implemented")

    def next(self, button_pressed):
        raise NotImplementedError("Next not implemented")

class TimedState(SessionState):
    def __init__(self, session, timer_length_s):
        super(TimedState, self).__init__(session)
        self.timer = time.time() + timer_length_s

    def time_up(self):
        return self.timer <= time.time()

class WaitingState(SessionState):
    def run(self):
        self.session.booth.display_preview()
        self.session.booth.render_text_centred("Push when ready!")

    def next(self, button_pressed):
        if button_pressed:
            self.session.capture_start = datetime.datetime.now()
            return CountdownState(self.session)
        else:
            return self

class CountdownState(TimedState):
    def __init__(self, session):
        super(CountdownState, self).__init__(session, session.booth.count_down_time)
        self.capture_start = datetime.datetime.now()

    def run(self):
        self.session.booth.display_preview()
        self.display_countdown()

    def display_countdown(self):
        time_remaining = self.timer - time.time()

        if time_remaining <= 0:
            self.session.booth.display_camera_arrow(clear_screen=True)
        else:
            lines = [u'Taking picture %d of 4 in:' % (self.session.photo_count + 1), str(int(time_remaining))]
            if time_remaining < 2.5 and int(time_remaining * 2) % 2 == 0:
                lines = ["Look at the camera!", ""] + lines
            elif time_remaining < 2.5:
                lines = ["", ""] + lines
                self.session.booth.display_camera_arrow()
            else:
                lines = ["", ""] + lines
            self.session.booth.render_text_centred(*lines)

    def next(self, button_pressed):
        if self.time_up():
            image = self.take_picture()
            return ShowLastCaptureState(self.session, image)
        else:
            return self

    def take_picture(self):
        self.session.photo_count += 1
        image_name = self.session.get_image_name(self.session.photo_count)
        self.session.booth.capture_image(image_name)
        return image_name


class ShowLastCaptureState(TimedState):
    def __init__(self, session, image):
        super(ShowLastCaptureState, self).__init__(session, session.booth.image_display_time)
        self.image = image

    def run(self):
        self.session.booth.display_image(self.image)

    def next(self, button_pressed):
        if self.time_up():
            if self.session.photo_count == 4:
                return ShowSessionMontageState(self.session)
            else:
                return CountdownState(self.session)
        else:
            return self


class ShowSessionMontageState(TimedState):
    def __init__(self, session):
        super(ShowSessionMontageState, self).__init__(session, session.booth.montage_display_time)
        self.displayed = False
        self.saved = False

    def run(self):
        if not self.displayed:
            for im in range(1, 5):
                image = self.session.booth.load_image(self.session.get_image_name(im))
                size = (self.session.booth.size[0]/2, self.session.booth.size[1]/2)
                image = pygame.transform.scale(image, size)
                x_pos = size[0] * ((im - 1) % 2)
                y_pos = size[1] * (1 if im > 2 else 0)
                self.session.booth.main_surface.blit(image, (x_pos, y_pos))
            self.displayed = True
        elif not self.saved:
            self.session.booth.save_and_print_combined(
                self.session.get_image_name('combined'),
                [self.session.get_image_name(im) for im in range(1, 5)])
            self.saved = True
            if self.session.booth.print_count:
                self.session.booth.render_text_bottom("Printing...", size=100)

    def next(self, button_pressed):
        if self.time_up():
            return None
        else:
            return self



class PhotoSession(object):
    def __init__(self, booth):
        self.booth = booth

        self.state = WaitingState(self)
        self.capture_start = None
        self.photo_count = 0
        self.session_start = time.time()

    def do_frame(self, button_pressed):
        self.state.run()

        self.state = self.state.next(button_pressed)

    def idle(self):
        return not self.capture_start and time.time() - self.session_start > self.booth.idle_time

    def get_image_name(self, count):
        return self.capture_start.strftime('%Y-%m-%d-%H%M%S') + '-' + str(count) + '.jpg'

    def finished(self):
        return self.state is None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("save_to", help="Location to save images")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--debug", help="Don't require a real camera to be attached", action="store_true")
    group.add_argument("-w", "--webcam", help="Use a webcam to capture images", action="store_true")
    parser.add_argument("--nofullscreen", help="Don't use fullscreen mode", action="store_true")
    parser.add_argument("-p", "--print_count", help="Set number of copies to print", type=int, default=0)
    parser.add_argument("-P", "--printer", help="Set printer to use", default=None)
    parser.add_argument("-u", "--upload_to", help="Url to upload images to")
    args = parser.parse_args()

    logger.info("Args were: %s", args)

    if args.upload_to and not upload_image_async:
        print "Failed to find requests library, which is required for uploads."
        logger.error("Failed to find requests library.")
        sys.exit(-1)

    booth = PhotoBooth(args.save_to, fullscreen=(not args.nofullscreen), debug=args.debug, webcam=args.webcam, print_count=args.print_count, printer=args.printer, upload_to=args.upload_to)
    try:
        booth.start()
    except Exception:
        logger.exception("Unhandled exception!")
        sys.exit(-1)
    finally:
        logger.info("Fin!")
