# Scripting file (for command)
# TODO
# soundmeter --threshold <RMS value> --duration <segments> --trigger script.sh
# soundmeter --test --duration <seconds>
# soundmeter --log <filename>
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


def monitor():
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

    # Process output
    output.seek(0)
    wf = wave.open(output, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    data = output.getvalue()
    segment = AudioSegment(data)
    sys.stdout.write('\r%10d  ' % segment.rms)
    sys.stdout.flush()


def main():
    while True:
        monitor()


def sigint_handler(signum, frame):
    sys.stdout.write('\r\n')
    os._exit(1)


signal.signal(signal.SIGINT, sigint_handler)


if __name__ == "__main__":
    main()
