import enum
import json
from .constants import PREFIX_LEN
from .message import Message

class MessageDecodeStatus(enum.Enum):
    DecodingPrefix = 0 # received buffer, decoding prefix
    DecodingHeader = 1
    DecodingPayload = 2
    Corrupted = -1 # e.g. exceptions, missing segments, timeout ... socket should be closed then

class MessageDecode:
    """
    a state machine that handles incoming buffer and yield decoded messages
    
    fields: `int prefix`, `list<int> header`, `string payload`, `binary buffer`
    """
    def __init__(self):
        self.state = MessageDecodeStatus.DecodingPrefix
        self.prefix = -1
        self.header = list()
        self.payload = ""
        self.buffer = b''

    def handlebuffer(self, buf):
        """
        description: continue stepping through each decoding process
        yields: Message objects for each decoded message
        """
        if not buf:
            return

        self.buffer += buf

        while self.state != MessageDecodeStatus.Corrupted: # continue decoding if each step makes progress
            if self.state == MessageDecodeStatus.DecodingPrefix and not self.parse_prefix():
                return
            if self.state == MessageDecodeStatus.DecodingHeader and not self.parse_header():
                return
            if self.state == MessageDecodeStatus.DecodingPayload and not self.parse_payload():
                return
            yield Message(self._get_msg_type(),self.payload)

    def is_corrupted(self):
        return self.state == MessageDecodeStatus.Corrupted

    def _get_msg_type(self):
        return self.header[0]

    def _get_payload_len(self):
        if len(self.header) == 2:
            return self.header[1]
        return -1

    def reset_state(self):
        self.state = MessageDecodeStatus.DecodingPrefix

    def parse_prefix(self):
        """
        assumptions: self in DecodingPrefix state
        returns: `True` if state is updated, `False` otherwise
        """
        try:
            if len(self.buffer) >= PREFIX_LEN:
                self.prefix = int(self.buffer[:PREFIX_LEN]) # emits ValueError
                self.buffer = self.buffer[PREFIX_LEN:]
                self.state = MessageDecodeStatus.DecodingHeader
                return True
        except ValueError as e:
            self.state = MessageDecodeStatus.Corrupted
        return False

    def parse_header(self):
        try:
            if len(self.buffer) >= self.prefix:
                self.header = json.loads(self.buffer[:self.prefix]) # emits JSONDecodeError
                self.buffer = self.buffer[self.prefix:]
                self.state = MessageDecodeStatus.DecodingPayload
                return True
        except json.JSONDecodeError as e:
            self.state = MessageDecodeStatus.Corrupted
        return False

    def parse_payload(self):
        """
        description: parse payload
        """
        try:
            if len(self.buffer) >= self._get_payload_len():
                self.payload = self.buffer[:self._get_payload_len()].decode("utf-8")
                self.buffer = self.buffer[self._get_payload_len():]
                self.reset_state()
                return True
        except Exception as e: # for consistency's sake
            self.state = MessageDecodeStatus.Corrupted
        return False
