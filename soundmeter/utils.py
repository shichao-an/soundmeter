import os


def get_file_path(f):
    name = getattr(f, 'name')
    if name:
        path = os.path.abspath(name)
        return path
