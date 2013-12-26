# Scripting file (for command)
# TODO
# soundmeter --threshold <RMS value> --duration <segments> --trigger script.sh
# soundmeter --collect/-c [seconds]
# soundmeter --log <filename>
import argparse
import os
import pyaudio
from pydub import AudioSegment
import wave
import signal
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from .settings import (FRAMES_PER_BUFFER, FORMAT, CHANNELS, RATE,
                       AUDIO_SEGMENT_LENGTH)

_soundmeter = None


class Meter(object):

    def __init__(self):
        self.output = StringIO()
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=FORMAT,
                                      channels=CHANNELS,
                                      rate=RATE,
                                      input=True,
                                      frames_per_buffer=FRAMES_PER_BUFFER)
        global _soundmeter
        _soundmeter = self  # Register this meter globally

    def record(self):
        """Record PyAudio stream into StringIO output"""

        frames = []
        n = int(RATE / FRAMES_PER_BUFFER * AUDIO_SEGMENT_LENGTH)
        self.stream.start_stream()
        for i in xrange(n):
            data = self.stream.read(FRAMES_PER_BUFFER)
            frames.append(data)
        self.stream.stop_stream()
        self.output.seek(0)
        w = wave.open(self.output, 'wb')
        w.setnchannels(CHANNELS)
        w.setsampwidth(self.audio.get_sample_size(FORMAT))
        w.setframerate(RATE)
        w.writeframes(b''.join(frames))

    def start(self):
        while True:
            self.record()  # Record stream in `AUDIO_SEGMENT_LENGTH' long
            data = self.output.getvalue()
            segment = AudioSegment(data)
            sys.stdout.write('\r%10d  ' % segment.rms)
            sys.stdout.flush()

    def stop(self):
        """Stop the stream and terminate PyAudio"""
        self.stream.stop_stream()
        self.audio.terminate()


def parse_args():
    parser = argparse.ArgumentParser(usage='%(prog)s [options]',
                                     prog='soundmeter')
    parser.add_argument('-c', '--collect', action='store_true',
                        help='collect RMS values to determine thresholds')
    seconds_help = 'time in seconds to run the meter (default forever)'
    parser.add_argument('-s', '--seconds',
                        help=seconds_help)
    trigger_help = 'trigger condition (threshold RMS and number of times)'
    parser.add_argument('-t', '--trigger', nargs=2,
                        metavar=('[+|-]THRESHOLD', 'NUM'),
                        help=trigger_help)
    parser.add_argument('-e', '--exec', metavar='SCRIPT',
                        help='shell script to execute upon trigger')
    parser.add_argument('-d', '--daemonize', action='store_true',
                        help='run the meter in the background')
    args = parser.parse_args()
    print args


def clear_stdout():
    sys.stdout.write('\r\n')


def main():
    signal.setitimer(signal.ITIMER_REAL, 3.5)
    #while True:
        #meter()
    m = Meter()
    m.start()


def sigint_handler(signum, frame):
    clear_stdout()
    _soundmeter.stop()
    os._exit(1)


def sigalrm_handler(signum, frame):
    clear_stdout()
    _soundmeter.stop()
    os._exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGALRM, sigalrm_handler)


if __name__ == '__main__':
    main()
