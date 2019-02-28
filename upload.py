
import requests
import threading
import logging

logger = logging.getLogger('photobooth.upload')

PHOTO_API_KEY = '''TODO: Your API key here'''


def upload_image_async(upload_to, file_path):
    UploadThread(upload_to, file_path).start()


class UploadThread(threading.Thread):
    def __init__(self, url, file_path):
        super(UploadThread, self).__init__()
        self.url = url
        self.file_path = file_path

    def run(self):
        logger.info("Uploading to website: %s", self.file_path)
        with open(self.file_path, 'rb') as f:
            files = {'file': f}
            headers = {'X-API-TOKEN': PHOTO_API_KEY}
            try:
                r = requests.post(self.url, files=files, headers=headers)
                r.raise_for_status()
                logger.info("Uploaded %s successfully", self.file_path)
            except Exception:
                logger.exception("Failed to upload %s. ", self.file_path)
