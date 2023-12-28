import os
import re
import shutil

import requests

from viper.flash import flash


def download(
        link,
        path,
        filename=None,
        parallel=True,
        headers=None,
        max_workers=8
):
    is_chunk_file = False

    # If chunk already exists and valid, save any kind of computation or io
    chunk_file_name_preset = 'downloaded_chunk_file'
    if filename is not None and filename.startswith(chunk_file_name_preset):
        is_chunk_file = True
        expected_chunk_size = int(filename.split('_')[4]) - int(filename.split('_')[3]) + 1
        chunk_path = os.path.join(path, filename)
        if (os.path.exists(chunk_path) and os.path.isfile(chunk_path)
                and os.stat(chunk_path).st_size == expected_chunk_size):
            return chunk_path

    response = requests.get(link, stream=True, headers=headers)

    if filename is None:
        filename = re.findall(r'filename=(\s+)', response.headers['Content-Disposition'])[0].strip(' ').strip('"')

    file_path = os.path.join(path, filename)
    total_size = int(response.headers.get('content-length', 0))

    start = 0
    if os.path.exists(file_path) and os.path.isfile(file_path):
        start = os.stat(file_path).st_size

    if start >= total_size:
        return file_path

    accepts_range = 'bytes' in response.headers.get('accept-ranges', 'None') or is_chunk_file
    if parallel and accepts_range:
        partial_dir = os.path.join(path, f'{filename}_partial')

        chunk_size = max(total_size // max_workers, 10485760)
        chunk_args = []

        while start < total_size:
            end = min(start + chunk_size - 1, total_size - 1)
            expected_chunk_size = (end - start) + 1
            chunk_name = f'{chunk_file_name_preset}_{start}_{end}'
            chunk_args.append((chunk_name, {'Range': f'bytes={start}-{end}'}))
            start += expected_chunk_size

            # break

        flash(
            fn=lambda p: download(link, partial_dir, filename=p[0], parallel=False, headers=p[1]),
            args=chunk_args,
            max_workers=max_workers
        )

        fp1 = open(os.path.join(path, filename), 'wb')
        for chunk_name, _ in chunk_args:
            fp2 = open(os.path.join(partial_dir, chunk_name), 'rb')
            fp1.write(fp2.read())
            fp2.close()
        fp1.close()

        shutil.rmtree(partial_dir)
    else:
        os.makedirs(path, exist_ok=True)
        block_size = 4096

        write_mode = 'wb'
        if start > 0 and accepts_range:
            end = total_size
            if is_chunk_file:
                start = start + int(filename.split('_')[3])
                end = int(filename.split('_')[4])
            write_mode = 'ab'
            response = requests.get(link, stream=True, headers={'Range': f'bytes={start}-{end}'})

        with open(file_path, write_mode) as file:
            for data in response.iter_content(block_size):
                file.write(data)

    return file_path


if __name__ == '__main__':
    download(
        'http://some/link',
        'downloads',
        parallel=True,
        filename='test.mp4'
    )
