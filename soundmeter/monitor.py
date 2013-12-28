from .meter import Meter


class Monitor(Meter):

    def __init__(self, *args, **kwargs):
        super(Monitor, self).__init__(*args, **kwargs)

    def monitor(self, rms):
        """Extra monitor actions with RMS values

        Custom trigger conditions and actions can be written here as long as
        `action=None` is passed to the Monitor(). The Monitor instance will
        only execute monitor() as action is disabled.
        """
        pass

    # The following hooks can be used with as long as
    # `action=None` is passed to the Monitor()
    def prepopen(self):
        """Extra code before executing the script"""
        pass

    def postpopen(self):
        """Extra code after executing the script"""
        pass

    # The following hooks can be used in all cases
    def prestop(self):
        """Extra code before stop"""
        pass

    def poststop(self):
        """Extra code after stop"""
        pass
