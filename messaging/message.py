import json
from enum import Enum

from .constants import UTF_FORMAT, PREFIX_LEN, MAX_HEADER_SIZE

class Message:
    """
    description: a generic network messaging model
    members: msg_type should be an integer
    """
    def __init__(self, _msg_type, _payload):
        self.msg_type = _msg_type
        self.payload = _payload
    
    def __hash__(self):
        return hash((self.msg_type, self.payload))
    
    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.msg_type == other.msg_type and self.payload == other.payload

    def encode_payload(self):
        return self.payload.encode(UTF_FORMAT)

    def encode(self):
        """
        description: encode the message
        returns: encoded message if successful, empty string otherwise
        """
        e_payload = self.encode_payload()
        e_header = json.dumps([self.msg_type, len(e_payload)]).encode(UTF_FORMAT)
        e_header_len = len(e_header)
        return str(e_header_len).encode(UTF_FORMAT).zfill(PREFIX_LEN)+e_header+e_payload if e_header_len < MAX_HEADER_SIZE else ""