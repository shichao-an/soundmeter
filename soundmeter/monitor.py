from .meter import Meter


class Monitor(Meter):
    def __init__(self, *args, **kwargs):
        super(Monitor, self).__init__(*args, **kwargs)

    def monitor(self, rms):
        """Extra monitor actions with RMS values"""
        pass

    def prepopen(self):
        """Extra code before executing the script"""
        pass

    def postpopen(self):
        """Extra code after executing the script"""
        pass

    def prestop(self):
        """Extra code before stop"""
        pass

    def poststop(self):
        """Extra code after stop"""
        pass
