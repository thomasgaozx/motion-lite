import threading
import collections

class MessageQueue:
    """
    description: thread-safe, like queue.Queue except one can interrupt
    blocking actions directly through `signal_termination()` instead of
    pushing a dummy item
    """
    def __init__(self, upper_cap = 1500):
        self.q = collections.deque()
        self.qcv = threading.Condition()
        self.upper_cap = upper_cap
        self.running = True

    def __len__(self):
        with self.qcv:
            return len(self.q)

    def signal_termination(self):
        with self.qcv:
            self.running = False
            self.qcv.notify_all()

    def enqueue(self, msg):
        with self.qcv:
            if len(self.q) > self.upper_cap:
                return False
            self.q.append(msg)
            self.qcv.notify_all()
        return True

    def dequeue(self):
        """
        returns: None if the queue is not running and there is no items left,
        otherwise queue item
        """
        with self.qcv:
            while self.running and len(self.q) == 0:
                self.qcv.wait()
            return self.q.pop() if len(self.q) > 0 else None

    def clear(self):
        with self.qcv:
            self.q.clear()
