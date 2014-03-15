#!/usr/bin/env python

import piggyphoto, pygame
import os, sys
import time, datetime
import StringIO
from subprocess import call
import argparse

COUNT_DOWN_TIME = 1
MONTAGE_DISPLAY_TIME = 2
IDLE_TIME = 10
IMAGE_DISPLAY_TIME = 3
CAPTURE_SHUTTER_SPEED = '1/200'
DEFAULT_PREVIEW_SHUTTER_SPEED = '1'

CAPTURE_APERTURE = '8'
DEFAULT_PREVIEW_APERTURE = '1.8'

TTY = '/dev/ttyUSB0'

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
            print "needed new camera"
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
        print "Sleep!"

class DebugCamera():
    def capture_preview(self):
        with open('preview.jpg', 'rb') as img:
            return pygame.image.load(StringIO.StringIO(img.read()))
    
    def capture_image(self, image_path):
        time.sleep(0.5)
        print "Captured an image!", image_path
        
    def sleep(self):
        print "Sleep!"

class PhotoBooth(object):
    def __init__(self, image_dest, fullscreen, debug, webcam, printing):
        self.debug = debug
        if debug:
            self.camera = DebugCamera()
        elif webcam:
            self.camera = WebcamCamera()
        else:
            self.camera = Camera()
        
        self.printing = printing
        
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
        self.camera.capture_image(os.path.join(self.output_dir, file_name))

    def display_camera_arrow(self):
        self.main_surface.fill((0,0,0))
        arrow = pygame.Surface((300, 300))
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
        out_path = os.path.join(self.output_dir, out_name)
        first = self.load_image(images[0])
        size = (first.get_size()[0]/2, first.get_size()[1]/2)
        
        combined = pygame.Surface(first.get_size())
        for count, image_name in enumerate(images):
            image = self.load_image(image_name)
            image = pygame.transform.scale(image, size)
            x_pos = size[0] * (count % 2)
            y_pos = size[1] * (1 if count > 1 else 0)
            combined.blit(image, (x_pos, y_pos))
        if self.debug:
            print "Would save image to:", out_path
        else:
            pygame.image.save(combined, out_path)
        
        if self.printing:
            if self.debug:
                print "lpr", out_path
            else:
                call(["lpr", out_path])

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
            if time.time() - self.display_timer < IMAGE_DISPLAY_TIME:
                # still displaying last image
                pass
            else:
                print "finished displaying last image"
                self.timer = time.time() + COUNT_DOWN_TIME + 1
                self.display_timer = -1
        else:
            self.booth.display_preview()
            if not self.capture_start:
                self.booth.render_text_centred("Push when ready!")
        
            if self.timer > 0:
                self.do_countdown()
        
        if button_pressed and not self.capture_start:
            self.timer = time.time() + COUNT_DOWN_TIME + 1
            self.capture_start = datetime.datetime.now()
            
        return self.finished
    
    def idle(self):
        return not self.capture_start and time.time() - self.session_start > IDLE_TIME
    
    def do_countdown(self):
        time_remaining = self.timer - time.time()
        
        if self.take_picture:
            self.take_picture = False
            image_name = self.get_image_name(self.photo_count)
            self.booth.capture_image(image_name)
            if IMAGE_DISPLAY_TIME > 0:
                self.display_timer = time.time()
                self.booth.display_image(image_name)
            if self.photo_count == 4:
                self.timer = -1
                self.photo_count = 1
                self.montage_timer = time.time() + IMAGE_DISPLAY_TIME
            else:
                self.timer = time.time() + COUNT_DOWN_TIME + 1
                self.photo_count += 1
        elif time_remaining <= 0:
            self.booth.display_camera_arrow()
            self.take_picture = True
        else:
            lines = [u'Taking picture %d of 4 in:' % self.photo_count, str(int(time_remaining))]
            if time_remaining < 2.5 and int(time_remaining * 3) % 2 == 0:
                lines = ["Look at the camera!", ""] + lines
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
            
        if time.time() - self.montage_timer > MONTAGE_DISPLAY_TIME:
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
                print "BUTTON PRESSED"
                self.pressed = True
                return True
            elif not currently_pressed:
                self.pressed = False
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("save_to", help="Location to save images")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--debug", help="Don't require a real camera to be attached", action="store_true")
    group.add_argument("-w", "--webcam", help="Use a webcam to capture images", action="store_true")
    parser.add_argument("--nofullscreen", help="Don't use fullscreen mode", action="store_true")
    parser.add_argument("--printing", help="Enable printing", action="store_true")
    args = parser.parse_args()

    booth = PhotoBooth(args.save_to, fullscreen=(not args.nofullscreen), debug=args.debug, webcam=args.webcam, printing=args.printing)
    booth.start()

# TODO
# Investigate leave locked
# Reinit the camera, or exit it when on black screen
# Focusing?

