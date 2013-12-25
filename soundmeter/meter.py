# Scripting file (for command)
# TODO
# soundmeter --threshold <RMS value> --duration <segments> --trigger script.sh
# soundmeter --test --duration <seconds>
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

# StringIO buffer for audio segments
output = StringIO()


def meter():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                    frames_per_buffer=FRAMES_PER_BUFFER)
    frames = []
    n = int(RATE / FRAMES_PER_BUFFER * AUDIO_SEGMENT_LENGTH)
    for i in xrange(n):
        data = stream.read(FRAMES_PER_BUFFER)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    p.terminate()

    output.seek(0)
    wf = wave.open(output, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    data = output.getvalue()
    segment = AudioSegment(data)
    sys.stdout.write('\r%10d  ' % segment.rms)


def parse_args():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-c', '--collect', type=float, nargs='?', const=10.0,
                       default=argparse.SUPPRESS,
                       help='Collect RMS values to determine thresholds.')
    parser.add_argument('--log', nargs=1, type=argparse.FileType('a'))


def main():
    while True:
        meter()


def sigint_handler(signum, frame):
    sys.stdout.write('\r\n')
    os._exit(1)


signal.signal(signal.SIGINT, sigint_handler)


if __name__ == '__main__':
    main()
