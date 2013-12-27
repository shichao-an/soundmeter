from unittest import TestCase
from scripttest import TestFileEnvironment
from .meter import Meter


class TestMeter(TestCase):
    def setUp(self):
        self.meter = Meter(seconds=2.0)

    def test_running(self):
        self.assertFalse(self.meter.is_running)
        self.meter.start()
        self.assertFalse(self.meter.is_running)


class TestCommand(TestCase):
    def setUp(self):
        self.env = TestFileEnvironment('./test-output')

    def test_default(self):
        res = self.env.run('../run.py', '-s', '2')
        self.assertIn('Timeout', res.stdout)
