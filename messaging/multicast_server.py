import selectors
import socket
import threading

from abc import abstractmethod

from .message_queue import MessageQueue
from .message import Message
from .message_decode import MessageDecode

class BaseServer(object):
    """
    description: a basic multicasting server, requests are queued. responses
    may be distributed sporadically through worker threads

    warning: users are expected to implement their own process_messages
    mechanisms.
    """
    def __init__(self, _addr, num_of_workers = 1):
        """
        description: initialize and start the server threads
        """
        self.request_queue = MessageQueue()
        self.sel = selectors.DefaultSelector()
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.bind(_addr)
        self.addr = self.lsock.getsockname()

        self.running = True
        self.main_thread = threading.Thread(target=self.serve_forever, args=tuple())
        self.main_thread.start()

        self.consumer_pool = list()
        for i in range(num_of_workers):
            worker_thread = threading.Thread(target=self.consume_messages, args=tuple())
            worker_thread.start()
            self.consumer_pool.append(worker_thread)

    def signal_termination(self):
        """
        description: signals all threads to stop and interrupts blocking actions,
        but does not join any threads
        """
        self.running = False
        self.request_queue.signal_termination()

        dummy_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dummy_sock.settimeout(2)
        rc = dummy_sock.connect_ex(self.addr) # should interrupt the blocking `select`
        return rc == 0

    def deinit(self):
        """
        description: signal termination and wait for all working workers to finish
        their job, and then join all threads

        warning: there is a slim possibility that main thread is not joint
        returns: True if successful, False otherwise
        """
        self.signal_termination()
        for worker_thread in self.consumer_pool:
            worker_thread.join()
        self.main_thread.join(timeout=2)

        return not self.main_thread.is_alive()

    def serve_forever(self):
        """
        [MAIN THREAD]
        description: server main thread that handles incoming connections, decode
        incoming bytes from the network buffer, then queue the requests
        """
        self.lsock.listen()
        self.lsock.setblocking(False)
        self.sel.register(self.lsock, selectors.EVENT_READ)

        # event loop
        while self.running:
            event_tuples = self.sel.select() # blocking
            for key, mask in event_tuples:
                if key.fileobj is self.lsock: # the listening socket
                    self.accept_conn(key.fileobj)
                else: # the connected socket
                    self.service_conn(key)

        # clean up
        self.sel.unregister(self.lsock)
        self.lsock.close()
        self.sel.close()

    def accept_conn(self, sock):
        """
        [MAIN THREAD]
        description: accepts a connection and register the connected socket for reading
        """
        conn, addr = sock.accept()  # should be ready to read
        conn.setblocking(False)
        event_mask = selectors.EVENT_READ
        self.sel.register(conn, event_mask, data=MessageDecode())

    def service_conn(self, key):
        """
        [MAIN THREAD]
        description: coping with incoming bytes
        """
        sock = key.fileobj
        recv_data = sock.recv(1024)
        if recv_data:
            for msg in key.data.handlebuffer(recv_data): # key.data is the msg decode state machine
                self.request_queue.enqueue((key, msg)) # i.e. (addr, msg)
        else:
            self.sel.unregister(sock)
            sock.close()

    def consume_messages(self):
        """
        [WORKER THREAD]
        description: message consumer, running on a separate thread
        """
        while self.running:
            key_msg_tup = self.request_queue.dequeue()
            if key_msg_tup is None: return

            key, msg = key_msg_tup
            self.process_messages(key, msg)

    @abstractmethod
    def process_messages(self, key, msg):
        """
        [WORKER THREAD]
        description: users are responsible for implementing their own
        version of message processing

        warning: msg may be None?
        """
        pass
