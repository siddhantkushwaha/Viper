"""
Author: Siddhant Kushwaha

To take lock across threads and process.
"""

import os
import tempfile
import threading
import time

_temp_dir = tempfile.gettempdir()


class NamedLock:
    """A file-based locking mechanism to prevent multiple instances of a process"""

    # Class-level dict to maintain thread-level locks per lock file
    _thread_locks = {}

    # For synchronizing access to _thread_locks
    _thread_locks_lock = threading.Lock()

    def __init__(self, lock_name):
        """
        Initialize the file lock

        Args:
            lock_name (str): Name for the lock file (without extension)
        """
        self.pid = os.getpid()
        self.lock_name = lock_name
        self.lock_file = os.path.join(_temp_dir, f"{lock_name}.lock")

        # Thread-level lock specific to this lock_name
        with NamedLock._thread_locks_lock:
            if self.lock_file not in NamedLock._thread_locks:
                NamedLock._thread_locks[self.lock_file] = threading.Lock()
            self._thread_lock = NamedLock._thread_locks[self.lock_file]

        self.acquired = False

    def __del__(self):
        self._cleanup_lock()

    def _is_process_running(self, pid):
        """Check if a process with given PID is running"""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _cleanup_lock(self):
        """Remove lock file on exit"""
        if self.acquired and os.path.exists(self.lock_file):
            try:
                self._thread_lock.release()
                os.remove(self.lock_file)
            except:
                pass

            print(f"Lock '{self.lock_name}' released (PID: {self.pid})")
            self.acquired = False

    def _try_acquire_once(self):
        """
        Try to acquire lock once (internal method)

        Returns:
            bool: True if lock acquired successfully, False otherwise
        """

        acquired_thread_lock = self._thread_lock.acquire(blocking=False)
        if not acquired_thread_lock:
            print(f"Lock '{self.lock_name}' already held on different thread.")
            return False

        if os.path.exists(self.lock_file):
            try:
                with open(self.lock_file, "r") as f:
                    existing_pid = int(f.read().strip())

                if existing_pid == self.pid:
                    print(f"Lock '{self.lock_name}' is already held by this process (PID: {existing_pid})")
                    self.acquired = True
                    return True
                elif self._is_process_running(existing_pid):
                    print(f"Lock '{self.lock_name}' already held by PID: {existing_pid}")
                    return False
                else:
                    os.remove(self.lock_file)
            except:
                pass

        # Create lock file with current PID atomically
        try:
            # Ensure lock directory exists
            os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)

            # Use O_CREAT | O_EXCL for atomic creation - fails if file exists
            fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            try:
                os.write(fd, str(self.pid).encode())
            finally:
                os.close(fd)

            print(f"Lock '{self.lock_name}' acquired (PID: {self.pid})")
            self.acquired = True

            return True

        except FileExistsError:
            # Another process created the lock file between our check and creation
            print(f"Lock '{self.lock_name}' was created by another process during acquisition")
            return False
        except IOError as e:
            print(f"Failed to create lock file '{self.lock_name}': {e}")
            return False

    def acquire(self, wait_for_lock=True, timeout=3600, poll_interval=1):
        """
        Acquire exclusive lock

        Args:
            wait_for_lock (bool): If True, wait for lock to become available
            timeout (float): Maximum time to wait in seconds (None = wait forever)
            poll_interval (float): Time between lock acquisition attempts in seconds

        Returns:
            bool: True if lock acquired successfully, False otherwise
        """
        if not wait_for_lock:
            return self._try_acquire_once()

        # Waiting mode with timeout
        start_time = time.time()

        while True:
            if self._try_acquire_once():
                return True

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    print(
                        f"Timeout after {timeout} seconds waiting for lock '{self.lock_name}'"
                    )
                    return False

            # Wait before next attempt
            time.sleep(poll_interval)

    def release(self):
        """Manually release the lock"""
        self._cleanup_lock()

    def __enter__(self):
        """Context manager entry - uses default acquire() behavior (no waiting)"""
        if not self.acquire(wait_for_lock=False):
            raise RuntimeError(f"Failed to acquire lock '{self.lock_name}'")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
