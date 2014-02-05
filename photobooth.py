#!/usr/bin/env python

import piggyphoto, pygame
import os, sys
import time, datetime
import StringIO

COUNT_DOWN_TIME = 2
MONTAGE_DISPLAY_TIME = 4

class Camera(object):
    def __init__(self):
        self.camera = piggyphoto.camera()
        #qq self.camera.leave_locked()
    
    def capture_preview(self):
        return StringIO.StringIO(self.camera.capture_preview().get_data())
    
    def capture_image(self, image_name):
        self.camera.capture_image(image_name)

class DebugCamera():
    def capture_preview(self):
        with open('preview.jpg', 'rb') as img:
            return StringIO.StringIO(img.read())
    
    def capture_image(self, image_name):
        print "Captured an image!", image_name

class PhotoBooth(object):
    def __init__(self, fullscreen=False, debug=True):
        self.debug = debug
        if debug:
            self.camera = DebugCamera()
        else:
            self.camera = Camera()
        self.size = None
        self.fullscreen = fullscreen
        self.events = []
        self.current_session = None

    def capture_preview(self):
        preview = self.camera.capture_preview()
        
        picture = pygame.image.load(preview)
        if self.size:
            picture = pygame.transform.scale(picture, self.size)
        return picture

    def start(self):
        preview = self.capture_preview()
        pygame.init()
        
        if self.fullscreen:
            pygame.display.set_mode((0,0), pygame.FULLSCREEN)
        else:
            pygame.display.set_mode(preview.get_size())

        self.main_surface = pygame.display.get_surface()
    
        self.size = self.main_surface.get_size()

        while self.main_loop():
            pass
        
    def main_loop(self):
        if len(self.events) > 10:
            self.events = self.events[:10]
        pygame.display.flip()
         
        button_press = self.space_pressed()
        
        if self.current_session:
            self.current_session.do_frame(button_press)
        elif button_press:
            self.current_session = PhotoSession(self)
        else:
            self.wait()
                
        return self.check_for_quit_event()

    def wait(self):
        self.render_text_centred('Waiting for button press')

    def render_text_centred(self, text_string):
        location = self.main_surface.get_rect()
        font = pygame.font.SysFont(pygame.font.get_default_font(), 142)
        text = font.render(text_string, 1, (210, 210, 210))
        textpos = text.get_rect()

        textpos.centerx = location.centerx
        textpos.centery = location.centery
        self.main_surface.blit(text, textpos)

    def load_image(self, image_name):
        if self.debug:
            image_name = "test.jpg"
        return pygame.image.load(image_name)

    def check_key_event(self, *keys):
        self.events += pygame.event.get(pygame.KEYUP)
        pygame.event.clear()
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
        self.montage_timer = -1
        self.montage_displayed = False

    def do_frame(self, button_pressed):
        if self.montage_timer > 0:
            self.display_montage()
        else:
            picture = self.booth.capture_preview()
            self.booth.main_surface.blit(picture, (0, 0))
        
        if self.timer > 0:
            self.do_countdown()
        
        if button_pressed and not self.capture_start:
            self.timer = time.time() + COUNT_DOWN_TIME + 1
            self.capture_start = datetime.datetime.now()
        
    def do_countdown(self):
        time_remaining = int(self.timer - time.time())
        
        if time_remaining <= 0:
            image_name = self.get_image_name(self.photo_count)
            self.booth.camera.capture_image(image_name)
            if self.photo_count == 4:
                self.timer = -1
                self.photo_count = 1
                self.montage_timer = time.time()
            else:
                self.timer = time.time() + COUNT_DOWN_TIME + 1
                self.photo_count += 1
        else:
            self.booth.render_text_centred(str(time_remaining))
    
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
        if time.time() - self.montage_timer > MONTAGE_DISPLAY_TIME:
            self.montage_timer = -1
            self.montage_displayed = False
    
    def get_image_name(self, count):
        return self.capture_start.strftime('%Y-%m-%d-%H%M%S') + '-' + str(count) + '.jpg'

def main():
    booth = PhotoBooth(fullscreen=False, debug=True)
    booth.start()

if __name__ == '__main__':
    main()



#### Plan
#
# 1. Start previewing
# 2. On interupt:
#  a. Start timer countdown
#  b. 
#
#
#
#
#
#
#



