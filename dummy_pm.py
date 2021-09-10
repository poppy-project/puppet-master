import os
import time
import random

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


def print_command(cmd):
    print(' '.join(cmd))


pm.call = print_command


class PuppetMaster(pm.PuppetMaster):
    def __init__(self, DaemonCls, configfile, pidfile):
        pm.PuppetMaster.__init__(self, DaemonCls, configfile, pidfile)

        self.update_config('robot.use-dummy', True)
        self.update_config('update.logfile', '/tmp/update.log')


    def log(self, msg, erase=False):
        if erase:
            os.remove(self.config.poppyLog.puppetMaster)

        with open(self.config.poppyLog.puppetMaster, 'a') as f:
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

    def self_update(self):
        self._updating = True

        if os.path.exists(self.config.poppyLog.update):
            os.remove(self.config.poppyLog.update)

        while True:
            with open(self.config.poppyLog.update, 'a') as f:
                f.write('Faking some install...\n')
            time.sleep(random.random() * 2)

            if random.random() < 0.1:
                break

        with open(self.config.poppyLog.update, 'a') as f:
            f.write('Your robot is now up-to-date!\n')

        self._updating = False

        return True
