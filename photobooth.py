import piggyphoto, pygame
import os, sys
import time, datetime
import StringIO

class PhotoBooth(object):
    def __init__(self, fullscreen=False):
        self.camera = piggyphoto.camera()
        #self.camera.leave_locked()
        self.size = None
        self.fullscreen = fullscreen
        self.timer = -1
        self.photo_count = 1
        self.capture_start = None
        self.montage_timer = -1
        self.montage_displayed = False

    def capture_preview(self):
        preview = self.camera.capture_preview()
        picture = pygame.image.load(StringIO.StringIO(preview.get_data()))
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

        while True:
            self.main_loop()
        
    def main_loop(self):
        if self.montage_timer > 0:
            self.display_montage()
        else:
            picture = self.capture_preview()
            self.main_surface.blit(picture, (0, 0))
        
        if self.timer > 0:
            self.do_countdown()
        pygame.display.flip()
        self.check_event()

    def do_countdown(self):
        time_remaining = int(self.timer - time.time())
        
        if time_remaining <= 0:
            image_name = self.get_image_name(self.photo_count)
            self.camera.capture_image(image_name)
            if self.photo_count == 4:
                self.timer = -1
                self.photo_count = 1
                self.montage_timer = time.time()
                # print
            else:
                self.timer = time.time() + 4
                self.photo_count += 1
        else:
            self.render_text_centred(str(time_remaining), self.main_surface.get_rect())
    
    def display_montage(self):
        if not self.montage_displayed:
            for im in range(1, 5):
                image = pygame.image.load(self.get_image_name(im))
                size = (self.size[0]/2, self.size[1]/2)
                image = pygame.transform.scale(image, size)
                x_pos = size[0] * ((im - 1) % 2)
                y_pos = size[1] * (1 if im > 2 else 0)
                self.main_surface.blit(image, (x_pos, y_pos))
            self.montage_displayed = True
        if time.time() - self.montage_timer > 8:
            self.montage_timer = -1
            self.montage_displayed = False
    
    def get_image_name(self, count):
        return self.capture_start.strftime('%Y-%m-%d-%H%M%S') + '-' + str(count) + '.jpg'
            
    def render_text_centred(self, text_string, location):
        font = pygame.font.SysFont(pygame.font.get_default_font(), 142)
        text = font.render(text_string, 1, (210, 210, 210))
        textpos = text.get_rect()

        textpos.centerx = location.centerx
        textpos.centery = location.centery
        self.main_surface.blit(text, textpos)

    def check_event(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYUP and event.dict['key'] == pygame.K_q:
                sys.exit()
            elif event.type == pygame.KEYUP and event.dict['key'] == pygame.K_SPACE:
                self.timer = time.time() + 5
                self.capture_start = datetime.datetime.now()

def main():
    booth = PhotoBooth(fullscreen=True)
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



