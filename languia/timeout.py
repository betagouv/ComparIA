import concurrent.futures
import threading

class TimeoutException(Exception):
    """Raised when the timeout is reached."""
    pass

class TimeoutIterator:
    """Wrap the iterator with a timeout."""
    def __init__(self, iterator, timeout):
        self.iterator = iterator
        self.timeout = timeout
        self.exception = None
        self.future = None

    def __iter__(self):
        return self

    def __next__(self):
        if self.future is None:
            self.future = concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(next, self.iterator)
            self.exception = None
        try:
            return self.future.result(timeout=self.timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutException("Timeout reached")
        except Exception as e:
            self.exception = e
            raise
        finally:
            self.future = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.exception:
            raise self.exception

# Usage
timeout = 10  # seconds
