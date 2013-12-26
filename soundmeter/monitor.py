from .meter import Meter


class Monitor(Meter):
    def __init__(self, *args, **kwargs):
        super(Monitor, self).__init__(*args, **kwargs)

    def monitor(self, rms):
        """Extra monitor actions with RMS values"""
        pass
