import os
import cv2
import threading
import traceback

from queue import Queue, Full
from .debug import log

class VideoWriter:
    def __init__(self, _framerate, _resolution, _vid_dir):
        self.running = True
        self.q = Queue(maxsize=3000)
        self.framerate = _framerate
        self.resolution = _resolution
        self.vid_dir = _vid_dir
        self.m_thread = threading.Thread(target=self.write_video, args=())
        self.m_thread.start()
        log("[STAT] init success")
        log(self.resolution)

    def signal_termination(self):
        self.schedule_frame_write(None)
        self.running = False
        log("[STAT] signaled termination")


    def deinit(self):
        """
        returns whether the worker thread is alive or not
        """
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
            return True
        except Full:
            log("[PROD] queue is full")
            return False

    def write_video(self):
        log("[CONS] thread started")
        video = None # sentinel for end of video
        while self.running:
            frame_info = self.q.get()
            log("[CONS] WRITING")
        # try:
            if frame_info is None: # end of a video
                video.release()
                log("[CONS] video saved: ")
                video = None
            elif video is None: # start of a video
                
                video = cv2.VideoWriter(os.path.join(self.vid_dir, frame_info[1]+".avi"), cv2.VideoWriter_fourcc(*"MJPG"), 
                        self.framerate, self.resolution)
                log("[CONS] video writer started: " + frame_info[1])
                video.write(frame_info[0])
            else:
                video.write(frame_info[0])
        # except Exception: # corrupted?
        #     log('[CONS] exception while writing video: ' + traceback.format_exc())
        #     video = None
        
        if video is not None:
            video.release()
