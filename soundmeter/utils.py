from ctypes import *  # NOQA
from contextlib import contextmanager
import os
import six
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


# Work-around on error messages by alsa-lib
# http://stackoverflow.com/questions/7088672/
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int,
                               c_char_p, c_int, c_char_p)


def py_error_handler(filename, line, function, err, fmt):
    pass


c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)


@contextmanager
def noalsaerr():
    try:
        asound = cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(c_error_handler)
        yield
        asound.snd_lib_error_set_handler(None)
    except:
        yield


def coroutine(func):
    def start(*args, **kwargs):
        g = func(*args, **kwargs)
        if six.PY2:
            g.next()
        else:
            g.__next__()
        return g
    return start
