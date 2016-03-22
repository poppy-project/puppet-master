from __future__ import print_function

import os

from contextlib import closing

from config import Config, attrsetter


success = """
Attempt 1 to start the robot...
SnapRobotServer is now running on: http://0.0.0.0:6969

You can open Snap! interface with loaded blocks at "http://snap.berkeley.edu/snapsource/snap.html#open:http://192.168.0.24:6969/snap-blocks.xml"

Robot created and running!
"""

fail = """
Attempt 1 to start the robot...
Can not open camera device -1!
Attempt 2 to start the robot...
Can not open camera device -1!
Attempt 3 to start the robot...
Can not open camera device -1!
Attempt 4 to start the robot...
Can not open camera device -1!
Attempt 5 to start the robot...
Can not open camera device -1!
Could not start up the robot...
"""


def call(cmd):
    print('Calling "{}"'.format(' '.join(cmd)))


class PuppetMaster(object):
    def __init__(self, DaemonCls, configfile, pidfile):
        self.configfile = os.path.abspath(configfile)
        self.pidfile = os.path.abspath(pidfile)
        self.logfile = self.config.info.logfile

        self.daemon = None
        self._running = 'stopped'

        self.config_handlers = {
            'robot.camera': lambda _: self.restart(),
            'robot.name': self._change_hostname,
        }

    def log(self, msg):
        print(msg)
        with open(self.config.info.logfile, 'a') as f:
            f.write('{}\n'.format(msg))

    def start(self):
        self.log('Start daemon')
        self._running = 'running'

    @property
    def running(self):
        return 'running' in self._running

    def stop(self):
        try:
            self.log('Stop daemon')
            self._running = 'stopped'
        except OSError:
            self.force_clean()

    def restart(self):
        self.log('Restart daemon')
        if self.running:
            self.stop()

        self.start()

    def force_clean(self):
        self.log('Force clean')
        # self.daemon.force_clean()

    @property
    def config(self):
        return Config.from_file(self.configfile)

    def update_config(self, key, value):
        self.log('Update config {}={}'.format(key, value))
        with closing(self.config) as c:
            attrsetter(key)(c, value)

        if key in self.config_handlers:
            self.config_handlers[key](value)

    def update(self):
        raise NotImplementedError

    @property
    def is_updating(self):
        raise NotImplementedError

    def _change_hostname(self, name):
        self.log('change hostname to {}'.format(name))
        call(['sudo', 'raspi-config', '--change-hostname', name])
        call(['sudo', 'service', 'avahi-daemon', 'restart'])
        self.restart()


if __name__ == '__main__':
    import sys

    # configfile = os.path.expanduser('~/.poppy_config.yaml')
    configfile = 'bob.yaml'
    pidfile = '/tmp/puppet-master-pid.lock'
    logfile = '/tmp/puppet-master.log'

    puppet_master = PuppetMaster(DaemonCls=None,
                                 configfile=configfile,
                                 pidfile=pidfile,
                                 logfile=logfile)

    if sys.argv[1] == 'start':
        puppet_master.start()
    elif sys.argv[1] == 'stop':
        puppet_master.stop()
