import os
import cv2
import threading
import traceback

from queue import Queue, Full
from .debug import log
from .write_lock import WriteLock

class VideoWriter:
    def __init__(self, _conf, _threshold=180, _buffer=80):
        """
        Starts the consumer thread to write videos.
        threshold is the value that when reached, write_lock's read override would be enabled.
        threshold - buffer = the number of frame when reached, write_lock's read override will be disabled.
        """
        self.running = True
        self.q = Queue(maxsize=350)
        self.conf = _conf
        self.trigger_threshold = _threshold
        self.stop_threashold = _threshold - _buffer

        self.write_lock = WriteLock()

        # init consumer thread
        self.m_thread = threading.Thread(target=self.write_video, args=())
        self.m_thread.start()
        log("[STAT] video writer init success")

    def signal_termination(self):
        self.schedule_frame_write(None)
        self.running = False
        self.write_lock.set_read_override() # force blocking action to quit
        log("[STAT] signaled termination")

    def deinit(self):
        """ returns whether the worker thread is alive or not """
        self.signal_termination()
        self.m_thread.join(timeout=2)
        log("[STAT] deinit success")
        return not self.m_thread.is_alive()

    def schedule_frame_write(self, frame):
        """
        frame is a tuple (frame, date_str)
        """
        try:
            self.q.put_nowait(frame)
            if self.q.qsize() > self.trigger_threshold:
                self.write_lock.set_read_override()
            return True
        except Full:
            log("[PROD] queue is full")
            return False

    def write_video(self):
        log("[CONS] thread started")
        video = None
        while self.running:
            self.write_lock.pending_read()

            frame_info = self.q.get()
            log("[CONS] WRITING")

        # try:
            if frame_info is None: # end of a video
                video.release()
                log("[CONS] video saved: ")
                video = None
            elif video is None: # start of a video

                video = cv2.VideoWriter(os.path.join(self.conf.video_path, frame_info[1]+".avi"), cv2.VideoWriter_fourcc(*"MJPG"),
                        self.conf.fps, self.conf.resolution)
                log("[CONS] video writer started: " + frame_info[1])
                video.write(frame_info[0])
            else:
                video.write(frame_info[0])

            if not self.write_lock.disallow_read_override and self.q.qsize() < self.stop_threashold:
                self.write_lock.unset_read_override()
        # except Exception: # corrupted?
        #     log('[CONS] exception while writing video: ' + traceback.format_exc())
        #     video = None

        if video is not None:
            video.release()
