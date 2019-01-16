import time

from .basic_motion_capture import BaseMotionCapture

from picamera.array import PiRGBArray
from picamera import PiCamera

class PiMotionCapture(BaseMotionCapture):
    """ decouples dependencies for picamera API """
    def __init__(self, _conf):
        super(PiMotionCapture, self).__init__(_conf)

        self.camera = PiCamera()
        self.camera.vflip = self.conf.vflip
        self.camera.resolution = self.conf.resolution
        self.camera.framerate = self.conf.fps
        self.raw_capture = PiRGBArray(self.camera, size=self.conf.resolution)

    def capture_forever(self):
        time.sleep(1.5)

        for f in self.camera.capture_continuous(self.raw_capture,
                format="bgr", use_video_port=True):
            if not self.process_frame(f): break

            self.raw_capture.truncate(0)
