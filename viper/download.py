import os
import re
import shutil
from threading import Lock, Thread
import requests
import time
from viper.flash import flash


NETWORK_ITER_SIZE = 1024 * 1024 * 8 # 8 MB
LOCAL_COPY_BUFFER_SIZE = 1024 * 1024 * 20 # 20 MB
DEFAULT_CHUNK_SIZE = 1024 * 1024 * 200 # 200 MB
DEFAULT_MAX_WORKERS = 4

def merge(src_paths, dest_path):
    if len(src_paths) > 1:
        with open(dest_path, 'wb') as dest_file:
            for src_path in src_paths:
                with open(src_path, 'rb') as src_file:
                    shutil.copyfileobj(src_file, dest_file, length=LOCAL_COPY_BUFFER_SIZE)
                    os.remove(src_path)
    elif src_paths[0] != dest_path:
        shutil.move(src_paths[0], dest_path)


def download_chunk(file_path, range, link, supports_range, state, state_lock):
    current_file_size = os.stat(file_path).st_size if os.path.exists(file_path) else 0

    start, end = range

    # If the file already exists and is not empty, adjust the start position
    if current_file_size > 0:
        start += current_file_size
        with state_lock:
            state[1] += current_file_size

    if end < start:
        return
    
    new_headers = {}
    new_headers['Range'] = f'bytes={start}-{end}' if start < end else ''

    response = requests.get(link, stream=True, headers=new_headers)

    open_mode = 'ab' if supports_range else 'wb'
    with open(file_path, open_mode) as file:
        for data in response.iter_content(NETWORK_ITER_SIZE):
            file.write(data)
            with state_lock:
                state[1] += len(data)


def progress_thread(state, state_lock, use_bar=False):
    while True:
        with state_lock:
            total_downloaded = state[1]
            total_expected = state[0]
        
        if use_bar:
            progress = (total_downloaded / total_expected) * 100
            bar_length = 50
            filled_length = int(bar_length * progress // 100)
            bar = '=' * filled_length + '-' * (bar_length - filled_length)
            print(f'\rProgress: |{bar}| {progress:.2f}%', end='', flush=True)
            time.sleep(0.5)
        else:
            mb_downloaded = total_downloaded / (1024 * 1024)
            mb_expected = total_expected / (1024 * 1024)
            percent = (total_downloaded / total_expected) * 100 if total_expected > 0 else 0
            # print(total_downloaded, total_expected)
            print(f'Downloaded {mb_downloaded:.2f} MB of {mb_expected:.2f} MB. {percent:.2f}% complete')
            time.sleep(2)
        
        if total_downloaded >= total_expected:
            print()
            break

        
def download(
        link,
        dir_path,
        filename=None,
        parallel=True,
        chunk_size=DEFAULT_CHUNK_SIZE,
        max_workers=DEFAULT_MAX_WORKERS,
        use_bar=False
):
    response = requests.get(link, stream=True)

    if filename is None:
        filename = re.findall(r'filename=(\s+)', response.headers['Content-Disposition'])[0].strip(' ').strip('"') 

    total_size = int(response.headers.get('content-length', 0))
    
    file_path = os.path.join(dir_path, filename)

    partial_dir = os.path.join(dir_path, f'{filename}_partial')
    os.makedirs(partial_dir, exist_ok=True)

    chunk_args = []
    supports_range = 'bytes' in response.headers.get('accept-ranges', 'None')
    if supports_range and parallel:
        start = 0
        while start < total_size:
            end = min(start + chunk_size - 1, total_size - 1)
            expected_chunk_size = (end - start) + 1
            chunk_name = f'chunk_{start}_{end}'
            chunk_path = os.path.join(partial_dir, chunk_name)
            chunk_range = (start, end)
            chunk_args.append((chunk_path, chunk_range))
            start += expected_chunk_size
    else:
        # Single chunk when parallel downloads not supported or not needed
        chunk_range = (0, total_size - 1)
        chunk_args.append((file_path, chunk_range))

    state = [total_size, 0]
    state_lock = Lock()

    progress_th = Thread(target=progress_thread, args=(state, state_lock, use_bar))
    progress_th.start()
    
    # Blocking call to download chunks
    flash(
        fn=lambda arg: download_chunk(arg[0], arg[1], link, supports_range, state, state_lock),
        args=chunk_args,
        max_workers=max_workers
    )

    chunk_paths = [chunk_path for chunk_path, _ in chunk_args]
    merge(chunk_paths, file_path)

    shutil.rmtree(partial_dir)
    size = os.stat(file_path).st_size
    return file_path, size == total_size

    
if __name__ == '__main__':
    link = ''
    path = 'data'
    filename = 'test'
    pt, _ = download(
        link=link,
        dir_path=path,
        filename=filename,
        parallel=True,
        use_bar=True
    )
