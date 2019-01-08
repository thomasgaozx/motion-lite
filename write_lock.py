import threading

class WriteLock:
    """
    Applicable to 1 writer and multiple reader
    1) while writing, reading is not allowed
    2) while reading, writing is allowed, the on-going reading operation will complete
    before being blocked again
    3) writing can occur *while* reading
    4) set read_override would allow the reading to occur concurrently with writing
    """
    def __init__(self):
        self.cv = threading.Condition()
        self.is_writing = False
        self.disallow_read_override = True

    def set_read_override(self): # infrequent
        """ allow read and write to happen concurrently

        calling this method frequently may reduce performance """
        with self.cv:
            self.disallow_read_override = False
            self.cv.notify_all()

    def unset_read_override(self): # infrequent
        """ disallow read and write to happen concurrently,
            calls this after set read override """
        with self.cv:
            self.disallow_read_override = True

    def pending_read(self): # ver frequent
        """
        wait until writing stops and then proceed

        initial check may seem redundant, but since this method will be called
        frequently, a raw, cv-independent initial check will improve performance.

        Since the writing can occur while reading is still in progress, there
        is no conflict, and the race condition won't have any consequence.
        """

        # initial check
        if self.is_writing and self.disallow_read_override:
            # set read override here
            with self.cv:
                while self.is_writing and self.disallow_read_override:
                    self.cv.wait()

    def write_lock(self): # infrequent
        """ only requires once """
        with self.cv:
            self.is_writing = True

    def write_unlock(self): #infrequent
        with self.cv:
            self.is_writing = False
            self.cv.notify_all()
