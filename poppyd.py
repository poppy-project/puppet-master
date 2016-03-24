#!/usr/bin/env python

import os
import yaml
import signal

from subprocess import Popen


class Daemon(object):
    def __init__(self, pidfile, logfile):
        self.pidfile = os.path.abspath(pidfile)
        self.logfile = os.path.abspath(logfile)

    def get_command(self):
        raise NotImplementedError

    def start(self):
        if 'running' in self.status():
            raise SystemError('pidfile {} already exist. '
                              'Daemon already running?'.format(self.pidfile))

        with open(self.logfile, 'w') as log:
            p = Popen(self.get_command(), stdout=log, stderr=log)

            with open(self.pidfile, 'w') as f:
                f.write('{}'.format(p.pid))

        return('Poppy daemon is now running!')

    def stop(self):
        if 'stopped' in self.status():
            raise SystemError('pidfile {} does not exist. '
                              'Daemon already stopped?'.format(self.pidfile))

        with open(self.pidfile) as f:
            pid = int(f.read())

        os.kill(pid, signal.SIGTERM)
        os.remove(self.pidfile)

        return('Poppy daemon is now stopped!')

    def restart(self):
        if 'running' in self.status():
            self.stop()
        self.start()

        return('Poppy daemon has been restarted!')

    def status(self):
        return 'Poppy daemon is {}.'.format('running'
                                            if os.path.exists(self.pidfile) else
                                            'stopped')

    def force_clean(self):
        os.remove(self.pidfile)


class PoppyDaemon(Daemon):
    def __init__(self, configfile, pidfile):
        self.configfile = configfile

        with open(self.configfile) as f:
            config = yaml.load(f)

        Daemon.__init__(self, pidfile, config['info']['logfile'])

    def get_command(self):
        with open(self.configfile) as f:
            config = yaml.load(f)

        cmd = [
            'poppy-services',
            config['robot']['creature'],
            '--snap',
            '--no-browser',
        ]

        if not config['robot']['camera']:
            cmd += ['--disable-camera']

        if 'use-dummy' in config['robot'] and config['robot']['use-dummy']:
            cmd += ['--poppy-simu']

        return cmd


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Poppy daemon',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('command', type=str,
                        choices=('start', 'stop', 'restart', 'status'),
                        help='possible commands')
    parser.add_argument('--configfile', type=str,
                        default=os.path.expanduser('~/.poppy_config.yaml'),
                        help='used config file')
    parser.add_argument('--pidfile', type=str,
                        default='/tmp/poppyd-pid.lock',
                        help='used pid file')
    args = parser.parse_args()

    poppyd = PoppyDaemon(args.configfile, args.pidfile)
    print(getattr(poppyd, args.command)())
