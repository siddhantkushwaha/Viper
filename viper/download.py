import os
import re
import shutil

import requests

from viper.flash import flash


def download(link, path, filename=None, parallel=True, headers=None):
    response = requests.get(link, stream=True, headers=headers)

    filename = re.findall(r'filename=(\s+)', response.headers['Content-Disposition'])[0].strip(' ').strip(
        '"') if filename is None else filename
    total_size = int(response.headers.get('content-length', 0))

    file_path = os.path.join(path, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path) and os.stat(file_path).st_size == total_size:
        print('Download skipped.')
        return

    if parallel:
        if 'bytes' in response.headers.get('accept-ranges', 'None'):
            print('File supports parallel downloads')

            partial_dir = os.path.join(path, f'{filename}_partial')
            chunk_size = 1024 * 1024 * 2

            start = 0

            chunk_args = []

            while start < total_size:
                end = min(start + chunk_size - 1, total_size - 1)
                expected_chunk_size = (end - start) + 1
                chunk_args.append((f'chunk_{start}_{end}', {'Range': f'bytes={start}-{end}'}))
                start += expected_chunk_size

            num_workers = min(total_size // chunk_size, 512)
            flash(
                fn=lambda p: download(link, partial_dir, filename=p[0], parallel=False, headers=p[1]),
                args=chunk_args,
                max_workers=num_workers
            )

            fp1 = open(os.path.join(path, filename), 'wb')
            for chunk_name, _ in chunk_args:
                fp2 = open(os.path.join(partial_dir, chunk_name), 'rb')
                fp1.write(fp2.read())
                fp2.close()
            fp1.close()

            shutil.rmtree(partial_dir)

        else:
            download(link, path, filename, parallel=False)
    else:
        print('Saving at:', file_path)
        os.makedirs(path, exist_ok=True)

        block_size = 1024
        with open(file_path, 'wb') as file:
            for data in response.iter_content(block_size):
                file.write(data)

    return filename


if __name__ == '__main__':
    download('https://file-examples-com.github.io/uploads/2017/04/file_example_MP4_1920_18MG.mp4', 'downloads',
             'test.mp4')
