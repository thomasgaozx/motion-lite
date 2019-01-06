import cv2
import threading

from queue import Queue, Full

class VideoWriter:
    def __init__(self, _framerate, _resolution):
        self.running = True
        self.q = Queue(maxsize=3000)
        self.framerate = _framerate
        self.resolution = _resolution
        self.m_thread = threading.Thread(target=self.write_video, args=())
        self.m_thread.start()

    def signal_termination(self):
        self.schedule_frame_write(None)
        self.running = False

    def deinit(self):
        """
        returns whether the worker thread is alive or not
        """
        self.signal_termination()
        self.m_thread.join(timeout=2)
        return not self.m_thread.is_alive()

    def schedule_frame_write(self, frame):
        """
        frame is a tuple (frame, date_str)
        """
        try:
            self.q.put_nowait(frame)
            return True
        except Full:
            return False

    def write_video(self):
        video = None # sentinel for end of video
        while self.running:
            frame_info = self.q.get()
            try:
                if frame_info is None: # end of a video
                    video.release()
                    video = None
                elif video is None: # start of a video
                    video = cv2.VideoWriter(frame_info[1]+".avi", cv2.VideoWriter_fourcc(*"MJPG"), 
                            self.framerate, self.resolution)
                    video.write(frame_info[0])
                else:
                    video.write(frame_info[0])
            except: # corrupted?
                video = None
        
        if video is not None:
            video.release()
