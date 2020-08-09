import os
import stat


def chmod(path, mode=stat.S_IRWXU):
    path = os.path.realpath(path)
    print(f'Absolute path: {path}')
    if os.path.exists(path):
        if os.path.isfile(path):
            os.chmod(path, mode)
        else:
            for root, _, files in os.walk(path):
                for file in files:
                    file_pt = os.path.join(root, file)
                    print(f'Changing permission for file: {file_pt} to {mode}')
                    os.chmod(file_pt, mode)
