try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import os
import pyaudio


PROG = 'soundmeter'
USER_DIR = os.path.join(os.path.expanduser('~'), '.' + PROG)
USER_LOGFILE = os.path.join(USER_DIR, 'log')
USER_CONFIG = os.path.join(USER_DIR, 'config')
USER_SCRIPT = os.path.join(USER_DIR, 'trigger.sh')


class Config(object):

    FRAMES_PER_BUFFER = 2048
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    INPUT_DEVICE_INDEX = None
    RATE = 44100
    AUDIO_SEGMENT_LENGTH = 0.5
    RMS_AS_TRIGGER_ARG = False

    def __init__(self, section=None):
        config = configparser.ConfigParser()
        config.read(os.environ.get('SOUNDMETER_TEST_CONFIG') or USER_CONFIG)
        items = {}

        if section is None:
            if config.has_section(PROG):
                section = PROG
            else:
                return

        if config.has_section(section):
            items = dict(config.items(section))
            for name in items:
                try:
                    if name in ['frames_per_buffer', 'format', 'channels',
                                'rate', 'input_device_index']:
                        items[name] = int(items[name])
                    elif name in ['audio_segment_length']:
                        items[name] = float(items[name])
                    elif name in ['rms_as_trigger_arg']:
                        items[name] = bool(items[name])
                    else:
                        msg = \
                            'Unknown name "%s" in config section "%s"' % (
                                name, section)
                        raise Exception(msg)
                except ValueError:
                    msg = \
                        'Invalid value to "%s" in config section "%s"' % (
                                name, section)
                    raise Exception(msg)
        else:
            raise Exception('No section named "%s" in config' % section)

        for name, value in items.items():
            setattr(self, name.upper(), value)
