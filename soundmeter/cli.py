from __future__ import print_function
import argparse
import os
import sys
from .settings import PROG, USER_LOGFILE, USER_SCRIPT, USER_DIR
from .utils import get_file_path, create_executable


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
    parser.add_argument('-t', '--trigger', nargs='+',
                        metavar=('[+|-]THRESHOLD', 'NUM'),
                        help=trigger_help)
    parser.add_argument('-e', '--exec', dest='script',
                        metavar='SCRIPT', type=argparse.FileType('r'),
                        default=USER_SCRIPT,
                        help='shell script to execute upon trigger')
    parser.add_argument('-d', '--daemonize', action='store_true',
                        help='run the meter in the background')
    parser.add_argument('--log', nargs='?', metavar='LOGFILE',
                        type=argparse.FileType('a'),
                        const=USER_LOGFILE,
                        help='log the meter (default to ~/.soundmeter/log)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose mode')
    segment_help = 'audio segment length recorded in seconds (defaults to 0.5)'
    parser.add_argument('--segment', metavar='SECONDS', help=segment_help)

    # Extra validation of arguments
    args = parser.parse_args()
    if args.collect:
        if args.action or args.trigger:
            msg = ('-c/--collect should not be used with -a/--action '
                   'or -t/--trigger')
            raise parser.error(msg)
    if args.segment:
        try:
            segment = float(args.segment)
        except ValueError:
            msg = '--segment must be an integer or float'
            raise parser.error(msg)
        if segment < 0.05:
            msg = '--segment cannot be smaller than 0.05'
            raise parser.error(msg)
    if args.action:
        if not args.trigger:
            msg = 'must specify -t/--trigger when using -a/--action'
            raise parser.error(msg)
        if args.action == 'stop':
            args.script = None
        if len(args.trigger) == 1:
            args.trigger.append('1')
        elif len(args.trigger) > 2:
            trigger_msg = '-t/--trigger accepts at most two arguments'
            raise parser.error(trigger_msg)
        else:
            trigger_msg = ('the second argument NUM to -t/--trigger must be an'
                           ' positive integer')
            if not args.trigger[1].isdigit():
                raise parser.error(trigger_msg)
            if args.trigger[1].isdigit() and int(args.trigger[1]) == 0:
                raise parser.error(trigger_msg)

    elif args.trigger:
        msg = 'must specify -a/--action when using -t/--trigger'
        raise parser.error(msg)

    elif args.script:
        if '-e' in sys.argv or '--exec' in sys.argv:
            msg = ('must specify -a/--action and -t/--trigger when using '
                   '-e/--exec')
            raise parser.error(msg)
        else:
            args.script = None
    return args


def get_meter_kwargs():
    kwargs = dict(parse_args()._get_kwargs())
    # Convert `trigger' into `threshold' and `num'
    if kwargs['trigger'] is not None:
        kwargs['threshold'] = kwargs['trigger'][0]
        kwargs['num'] = int(kwargs['trigger'][1])
    del kwargs['trigger']
    kwargs['script'] = get_file_path(kwargs['script'])
    kwargs['log'] = get_file_path(kwargs['log'])
    kwargs['segment'] = float(kwargs['segment']) \
        if kwargs['segment'] is not None else None
    return kwargs


def setup_user_dir():
    if not os.path.exists(USER_DIR):
        os.makedirs(USER_DIR)
    if not os.path.exists(USER_SCRIPT):
        content = '!/bin/sh\n'
        create_executable(USER_SCRIPT, content)
