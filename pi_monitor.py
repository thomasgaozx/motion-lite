from picamera.array import PiRGBArray
from picamera import PiCamera

from .video_writer import VideoWriter
from . import helper
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
conf = json.load(open(args["conf"]))

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
# uploaded timestamp, and frame motion counter
print("[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])
avg = None

vid_writer = VideoWriter(fps, res)
is_writing = False
last_started = None

# capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    # grab the raw NumPy array representing the image and initialize
    # the timestamp and occupied/unoccupied text
    # log("[MAIN] fetch raw frame and timestamp")
    raw_frame = f.array
    timestamp = datetime.datetime.now()

    # resize the frame, convert it to grayscale, and blur it
    # log("[MAIN] resize and blur secondary frame")
    frame = resize(raw_frame, width=500)
    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)

    # if the average frame is None, initialize it
    if avg is None:
        # log("[MAIN] starting background model...")
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue

    # log("[MAIN] accumulateWeighted")
    cv2.accumulateWeighted(gray, avg, 0.5)

    if is_writing and (timestamp - last_started).seconds < min_recording_period:
        vid_writer.schedule_frame_write((raw_frame, ts))
        rawCapture.truncate(0)
        continue

    # get contours
    # log("[MAIN] detect motions and get contours")
    cnts = helper.detect_motions(gray, avg, delta_thresh)

    # draw contours
    occupied = helper.draw_contours(frame, cnts, min_area)

    # draw the text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    cv2.putText(frame, "Occupied: " + str(occupied), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    if occupied:
        log("[ALERT] is_writing renewed")
        # write the image to temporary file
        is_writing = True
        vid_writer.schedule_frame_write((raw_frame, ts))
        last_started = timestamp
    elif is_writing:
        is_writing = False
        vid_writer.schedule_frame_write(None)

    # check to see if the frames should be displayed to screen
    if show_video and helper.display_frame(frame):
        break

    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)

# final cleanup
vid_writer.deinit()
cv2.destroyAllWindows()