import argparse
import daemon
import logging
import os
import pyaudio
import pydub
import wave
import signal
import subprocess
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from .settings import (PROG, FRAMES_PER_BUFFER, FORMAT, CHANNELS, RATE,
                       AUDIO_SEGMENT_LENGTH, USER_DIR, USER_LOGFILE)

_soundmeter = None


class Meter(object):

    num_frames = int(RATE / FRAMES_PER_BUFFER * AUDIO_SEGMENT_LENGTH)

    class StopException(Exception):
        pass

    def __init__(self, collect=False, seconds=None, action=None,
                 threshold=None, num=None, script=None, log=None,
                 daemonize=False, verbose=False):
        """
        :param collect: A boolean indicating whether collecting RMS values
        :param seconds: A float representing number of seconds to run the
            meter (None for forever)
        :param action: The action type ('stop', 'exec-stop' or 'exec')
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
        self.verbose = verbose
        self._graceful = False  # Graceful stop switch
        self._data = {}
        self.setup_logging()

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
        if self.log:
            #now = datetime.datetime.now()
            #line = '%s  %d\n' % (now.strftime(DATETIME_FORMAT), rms)
            #self.log.write(line)
            logging.info(rms)

    def graceful(self):
        """Graceful stop so that while loop in start() will stop after the
         current recording cycle"""
        self._graceful = True

    def stop(self):
        """Stop the stream and terminate PyAudio"""
        sys.stdout.write('\n')
        if not self._graceful:
            self._graceful = True
        if self.log:
            self.log.close()
        self.stream.stop_stream()
        self.audio.terminate()
        msg = 'Stopped'
        print msg
        if self.log:
            self.logging.info(msg)
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
            msg = 'Stop Action triggered'
            print msg
            if self.log:
                self.logging.info(msg)
            raise self.__class__.StopException('stop')
        elif self.action == 'exec-stop':
            msg = 'Exec-Stop Action triggered'
            self.popen()
            print msg
            if self.log:
                self.logging.info(msg)
            raise self.__class__.StopException('exec-stop')
            print 'execute script'
        elif self.action == 'exec':
            msg = 'Exec Action triggered'
            self.popen()
            print msg
            if self.log:
                self.logging.info(msg)

    def popen(self):
        if self.script:
            filename = os.path.abspath(self.script.name)
            try:
                subprocess.Popen([filename])
            except OSError, e:
                sys.stdout.write('\n')
                msg = 'Cannot execute the shell script: %s' % e
                print msg
                if self.log:
                    self.logging.info(msg)

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

    def setup_logging(self):
        if self.log:
            filename = os.path.abspath(self.log.name)
            self.logging = logging.basicConfig(
                filename=filename, format='%(asctime)s %(message)s')

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
    parser.add_argument('-a', '--action',
                        choices=['stop', 'exec-stop', 'exec'],
                        help="triggered action")
    trigger_help = 'trigger condition (threshold RMS and number of times)'
    parser.add_argument('-t', '--trigger', nargs=2,
                        metavar=('[+|-]THRESHOLD', 'NUM'),
                        help=trigger_help)
    parser.add_argument('-e', '--exec', dest='script', metavar='SCRIPT',
                        type=argparse.FileType('r'),
                        help='shell script to execute upon trigger')
    parser.add_argument('-d', '--daemonize', action='store_true',
                        help='run the meter in the background')
    parser.add_argument('--log', nargs='?', metavar='LOGFILE',
                        type=argparse.FileType('a'),
                        const=USER_LOGFILE,
                        help='log the meter (default to ~/.soundmeter/log)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose mode')
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
        if args.action in ['exec-stop', 'exec'] and not args.script:
            msg = ("must specify -e/--exec when using -a/--action "
                   "'exec-stop' or 'exec'")
            raise parser.error(msg)
        trigger_msg = ('the second argument NUM to -t/--trigger must be an '
                       'positive integer')
        if not args.trigger[1].isdigit():
            raise parser.error(trigger_msg)
        if args.trigger[1].isdigit() and int(args.trigger[1]) == 0:
            raise parser.error(trigger_msg)
    return args


def main():
    if not os.path.exists(USER_DIR):
        os.makedirs(USER_DIR)
    kwargs = dict(parse_args()._get_kwargs())
    print kwargs
    # Convert `trigger' into `threshold' and `num'
    if kwargs['trigger'] is not None:
        kwargs['threshold'] = kwargs['trigger'][0]
        kwargs['num'] = int(kwargs['trigger'][1])
    del kwargs['trigger']
    # Set default value to `action'
    if kwargs['daemonize']:
        with daemon.DaemonContext():
            m = Meter(**kwargs)
            m.start()
    else:
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
