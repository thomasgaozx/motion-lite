import threading

def log(msg):
    if is_debug: 
        with _console_lock:
            print(msg)

def set_debug(d):
    global is_debug
    is_debug = d

_console_lock = threading.Lock()
is_debug = False