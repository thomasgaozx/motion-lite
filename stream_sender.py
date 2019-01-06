import socket
import json
from .arr_manip import deserialize, serialize
from .messaging.message import Message

SERVER_PORT = 23949

class StreamSender:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect("127.0.0.1", SERVER_PORT)
    
    def send_frame(self, frame, date_str):
        self.sock.send(Message(0, serialize(frame, date_str)).encode())

    def cut_video(self):
        self.sock.send(Message(0, json.dumps(None)).encode())