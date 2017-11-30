from __future__ import print_function
import daemon
import logging
import pyaudio
import pydub
import wave
import signal
import six
import subprocess
import sys
import time
import warnings
if six.PY2:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
else:
    from io import BytesIO as StringIO
from .settings import (FRAMES_PER_BUFFER, FORMAT, CHANNELS, RATE,
                       INPUT_DEVICE_INDEX, AUDIO_SEGMENT_LENGTH,
                       RMS_AS_TRIGGER_ARG)
from .cli import get_meter_kwargs, setup_user_dir
from .utils import noalsaerr, coroutine


__all__ = ['Meter']
warnings.filterwarnings("ignore", category=DeprecationWarning)
_soundmeter = None


class Meter(object):

    class StopException(Exception):
        pass

    def __init__(self, collect=False, seconds=None, action=None,
                 threshold=None, num=None, script=None, log=None,
                 verbose=False, segment=None, *args, **kwargs):
        """
        :param bool collect: A boolean indicating whether collecting RMS values
        :param float seconds: A float representing number of seconds to run the
            meter (None for forever)
        :param str action: The action type ('stop', 'exec-stop' or 'exec')
        :param str threshold: A string representing threshold and bound type
            (e.g. '+252', '-144')
        :param int num: An integer indicating how many consecutive times the
            threshold is reached before triggering the action
        :param script: File object representing the script to be executed
        :param log: File object representing the log file
        :param bool verbose: A boolean for verbose mode
        :param float segment: A float representing `AUDIO_SEGMENT_LENGTH`
        """

        global _soundmeter
        _soundmeter = self  # Register this meter globally
        self.output = StringIO()
        with noalsaerr():
            self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=FORMAT,
                                      channels=CHANNELS,
                                      input_device_index=INPUT_DEVICE_INDEX,
                                      input=True,
                                      rate=RATE,
                                      frames_per_buffer=FRAMES_PER_BUFFER)
        self.collect = collect
        self.seconds = seconds
        self.action = action
        self.threshold = threshold
        self.num = num
        self.script = script
        self.log = log
        self.verbose = verbose
        self.segment = segment
        self.is_running = False
        self._graceful = False  # Graceful stop switch
        self._timeout = False
        self._timer = None
        self._data = {}
        self._setup_logging()

    @coroutine
    def record(self):
        """
        Record PyAudio stream into StringIO output

        This coroutine keeps stream open; the stream is closed in stop()
        """

        while True:
            frames = []
            self.stream.start_stream()
            for i in range(self.num_frames):
                data = self.stream.read(FRAMES_PER_BUFFER)
                frames.append(data)
            self.output.seek(0)
            w = wave.open(self.output, 'wb')
            w.setnchannels(CHANNELS)
            w.setsampwidth(self.audio.get_sample_size(FORMAT))
            w.setframerate(RATE)
            w.writeframes(b''.join(frames))
            w.close()
            yield

    def start(self):
        segment = self.segment or AUDIO_SEGMENT_LENGTH
        self.num_frames = int(RATE / FRAMES_PER_BUFFER * segment)
        if self.seconds:
            signal.setitimer(signal.ITIMER_REAL, self.seconds)
        if self.verbose:
            self._timer = time.time()
        if self.collect:
            print('Collecting RMS values...')
        if self.action:
            # Interpret threshold
            self.get_threshold()

        try:
            self.is_running = True
            record = self.record()
            while not self._graceful:
                record.send(True)  # Record stream `AUDIO_SEGMENT_LENGTH' long
                data = self.output.getvalue()
                segment = pydub.AudioSegment(data)
                rms = segment.rms
                if self.collect:
                    self.collect_rms(rms)
                self.meter(rms)
                if self.action:
                    if self.is_triggered(rms):
                        self.execute(rms)
                self.monitor(rms)
            self.is_running = False
            self.stop()

        except self.__class__.StopException:
            self.is_running = False
            self.stop()

    def meter(self, rms):
        if not self._graceful:
            sys.stdout.write('\r%10d  ' % rms)
            sys.stdout.flush()
            if self.log:
                self.logging.info(rms)

    def graceful(self):
        """Graceful stop so that the while loop in start() will stop after the
         current recording cycle"""
        self._graceful = True

    def timeout(self):
        msg = 'Timeout'
        print(msg)
        if self.log:
            self.logging.info(msg)
        self.graceful()

    def stop(self):
        """Stop the stream and terminate PyAudio"""
        self.prestop()
        if not self._graceful:
            self._graceful = True
        self.stream.stop_stream()
        self.audio.terminate()
        msg = 'Stopped'
        self.verbose_info(msg, log=False)
        # Log 'Stopped' anyway
        if self.log:
            self.logging.info(msg)
        if self.collect:
            if self._data:
                print('Collected result:')
                print('    min: %10d' % self._data['min'])
                print('    max: %10d' % self._data['max'])
                print('    avg: %10d' % int(self._data['avg']))
        self.poststop()

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
        t = self._data.get('triggered')
        if isinstance(t, int) and t >= self.num:
            return True
        return False

    def execute(self, rms):
        if self.action == 'stop':
            msg = 'Stop Action triggered'
            print(msg)
            if self.log:
                self.logging.info(msg)
            raise self.__class__.StopException('stop')

        elif self.action == 'exec-stop':
            msg = 'Exec-Stop Action triggered'
            print(msg)
            if self.log:
                self.logging.info(msg)
            v = 'Executing %s' % self.script
            self.verbose_info(v)
            self.popen(rms)
            raise self.__class__.StopException('exec-stop')

        elif self.action == 'exec':
            msg = 'Exec Action triggered'
            print(msg)
            if self.log:
                self.logging.info(msg)
            v = 'Executing %s' % self.script
            self.verbose_info(v)
            self.popen(rms)

    def popen(self, rms):
        self.prepopen()
        if self.script:
            try:
                cmd = [self.script]
                """If configured as True, rms value is passed
                as an argument for the script"""
                if (RMS_AS_TRIGGER_ARG):
                    cmd.append(str(rms))
                subprocess.Popen(cmd)
            except OSError as e:
                msg = 'Cannot execute the shell script: %s' % e
                print(msg)
                if self.log:
                    self.logging.info(msg)
        self.postpopen()

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

    def verbose_info(self, msg, log=True):
        if self.verbose:
            print(msg)
            if self.log and log:
                self.logging.info(msg)

    def _setup_logging(self):
        if self.log:
            self.logging = logging.basicConfig(
                filename=self.log, format='%(asctime)s %(message)s',
                level=logging.INFO)
            self.logging = logging.getLogger(__name__)

    def monitor(self, rms):
        """This function is to be overridden"""
        pass

    def prepopen(self):
        """Pre-popen hook"""
        pass

    def postpopen(self):
        """Post-popen hook"""
        pass

    def prestop(self):
        """Pre-stop hook"""
        pass

    def poststop(self):
        """Post-stop hook"""
        pass

    def __repr__(self):
        u = self.action if self.action else 'no-action'
        return '<%s: %s>' % (self.__class__.__name__, u)


def main():
    setup_user_dir()
    kwargs = get_meter_kwargs()
    if kwargs.pop('daemonize'):
        daemon_context = daemon.DaemonContext()
        # python-daemon>=2.1 has initgroups=True by default but it requires
        # root privileges.
        # setting daemon_context.initgroups to False instead of passing
        # arguments to daemon.DaemonContext will not break older versions
        daemon_context.initgroups = False
        with daemon_context:
            m = Meter(**kwargs)
            m.start()
    else:
        m = Meter(**kwargs)
        m.start()


# Signal handlers
def sigint_handler(signum, frame):
    sys.stdout.write('\n')
    _soundmeter.graceful()


def sigalrm_handler(signum, frame):
    _soundmeter.timeout()


# Register signal handlers
signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGALRM, sigalrm_handler)
