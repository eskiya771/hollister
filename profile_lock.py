"""Serialize manual and automatic Chromium access to the shared profile."""
import fcntl
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def profile_lock(profile):
    directory = Path(profile)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.monitor.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Browserprofil wird bereits verwendet') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
