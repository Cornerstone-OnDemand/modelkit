import glob
import os


def get_size(dir_path):
    if os.path.isfile(dir_path):
        return os.stat(dir_path).st_size
    return sum(
        os.stat(f).st_size
        for f in glob.iglob(os.path.join(dir_path, "**/*"), recursive=True)
        if os.path.isfile(f)
    )
