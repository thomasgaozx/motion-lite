import argparse
import warnings

from .configuration import Configuration

from . import debug
from . import helper
from .helper import resized, grab_contours
from .pi_motion_capture import PiMotionCapture

# parsing arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=False,
        help="path to the JSON configuration file")
args = vars(ap.parse_args())

warnings.filterwarnings("ignore")
conf_path = args["conf"]
if not conf_path:
    conf_path = "/home/pi/motion_lite/conf.json"

conf = Configuration(conf_path)
conf.verify()

debug.set_debug(conf.debug) # determines method of logging

motion_capture = PiMotionCapture(conf)
motion_capture.capture_forever()
