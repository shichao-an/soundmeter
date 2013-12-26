# Scripting file (for command)
# TODO
# soundmeter --threshold <RMS value> --duration <segments> --trigger script.sh
# soundmeter --collect/-c [seconds]
# soundmeter --log <filename>
import argparse
#import os
import pyaudio
import pydub
import wave
import signal
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from .settings import (PROG, FRAMES_PER_BUFFER, FORMAT, CHANNELS, RATE,
                       AUDIO_SEGMENT_LENGTH)

_soundmeter = None


class Meter(object):
    def __init__(self, collect=False, action=None, threshold=None,
                 num=None, script=None):
        """
        :param collect: A boolean indicating whether collecting RMS values
        :param action: The action type
        :param threshold: A string representing threshold and bound type (e.g.
            '+252', '-144')
        :param num: An integer indicating how many consecutive times the
            threshold is reached before triggering the action
        :param script: File object representing the script to be executed
        """

        global _soundmeter
        _soundmeter = self  # Register this meter globally
        self.output = StringIO()
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=FORMAT,
                                      channels=CHANNELS,
                                      rate=RATE,
                                      input=True,
                                      frames_per_buffer=FRAMES_PER_BUFFER)
        self.collect = collect
        self.action = action
        self.threshold = threshold
        self.num = num
        self.script = script
        self._data = {}

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
        if self.collect:
            print 'Collecting RMS values...'
        if self.action:
            self.get_threshold()

        while True:
            self.record()  # Record stream in `AUDIO_SEGMENT_LENGTH' long
            data = self.output.getvalue()
            segment = pydub.AudioSegment(data)
            rms = segment.rms
            if self.collect:
                self.collect_rms(rms)
            self.meter(rms)
            if self.action:
                if self.is_triggered(rms):
                    self.execute()

    def meter(self, rms):
        sys.stdout.write('\r%10d  ' % rms)
        sys.stdout.flush()

    def stop(self):
        """Stop the stream and terminate PyAudio"""
        self.stream.stop_stream()
        self.audio.terminate()
        if self.collect:
            if self._data:
                print 'Collected result:'
                print '    min: %10d' % self._data['min']
                print '    max: %10d' % self._data['max']
                print '    avg: %10d' % int(self._data['avg'])

    def get_threshold(self):
        """Get and validate raw RMS value from threshold"""

        if self.threshold.startswith('+'):
            if self.threshold[1:].isdigit():
                self._threshold = int(self.threshold[1:])
                self._upper = True
        elif self.threshold.startswith('-'):
            if self.threshold[1:].isdigit():
                self._threshold = int(self.threshold[1:])
                self._upper = False
        else:
            if self.threshold.isdigit():
                self._threshold = int(self.threshold)
                self._upper = True
        if not hasattr(self, '_threshold'):
            raise ValueError('Invalid threshold')

    def is_triggered(self, rms):
        if self._upper and rms > self._threshold \
                or not self._upper and rms < self._threshold:
            if 'triggered' in self._data:
                self._data['triggered'] += 1
            else:
                self._data['triggered'] = 1
        else:
            if 'triggered' in self._data:
                del self._data['triggered']
        if self._data.get('triggered', None) == self.num:
            return True
        return False

    def execute(self):
        if self.action == 'stop':
            self.stop()
            print 'Stopped'
            sys.exit(0)
        if self.action == 'stop-exec':
            self.stop()
            print 'Stopped and exec'
            sys.exit(0)
        if self.action == 'exec':
            print 'Exec'

    def collect_rms(self, rms):
        """Collect and calculate min, max and average RMS values"""
        if self._data:
            self._data['min'] = min(rms, self._data['min'])
            self._data['max'] = max(rms, self._data['max'])
            self._data['avg'] = float(rms + self._data['avg']) / 2
        else:
            self._data['min'] = rms
            self._data['max'] = rms
            self._data['avg'] = rms

    def __repr__(self):
        u = self.action if self.action else 'no-action'
        return '<%s: %s>' % (self.__class__.__name__, u)


def parse_args():
    parser = argparse.ArgumentParser(usage='%(prog)s [options]',
                                     prog=PROG)
    parser.add_argument('-c', '--collect', action='store_true',
                        help='collect RMS values to determine thresholds')
    seconds_help = 'time in seconds to run the meter (default forever)'
    parser.add_argument('-s', '--seconds',
                        help=seconds_help)
    parser.add_argument('-a', '--action',
                        choices=['stop', 'stop-exec', 'exec'])
    trigger_help = 'trigger condition (threshold RMS and number of times)'
    parser.add_argument('-t', '--trigger', nargs=2,
                        metavar=('[+|-]THRESHOLD', 'NUM'),
                        help=trigger_help)
    parser.add_argument('-e', '--exec', dest='script', metavar='SCRIPT',
                        help='shell script to execute upon trigger')
    parser.add_argument('-d', '--daemonize', action='store_true',
                        help='run the meter in the background')
    parser.add_argument('--log', nargs='?', metavar='LOGFILE',
                        help='log the meter (default to ~/.soundmeter/log)')
    args = parser.parse_args()
    if args.collect:
        if args.action:
            msg = '-c/--collect should not be used with -a/--action'
            raise parser.error(msg)
    if args.action:
        if not args.trigger:
            msg = 'must specify -t/--trigger when using -a/--action'
            raise parser.error(msg)
        if args.action in ['stop-exec', 'exec'] and not args.script:
            msg = 'must specify -e/--exec when using -a/--action'
            raise parser.error(msg)
    print args


def clear_stdout():
    sys.stdout.write('\r\n')


def main():
    #signal.setitimer(signal.ITIMER_REAL, 3.5)
    m = Meter(action='exec', threshold='+300', num=2)
    m.start()


def sigint_handler(signum, frame):
    clear_stdout()
    _soundmeter.stop()
    sys.exit(1)


def sigalrm_handler(signum, frame):
    clear_stdout()
    _soundmeter.stop()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGALRM, sigalrm_handler)


if __name__ == '__main__':
    main()
