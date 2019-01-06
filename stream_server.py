from .messaging.multicast_server import BaseServer
from .messaging.message import Message

from .video_writer import VideoWriter
from .arr_manip import deserialize

from . import stream_sender

class StreamServer(BaseServer):
    def __init__(self, _addr, _framerate, _resolution, vid_dir):
        super(StreamServer, self).__init__(_addr, 1)
        self.vid_writer = VideoWriter(_framerate, _resolution, vid_dir)

    def process_messages(self, key, msg):
        item = deserialize(msg.payload)
        self.vid_writer.schedule_frame_write(item)

def start_stream_server(_framerate, _resolution, vid_dir):
    server = StreamServer(("127.0.0.1", stream_sender.SERVER_PORT), _framerate, _resolution, vid_dir)

    while True:
        pass # do nothing