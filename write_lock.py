import threading

class WriteLock:
    """
    Applicable to 1 writer and multiple reader
    1) while writing, reading is not allowed
    2) while reading, writing is allowed, the on-going reading operation will complete
    before being blocked again
    3) writing can occur *while* reading
    """
    def __init__(self):
        self.cv = threading.Condition()
        self.is_writing = False
    
    def read_check(self):
        if self.is_writing:
            with self.cv:
                if self.is_writing:
                    self.cv.wait()

    def write_lock(self):
        with self.cv:
            self.is_writing = True
    
    def write_unlock(self):
        with self.cv:
            self.is_writing = False
            self.cv.notify_all()