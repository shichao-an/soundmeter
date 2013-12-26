# Default settings
import os
import pyaudio


PROG = 'soundmeter'
FRAMES_PER_BUFFER = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
AUDIO_SEGMENT_LENGTH = 0.5
USER_CONFIG_DIR = os.path.expanduser('~')
