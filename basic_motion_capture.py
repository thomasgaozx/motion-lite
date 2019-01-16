import threading
import datetime
import time
import cv2

from . import constants
from queue import Queue, Full
from .video_writer import VideoWriter
from .debug import log

def resized(img):
    """
    resize the image to a 360p for faster processing
    """
    return cv2.resize(img, (360, constants.DEFAULT_RESIZED_HEIGHT),
            interpolation=cv2.INTER_AREA)

def process_raw_frame(raw_frame):
    return cv2.GaussianBlur(cv2.cvtColor(resized(raw_frame), cv2.COLOR_BGR2GRAY), (21, 21), 0).astype("float")

class ImageAccumulator:
    def __init__(self, _relief_dur):
        """
        description: initialize the image accumulating components
        params: `_relief_dur` is the sleeping duration for each frame processing
        when high CPU-usage is detected
        """
        self.avg = None
        self.accum_q = Queue() # image accumulator queue
        self.relief_dur = _relief_dur

        self.m_thread = None
        self.running = False

    def start(self):
        self.running = True
        self.m_thread = threading.Thread(target=self.accumulate_forever, args=())
        self.m_thread.start()
    
    def signal_termination(self):
        self.running = False
        self.accum_q.put(None)
    
    def deinit(self):
        self.signal_termination()
        self.m_thread.join(timeout=2)
        return not self.m_thread.is_alive()
    
    def no_initial_frame(self):
        return self.avg is None

    def set_initial_frame(self, frame):
        self.avg = frame

    def schedule_raw_frame_accum(self, raw_frame):
        try:
            self.accum_q.put_nowait((raw_frame, True))
            return True
        except Full:
            return False

    def schedule_processed_frame_accum(self, processed_frame):
        try:
            self.accum_q.put_nowait((processed_frame, False))
            return True
        except Full:
            return False

    def accumulate_forever(self):
        while self.running:
            tup = self.accum_q.get()
            if tup is None: return

            if tup[1]: # is a raw frame
                if self.accum_q.qsize() > 100:
                    for i in range(95): # congestion
                        self.accum_q.get() # should not block!
                else:
                    time.sleep(self.relief_dur) # to spread the workload
                cv2.accumulateWeighted(process_raw_frame(tup[0]), self.avg, 0.5)
            else: # is a fully-processed frame
                cv2.accumulateWeighted(tup[0], self.avg, 0.5)

class BaseMotionCapture:
    def __init__(self, _conf):
        self.conf = _conf
        self.vid_writer = VideoWriter(_conf)
        self.accumulator = ImageAccumulator(0.95 / self.conf.fps)
        self.accumulator.start()
        self.last_started = None

    def process_frame(self, f):
        """ process an incoming frame """
        raw_frame = f.array
        timestamp = datetime.datetime.now()

        if self.accumulator.no_initial_frame():
            self.accumulator.set_initial_frame(process_raw_frame(raw_frame))
            return True

        # log("[MAIN] accumulateWeighted")
        ts = timestamp.strftime("%B %d %I:%M:%S%p")

        if self.is_writing() and (timestamp - self.last_started).seconds < self.conf.min_recording_period:
            if not self.is_read_override_disallowed():
                time.sleep(0.03) # to spread the workload, give read the priority
            self.accumulator.schedule_raw_frame_accum(raw_frame)
            self.vid_writer.schedule_frame_write((raw_frame, ts))
            return True

        # process the image
        frame = resized(raw_frame)
        gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)
        self.accumulator.schedule_processed_frame_accum(gray)

        # signal stop recording / continue recording
        if self.is_occupied(gray):
            log("[ALERT] is_writing started/renewed")
            self.vid_writer.write_lock.write_lock()
            self.vid_writer.schedule_frame_write((raw_frame, ts))
            self.last_started = timestamp
        elif self.is_writing():
            log("[ALERT] finished recording")
            self.vid_writer.write_lock.write_unlock()
            self.vid_writer.schedule_frame_write(None)

        # check to see if the frames should be displayed to screen
        if self.conf.show_video:
            # draw the timestamp on the frame
            cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

            cv2.imshow("Security Feed", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                log("[ALERT] quitting ...")
                return False
        
        return True
    
    def is_writing(self):
        """ not protected by any lock! """
        return self.vid_writer.write_lock.is_writing
    
    def is_read_override_disallowed(self):
        """ not protected by any lock! """
        return self.vid_writer.write_lock.disallow_read_override

    def is_occupied(self, gray):
        """ returns `True` if there is motion, `False` otherwise. """
        _frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(self.accumulator.avg))

        # threshold the delta image, dilate the thresholded image to fill in holes
        thresh = cv2.threshold(_frame_delta, self.conf.delta_thresh, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        # -2 is the position of the contour tuple from findContours
        contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        for c in contours:
            if cv2.contourArea(c) > self.conf.min_area:
                return True
        
        return False
