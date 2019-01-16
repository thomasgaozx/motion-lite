import json
import os

class Configuration:
    def __init__(self, conf_path):
        conf = None
        if conf_path:
            conf = json.load(open(conf_path))
        else:
            conf = json.load(open("/home/pi/motion_lite/conf.json")) # by default
        
        conf = json.load(open(conf_path))
        self.show_video = conf["show_video"]
        self.delta_thresh = conf["delta_thresh"]
        self.resolution = tuple(conf["resolution"])
        self.fps = conf["fps"]
        self.min_recording_period = conf["min_recording_period"]
        self.video_path = conf["video_path"]
        self.min_area = conf["min_area"]
        self.debug = conf["debug"]
        self.vflip = conf["horizontal-flip"]

    def verify(self):
        if not os.path.isdir(self.video_path):
            raise Exception(self.video_path + " doesn't exist!")
