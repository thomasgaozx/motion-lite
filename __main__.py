from picamera.array import PiRGBArray
from picamera import PiCamera

from .video_writer import VideoWriter
from .write_lock import WriteLock
from . import helper
from queue import Queue, Full
import threading
import warnings
import datetime
import json
import time
import cv2
import os

from .debug import set_debug, log

from .convenience import resize, grab_contours

# construct the argument parser and parse the arguments
args = helper.parse_args()

# filter warnings, load the configuration
warnings.filterwarnings("ignore")

conf_path = args["conf"]
if not conf_path:
    conf_path = "/home/pi/motion_lite/conf.json"

conf = json.load(open(conf_path))

# initialize the camera and grab a reference to the raw camera capture
res = tuple(conf["resolution"])
fps = conf["fps"]
camera = PiCamera()
camera.resolution = res
camera.framerate = fps
rawCapture = PiRGBArray(camera, size=res)

# Set up path to write videos
show_video = conf["show_video"]
min_area = conf["min_area"]
delta_thresh = conf["delta_thresh"]
min_recording_period = conf["min_recording_period"]
video_path = conf["video_path"]
if not os.path.isdir(video_path):
    raise Exception(video_path + " doesn't exist!")
set_debug(conf["debug"])

# allow the camera to warmup, then initialize the average frame, last
log("[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])
avg = None

vid_writer = VideoWriter(fps, res, video_path)
last_started = None

accum_q = Queue()

def accumulate_thread():
    global avg
    global accum_q
    while True:
        gray = accum_q.get()
        cv2.accumulateWeighted(gray, avg, 0.5)

def schedule_gray_accum(gray):
    global accum_q
    try:
        accum_q.put_nowait(gray)
        return True
    except Full:
        return False

accum_thread = threading.Thread(target=accumulate_thread, args=())
accum_thread.start()

# TODO: join later && signal exit

def process_frame(f):
    global avg
    global last_started
    global min_recording_period

    raw_frame = f.array
    timestamp = datetime.datetime.now()

    frame = resize(raw_frame, width=500)
    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)

    if avg is None:
        avg = gray.copy().astype("float")
        return True

    # log("[MAIN] accumulateWeighted")
    schedule_gray_accum(gray)
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")

    if vid_writer.write_lock.is_writing and (timestamp - last_started).seconds < min_recording_period:
        vid_writer.schedule_frame_write((raw_frame, ts))
        return True

    # get contours
    # log("[MAIN] detect motions and get contours")
    cnts = helper.detect_motions(gray, avg, delta_thresh)

    # draw contours
    occupied = helper.draw_contours(frame, cnts, min_area)

    # draw the text and timestamp on the frame
    cv2.putText(frame, "Occupied: " + str(occupied), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    # signal stop recording / continue recording
    if occupied:
        log("[ALERT] is_writing started/renewed")
        vid_writer.write_lock.write_lock()
        vid_writer.schedule_frame_write((raw_frame, ts))
        last_started = timestamp
    elif vid_writer.write_lock.is_writing:
        log("[ALERT] finished recording")
        vid_writer.write_lock.write_unlock()
        vid_writer.schedule_frame_write(None)

    # check to see if the frames should be displayed to screen
    if show_video:
        cv2.imshow("Security Feed", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            log("[ALERT] quitting ...")
            return False
    
    return True
        

# capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    if not process_frame(f): break

    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)

# final cleanup
vid_writer.deinit()
cv2.destroyAllWindows()
