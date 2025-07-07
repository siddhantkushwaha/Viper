"""
Author: Siddhant Kushwaha

File-based locking mechanism.
Takes lock_name and lock_dir as arguments.
"""

import atexit
import os
import signal
import sys
import tempfile
import time

_temp_dir = tempfile.gettempdir()


class FileLock:
    """A file-based locking mechanism to prevent multiple instances of a process"""

    def __init__(self, lock_name, lock_dir=_temp_dir):
        """
        Initialize the file lock

        Args:
            lock_name (str): Name for the lock file (without extension)
            lock_dir (str): Directory where lock file will be created
        """
        self.lock_name = lock_name
        self.lock_file = os.path.join(lock_dir, f"{lock_name}.lock")
        self.acquired = False

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
                os.remove(self.lock_file)
            except OSError:
                pass
            self.acquired = False

    def _signal_handler(self, signum, frame):
        """Handle signals for graceful cleanup"""
        print(f"\nReceived signal {signum}, cleaning up...")
        sys.exit(0)

    def _try_acquire_once(self):
        """
        Try to acquire lock once (internal method)

        Returns:
            bool: True if lock acquired successfully, False otherwise
        """
        if os.path.exists(self.lock_file):
            try:
                with open(self.lock_file, "r") as f:
                    existing_pid = int(f.read().strip())

                if self._is_process_running(existing_pid):
                    print(
                        f"Another instance with lock '{self.lock_name}' is already running (PID: {existing_pid})"
                    )
                    return False
                else:
                    print(f"Found stale lock file for PID {existing_pid}, removing it.")
                    os.remove(self.lock_file)
            except (ValueError, IOError):
                print("Found corrupted lock file, removing it.")
                try:
                    os.remove(self.lock_file)
                except OSError:
                    pass

        # Create lock file with current PID atomically
        try:
            # Ensure lock directory exists
            os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)

            # Use O_CREAT | O_EXCL for atomic creation - fails if file exists
            fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            try:
                os.write(fd, str(os.getpid()).encode())
            finally:
                os.close(fd)

            print(f"Lock '{self.lock_name}' acquired (PID: {os.getpid()})")
            self.acquired = True

            # Register cleanup function
            atexit.register(self._cleanup_lock)

            # Handle signals for graceful cleanup
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)

            return True

        except FileExistsError:
            # Another process created the lock file between our check and creation
            print(
                f"Lock '{self.lock_name}' was created by another process during acquisition"
            )
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
