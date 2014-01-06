import os
import signal
import subprocess
from unittest import TestCase
from scripttest import TestFileEnvironment
from .command import setup_user_dir
from .meter import Meter
from .utils import create_executable


def create_run_script():
    d = os.path.dirname(__file__)
    project_path = os.path.abspath(os.path.join(d, os.pardir))
    run_script = os.path.join(project_path, 'run.py')
    content = '#!/usr/bin/env python\n'
    content += 'from soundmeter.meter import main\n\n\n'
    content += 'main()'
    if not os.path.exists(run_script):
        create_executable(run_script, content)


setup_user_dir()
create_run_script()


class TestMeter(TestCase):
    """Test Meter class programmatically"""
    def setUp(self):
        self.meter = Meter(seconds=2.0)

    def test_running(self):
        self.assertFalse(self.meter.is_running)
        self.meter.start()
        self.assertFalse(self.meter.is_running)


class TestBasicCommands(TestCase):
    """Test basic command-line invoke of the program"""
    def setUp(self):
        self.env = TestFileEnvironment('./test-output')

    def test_default(self):
        res = self.env.run('../run.py', '-s', '1')
        assert 'Timeout' in res.stdout
        self.assertEqual(res.returncode, 0)

    def test_collect(self):
        res = self.env.run('../run.py', '-s', '1', '-c')
        assert 'Collecting' in res.stdout
        self.assertEqual(res.returncode, 0)

    def test_log(self):
        res = self.env.run('../run.py', '-s', '1', '--log', 'log.txt')
        assert 'Timeout' in res.stdout
        assert 'log.txt' in res.files_created
        self.assertEqual(res.returncode, 0)

    def test_segment(self):
        res = self.env.run('../run.py', '-s', '1', '--segment', '0.2')
        assert 'Timeout' in res.stdout
        self.assertEqual(res.returncode, 0)

    def tearDown(self):
        pass


class TestCommands(TestCase):
    def test_sigint(self):
        popen = subprocess.Popen(['./run.py'])
        os.kill(popen.pid, signal.SIGINT)

    def test_arguments(self):
        popen = subprocess.Popen(['./run.py', '-t', '10000', '-a', 'stop'])
        os.kill(popen.pid, signal.SIGINT)

    def test_daemon(self):
        popen = subprocess.Popen(['./run.py', '-d'])
        os.kill(popen.pid, signal.SIGINT)
