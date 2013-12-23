from soundmeter import meter
import os
import signal
import sys


def sigint_handler(signum, frame):
    sys.stdout.write('\r\n')
    os._exit(1)


signal.signal(signal.SIGINT, sigint_handler)


if __name__ == "__main__":
    meter.main()
