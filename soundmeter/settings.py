# Default settings
import ConfigParser
import os
import pyaudio

PROG = 'soundmeter'
USER_DIR = os.path.join(os.path.expanduser('~'), '.' + PROG)
USER_LOGFILE = os.path.join(USER_DIR, 'log')
USER_CONFIG = os.path.join(USER_DIR, 'config')
USER_SCRIPT = os.path.join(USER_DIR, 'trigger.sh')

config = ConfigParser.ConfigParser()
config.read(USER_CONFIG)
items = {}
if config.has_section(PROG):
    items = dict(config.items(PROG))
    for name in items:
        try:
            if name in ['frames_per_buffer', 'format', 'channels', 'rate']:
                items[name] = int(items[name])
            if name in ['audio_segment_length']:
                items[name] = float(items[name])
        except:
            items[name] = None

FRAMES_PER_BUFFER = items.get('frames_per_buffer') or 2048
FORMAT = items.get('format') or pyaudio.paInt16
CHANNELS = items.get('channels') or 2
RATE = items.get('rate') or 44100
AUDIO_SEGMENT_LENGTH = items.get('audio_segment_length') or 0.5
