import os
import stat


def get_file_path(f):
    if f:
        name = getattr(f, 'name')
        if name:
            path = os.path.abspath(name)
            return path


def create_executable(path, content):
    with open(path, 'w') as f:
        f.write(content)
    s = os.stat(path)
    os.chmod(path, s.st_mode | stat.S_IEXEC)
