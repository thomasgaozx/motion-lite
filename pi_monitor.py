from picamera.array import PiRGBArray
from picamera import PiCamera

from . import helper
import warnings
import datetime
import dropbox
import json
import time
import cv2
import os

from .convenience import resize, grab_contours

# construct the argument parser and parse the arguments
args = helper.parse_args()

# filter warnings, load the configuration
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

# Set up path to write videos
show_video = conf["show_video"]
min_area = conf["min_area"]
delta_thresh = conf["delta_thresh"]
video_path = conf["video_path"]
if not os.path.isdir(video_path):
    raise Exception(video_path + " doesn't exist!")

# allow the camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print("[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])
avg = None

# capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    # grab the raw NumPy array representing the image and initialize
    # the timestamp and occupied/unoccupied text
    frame = f.array
    timestamp = datetime.datetime.now()

    # resize the frame, convert it to grayscale, and blur it
    frame = resize(frame, width=500)
    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)

    # if the average frame is None, initialize it
    if avg is None:
        print("[INFO] starting background model...")
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue

    # accumulate the weighted average between the current frame and
    # previous frames, then compute the difference between the current
    # frame and running average
    cv2.accumulateWeighted(gray, avg, 0.5)

    # get contours
    cnts = helper.detect_motions(gray, avg, delta_thresh)

    # draw contours
    occupied = helper.draw_contours(frame, cnts, min_area)

    # draw the text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    cv2.putText(frame, "Occupied: " + str(occupied), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

    # check to see if the room is occupied
    if occupied:
        # check to see if enough time has passed between uploads

        # check to see if the number of frames with consistent motion is
        # high enough
        if motionCounter >= conf["min_motion_frames"]:
            # write the image to temporary file
            cv2.imwrite("{base_path}/{ts}{ext}".format(base_path=video_path, 
                ts=timestamp.strftime("%A %d %B %Y %I:%M:%S%p"), ext=".jpg"), frame)

            # upload the image to Dropbox and cleanup the tempory image
            print("[SAVED] {}".format(ts))

    # otherwise, the room is not occupied
    else:
        motionCounter = 0

    # check to see if the frames should be displayed to screen
    if show_video and helper.display_frame(frame):
        break

    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)
