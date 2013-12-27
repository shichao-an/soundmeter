import argparse
import pyaudio
import pydub
import wave
import signal
import sys
import threading
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from .settings import (PROG, FRAMES_PER_BUFFER, FORMAT, CHANNELS, RATE,
                       AUDIO_SEGMENT_LENGTH)

_soundmeter = None
lock = threading.Lock()


class Meter(object):

    num_frames = int(RATE / FRAMES_PER_BUFFER * AUDIO_SEGMENT_LENGTH)

    class StopException(Exception):
        pass

    def __init__(self, collect=False, seconds=None, action=None,
                 threshold=None, num=None, script=None, log=None,
                 daemonize=False):
        """
        :param collect: A boolean indicating whether collecting RMS values
        :param seconds: Number of seconds to run the meter (None for forever)
        :param action: The action type ('stop', 'stop-exec' or 'exec')
        :param threshold: A string representing threshold and bound type (e.g.
            '+252', '-144')
        :param num: An integer indicating how many consecutive times the
            threshold is reached before triggering the action
        :param script: File object representing the script to be executed
        :param log: File object representing the log file
        :param daemonize: A boolean indicating whether meter is run as daemon
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
        self.seconds = seconds
        self.action = action
        self.threshold = threshold
        self.num = num
        self.script = script
        self.log = log
        self.daemonize = daemonize
        self._graceful = False  # Graceful stop switch
        self._data = {}

    def record(self):
        """Record PyAudio stream into StringIO output"""

        frames = []
        num_frames = self.__class__.num_frames
        self.stream.start_stream()
        for i in xrange(num_frames):
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
        if self.seconds:
            signal.setitimer(signal.ITIMER_REAL, self.seconds)
        if self.collect:
            print 'Collecting RMS values...'
        if self.action:
            # Interpret threshold
            self.get_threshold()

        try:
            self.is_running = True
            while not self._graceful:
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
                self.monitor(rms)
            self.is_running = False
            self.stop()

        except self.__class__.StopException:
            self.is_running = False
            self.stop()

    def meter(self, rms):
        sys.stdout.write('\r%10d  ' % rms)
        sys.stdout.flush()

    def graceful(self):
        self._graceful = True

    def stop(self):
        """Stop the stream and terminate PyAudio"""
        sys.stdout.write('\n')
        if not self._graceful:
            self._graceful = True
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
        if self._data.get('triggered') == self.num:
            return True
        return False

    def execute(self):
        if self.action == 'stop':
            print 'Stopped'
            raise self.__class__.StopException('stop')
        elif self.action == 'stop-exec':
            print 'Stopped and exec'
            raise self.__class__.StopException('stop-exec')
        elif self.action == 'exec':
            print 'Exec'

    def monitor(self, rms):
        """This function is to be overridden"""
        pass

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
    parser.add_argument('-s', '--seconds', type=float,
                        help=seconds_help)
    parser.add_argument('-a', '--action', default='stop',
                        choices=['stop', 'stop-exec', 'exec'],
                        help="triggered action (defaults to 'stop')")
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

    # Extra validation of arguments
    args = parser.parse_args()
    if args.collect:
        if args.action or args.trigger:
            msg = ('-c/--collect should not be used with -a/--action '
                   'or -t/--trigger')
            raise parser.error(msg)
    if args.action:
        if not args.trigger:
            msg = 'must specify -t/--trigger when using -a/--action'
            raise parser.error(msg)
        if args.action in ['stop-exec', 'exec'] and not args.script:
            msg = ("must specify -e/--exec when using -a/--action "
                   "'stop-exec' or 'exec'")
            raise parser.error(msg)
        trigger_msg = ('the second argument NUM to -t/--trigger must be an '
                       'positive integer')
        if not args.trigger[1].isdigit():
            raise parser.error(trigger_msg)
        if args.trigger[1].isdigit() and int(args.trigger[1]) == 0:
            raise parser.error(trigger_msg)
    return args


def main():
    kwargs = dict(parse_args()._get_kwargs())
    # Convert `trigger' into `threshold' and `num'
    if kwargs['trigger'] is not None:
        kwargs['threshold'] = kwargs['trigger'][0]
        kwargs['num'] = kwargs['trigger'][0]
    del kwargs['trigger']
    m = Meter(**kwargs)
    m.start()


# Signal handlers
def sigint_handler(signum, frame):
    _soundmeter.graceful()


def sigalrm_handler(signum, frame):
    _soundmeter.graceful()


# Register signal handlers
signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGALRM, sigalrm_handler)


if __name__ == '__main__':
    main()
