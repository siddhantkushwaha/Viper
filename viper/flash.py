from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor


def flash(fn, args, max_workers=10):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fn, item): item for item in args}
        return as_completed(futures)
