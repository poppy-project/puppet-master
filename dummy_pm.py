from __future__ import print_function

import os

from collections import defaultdict

import puppet_master as pm


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


class PuppetMaster(pm.PuppetMaster):
    def __init__(self, DaemonCls, configfile, pidfile):
        pm.PuppetMaster.__init__(self, DaemonCls, configfile, pidfile)

        self.config_handlers = defaultdict(lambda: lambda _: _)
        self.update_config('robot.use-dummy', True)

    def log(self, msg, erase=False):
        if erase:
            os.remove(self.config.info.logfile)

        with open(self.config.info.logfile, 'a') as f:
            f.write('{}\n'.format(msg))

    def start(self):
        self.log(success, erase=True)
        pm.PuppetMaster.start(self)

    def stop(self):
        self.log('Stop daemon')
        pm.PuppetMaster.stop(self)

    def update_config(self, key, value):
        self.log('Update config {}={}'.format(key, value))
        pm.PuppetMaster.update_config(self, key, value)
