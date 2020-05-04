import multiprocessing
from multiprocessing.dummy import Pool as ThreadPool
import time
def abortable_worker(func, *args, **kwargs):
    timeout = kwargs.get('timeout', None)
    p = ThreadPool(1)
    res = p.apply_async(func, args=args)
    try:
        out = res.get(timeout)  # Wait timeout seconds for func to complete.
        return out
    except multiprocessing.TimeoutError:
        p.terminate()
        return [(time.time(), args[0][0], args[0][1], args[0][2], timeout, -10)]


