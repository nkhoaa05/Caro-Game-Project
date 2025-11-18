# helper.py
import threading
import time

def safe_start_thread(target, args=(), daemon=True):
    t = threading.Thread(target=target, args=args)
    t.daemon = daemon
    t.start()
    return t

def now_ts():
    return int(time.time())
