
import piggyphoto
import pygame
import StringIO
import time
import logging

logger = logging.getLogger('photobooth.cameras')

# Currently unused
#CAPTURE_SHUTTER_SPEED = '1/200'
#DEFAULT_PREVIEW_SHUTTER_SPEED = '1'

#CAPTURE_APERTURE = '8'
#DEFAULT_PREVIEW_APERTURE = '1.8'

class Camera(object):
    def __init__(self):
        self.camera = piggyphoto.camera()
        self.reset_settings()

        #self.camera.config.main.actions.autofocusdrive=True
        #self.camera.config.main.actions.manualfocusdrive=2
        #qq self.camera.leave_locked()

    def try_set_capturesettings(self, setting):
        for x in range(0, 10):
            try:
                con = self.camera.config
                con.main.capturesettings.autoexposuremode.value = setting
                self.camera.config = con
                if x > 0:
                    logger.info("Set capture settings after %d attempts", x)
                return
            except Exception, e:
                logger.exception("Failed to set capturesettings, attempt %d", x)
                if x >= 9:
                    raise e
                else:
                    time.sleep(x/2)
                if x > 4 and x % 2 == 1:
                    del self.camera
                    self.camera = piggyphoto.camera()

    def reset_settings(self):
        self.try_set_capturesettings('AV')
        #self.camera.config.main.capturesettings.shutterspeed.value = DEFAULT_PREVIEW_SHUTTER_SPEED
        #self.camera.config.main.capturesettings.aperture.value = DEFAULT_PREVIEW_APERTURE

    def set_settings_for_capture(self):
        self.try_set_capturesettings('Manual')
        #self.camera.config.main.capturesettings.shutterspeed.value = CAPTURE_SHUTTER_SPEED
        #self.camera.config.main.capturesettings.aperture.value = CAPTURE_APERTURE

    def capture_preview(self):
        if not self.camera:
            self.camera = piggyphoto.camera()
            logger.debug("Created new camera")
        return pygame.image.load(StringIO.StringIO(self.camera.capture_preview().get_data()))

    def capture_image(self, image_path):
        # Kludge - keep trying to capture the image
        # gphoto throws exceptions if for example the camera can't focus
        for x in range(0, 5):
            try:
                if hasattr(self, 'camera'):
                    # Delete the camera object. This causes the mirror to close, otherwise
                    # we don't get autofocus!
                    del self.camera
                self.camera = piggyphoto.camera()

                self.set_settings_for_capture()
                self.camera.capture_image(image_path)
                self.reset_settings()

                if x > 0:
                    logger.info("Captured image after %d attempts", x)
                return
            except Exception, e:
                logger.exception("Failed to capture image, attempt %d", x)
                if x >= 4:
                    if hasattr(self, 'camera'):
                        # Release the camera. Hopefully its more likely to work after a restart
                        del self.camera
                    raise e
                else:
                    time.sleep(x)

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
        logger.info("Sleep!")

class DebugCamera():
    def capture_preview(self):
        with open('preview.jpg', 'rb') as img:
            return pygame.image.load(StringIO.StringIO(img.read()))

    def capture_image(self, image_path):
        time.sleep(0.5)
        logger.info("Captured an image: %s", image_path)

    def sleep(self):
        logger.info("Sleep!")