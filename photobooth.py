#!/usr/bin/env python

import piggyphoto, pygame
import os, sys
import time, datetime
import StringIO
from subprocess import call

COUNT_DOWN_TIME = 1
MONTAGE_DISPLAY_TIME = 2

class Camera(object):
    def __init__(self):
        self.camera = piggyphoto.camera()
        #qq self.camera.leave_locked()
    
    def capture_preview(self):
        return StringIO.StringIO(self.camera.capture_preview().get_data())
    
    def capture_image(self, image_path):
        self.camera.capture_image(image_path)

class DebugCamera():
    def capture_preview(self):
        with open('preview.jpg', 'rb') as img:
            return StringIO.StringIO(img.read())
    
    def capture_image(self, image_path):
        print "Captured an image!", image_path

class PhotoBooth(object):
    def __init__(self, image_dest, fullscreen, debug, printing):
        self.debug = debug
        if debug:
            self.camera = DebugCamera()
        else:
            self.camera = Camera()
            
        self.printing = printing
            
        self.output_dir = image_dest
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
        self.clock = pygame.time.Clock()
        
        if self.fullscreen:
            pygame.display.set_mode((0,0), pygame.FULLSCREEN)
        else:
            pygame.display.set_mode(preview.get_size())

        self.main_surface = pygame.display.get_surface()
    
        self.size = self.main_surface.get_size()

        while self.main_loop():
            pass
        
    def main_loop(self):
        pygame.event.clear()
        self.clock.tick(25)
        if len(self.events) > 10:
            self.events = self.events[:10]
        pygame.display.flip()
         
        button_press = self.space_pressed()
        
        if self.current_session:
            if self.current_session.do_frame(button_press):
                self.current_session = None
        elif button_press:
            self.current_session = PhotoSession(self)
        else:
            self.wait()
                
        return self.check_for_quit_event()

    def wait(self):
        self.main_surface.fill((0,0,0))
        self.render_text_centred('Waiting for button press')

    def render_text_centred(self, text_string):
        location = self.main_surface.get_rect()
        font = pygame.font.SysFont(pygame.font.get_default_font(), 142)
        text = font.render(text_string, 1, (210, 210, 210))
        textpos = text.get_rect()

        textpos.centerx = location.centerx
        textpos.centery = location.centery
        self.main_surface.blit(text, textpos)

    def capture_image(self, file_name):
        self.camera.capture_image(os.path.join(self.output_dir, file_name))

    def load_image(self, image_name):
        if self.debug:
            image_path = "test.jpg"
        else:
            image_path = os.path.join(self.output_dir, file_name)
        return pygame.image.load(image_path)

    def save(self, out_name, images):
        out_path = os.path.join(self.output_dir, out_name)
        first = self.load_image(images[0])
        size = (first.get_size()[0]/2, first.get_size()[1]/2)
        print size
        combined = pygame.Surface(first.get_size())
        for count, image_name in enumerate(images):
            image = self.load_image(image_name)
            image = pygame.transform.scale(image, size)
            x_pos = size[0] * (count % 2)
            y_pos = size[1] * (1 if count > 1 else 0)
            print x_pos, y_pos
            combined.blit(image, (x_pos, y_pos))
        pygame.image.save(combined, out_path)
        
        if self.printing:
            call(["lpr", out_path])
        
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
        self.montage_timer = -1
        self.montage_displayed = False
        self.finished = False
        self.saved_image = False

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
            
        return self.finished
        
    def do_countdown(self):
        time_remaining = int(self.timer - time.time())
        
        if time_remaining <= 0:
            image_name = self.get_image_name(self.photo_count)
            self.booth.capture_image(image_name)
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
        elif not self.saved_image:
            self.booth.save(self.get_image_name('combined'), [self.get_image_name(im) for im in range(1,5)])
            self.saved_image = True
            
        if time.time() - self.montage_timer > MONTAGE_DISPLAY_TIME:
            self.montage_timer = -1
            self.montage_displayed = False
            self.finished = True
    
    def get_image_name(self, count):
        return self.capture_start.strftime('%Y-%m-%d-%H%M%S') + '-' + str(count) + '.jpg'

def main():
    booth = PhotoBooth('', fullscreen=False, debug=True, printing=False)
    booth.start()

if __name__ == '__main__':
    main()



#### Plan
#
#
#
#
#
#
#
#



