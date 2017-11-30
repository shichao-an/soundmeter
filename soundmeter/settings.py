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

config = configparser.ConfigParser()
config.read(os.environ.get('SOUNDMETER_TEST_CONFIG') or USER_CONFIG)
items = {}

if config.has_section(PROG):
    items = dict(config.items(PROG))
    for name in items:
        try:
            if name in ['frames_per_buffer', 'format', 'channels', 'rate',
                        'input_device_index']:
                items[name] = int(items[name])
            elif name in ['audio_segment_length']:
                items[name] = float(items[name])
            elif name in ['rms_as_trigger_arg']:
                items[name] = bool(items[name])
            else:
                raise Exception('Unknown name "%s" in config' % name)
        except ValueError:
            raise Exception('Invalid value to "%s" in config' % name)

FRAMES_PER_BUFFER = items.get('frames_per_buffer') or 2048
FORMAT = items.get('format') or pyaudio.paInt16
CHANNELS = items.get('channels') or 2
INPUT_DEVICE_INDEX = items.get('input_device_index')
RATE = items.get('rate') or 44100
AUDIO_SEGMENT_LENGTH = items.get('audio_segment_length') or 0.5
RMS_AS_TRIGGER_ARG = items.get('rms_as_trigger_arg') or False
