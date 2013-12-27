# Default settings
import os
import pyaudio


PROG = 'soundmeter'
FRAMES_PER_BUFFER = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
AUDIO_SEGMENT_LENGTH = 0.5
USER_DIR = os.path.join(os.path.expanduser('~'), '.' + PROG)
USER_LOGFILE = os.path.join(USER_DIR, 'log')
USER_CONFIG = os.path.join(USER_DIR, 'config')
USER_SCRIPT = os.path.join(USER_DIR, 'trigger.sh')
