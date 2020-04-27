import os
import time
import requests

from subprocess import call, check_call, Popen
from contextlib import closing
from threading import Thread

from poppyd import PoppyDaemon
from config import Config, attrsetter
from pypot.creatures import installed_poppy_creatures


class PuppetMaster(object):
    def __init__(self, DaemonCls, configfile, pidfile):
        self.configfile = os.path.abspath(configfile)
        self.pidfile = os.path.abspath(pidfile)
        self.logfile = self.config.info.logfile

        self.daemon = DaemonCls(self.configfile, self.pidfile)

        self.config_handlers = {
            'robot.name': self._change_hostname,
            'robot.motors': self._configure_motors,
            'wifi.start': self._auto_start_wifi,
            'wifi.ssid': self._add_wifi_ssid,
            'wifi.psk': self._add_wifi_psk,
            'hotspot.start': self._auto_start_hotspot,
            'hotspot.ssid': self._set_hotspot_ssid,
            'hotspot.psk': self._set_hotspot_psk
        }
        self._updating = False

    def start(self):
        self.daemon.start()

    @property
    def running(self):
        return 'running' in self.daemon.status()

    def stop(self):
        try:
            self.daemon.stop()
        except (OSError, SystemError):
            self.force_clean()

    def restart(self):
        if self.running:
            self.stop()

        self.start()

    def force_clean(self):
        self.daemon.force_clean()
        call(['pkill', '-f', 'poppy-services'])

    @property
    def config(self):
        return Config.from_file(self.configfile)

    def update_config(self, key, value):
        with closing(self.config) as c:
            attrsetter(key)(c, value)

        if key in self.config_handlers:
            self.config_handlers[key](value)

    def self_update(self):
        if self._updating:
            return

        self._updating = True

        if self.running:
            self.stop()
            flag=True
        else:
            flag=False

        if os.path.exists(self.config.update.logfile):
            os.remove(self.config.update.logfile)
        success = check_call(['poppy-update'])

        if flag: self.start()

        self._updating = False

        return success

    @property
    def is_updating(self):
        return self._updating

    def _change_hostname(self, name):
        call(['sudo', 'raspi-config', '--change-hostname', name])
        call(['sudo', 'hostnamectl', 'set-hostname', name])

    def restart_network(self):
        call(['sudo', 'systemctl', 'restart', 'networking.service'])
        call(['sudo', 'systemctl', 'restart', 'avahi-daemon.service'])
        if self.running:
            self.restart()

    def _get_robot_motor_list(self):
        try:
            RobotCls = installed_poppy_creatures[self.config.robot.creature]
            return sorted(RobotCls.default_config['motors'].keys())
        except KeyError:
            return ['']

    def _configure_motors(self, motor):
        if self.running:
            self.stop()
            flag=True
        else:
            flag=False

        creature = self.config.robot.creature.split('poppy-')[1]
        f = open(self.config.info.configMotorLog,"wb")
        check_call(['poppy-configure', creature, motor], stdout=f, stderr=f)

        if flag: self.start()

    def _auto_start_wifi(self, state):
        print('_auto_start_wifi No implemented! Comming soon')

    def _add_wifi_ssid(self, ssid):
        print('_add_wifi_ssid No implemented! Comming soon')

    def _add_wifi_psk(self, psk):
        print('_add_wifi_psk No implemented! Comming soon')

    def _auto_start_hotspot(self, state):
        print('_auto_start_hotspot No implemented! Comming soon')

    def _set_hotspot_ssid(self, ssid):
        print('_set_hotspot_ssid No implemented! Comming soon')

    def _set_hotspot_psk(self, psk):
        print('_set_hotspot_psk No implemented! Comming soon')

    def clone(self, number, http=8080, snap=6969, ws=9009):
        # port http, snap and ws, are hard coded in pypot for real robot
        nb_try = 0
        status = 'occuped'
        while status == 'occuped':
            nb_try+=1
            http+=1
            snap+=1
            ws+=1
            try:
                requests.get('http://{}:{}'.format(self.config.robot.name,http))
            except:
                status = 'free'
        for nb in range (number):
            f= open(self.config.info.virtualBotLog.replace('.log', '_{}.log'.format(nb+nb_try)), "wb")
            Popen(['poppy-services', '--poppy-simu', '--no-browser',
                   '--http', '--http-port', str(http),
                   '--snap', '--snap-port', str(snap),
                   '--ws', '--ws-port', str(ws),
                   self.config.robot.creature],
                   stdout=f, stderr=f)
            http+=1
            snap+=1
            ws+=1

    def reboot(self):
        try:
            for m in self.get_motors():
                self.send_value(m, 'compliant', True)
        except:
            pass

        def delayed_halt(sec=3):
            time.sleep(sec)
            call(['sudo', 'reboot'])
        Thread(target=delayed_halt).start()


    def shutdown(self):
        try:
            for m in self.get_motors():
                self.send_value(m, 'compliant', True)
        except:
            pass

        def delayed_halt(sec=3):
            time.sleep(sec)
            call(['sudo', 'halt'])
        Thread(target=delayed_halt).start()

    def get_motors(self):
        r = requests.get('http://localhost:8080/motor/list.json').json()
        return r['motors']

    def send_value(self, motor, register, value):
        url = 'http://localhost:8080/motor/{}/register/{}/value.json'
        r = requests.post(url.format(motor, register), json=value)
        return r


if __name__ == '__main__':
    import sys

    configfile = os.path.expanduser('~/.poppy_config.yaml')
    pidfile = '/tmp/puppet-master-pid.lock'

    puppet_master = PuppetMaster(DaemonCls=PoppyDaemon,
                                 configfile=configfile,
                                 pidfile=pidfile)

    if sys.argv[1] == 'start':
        puppet_master.start()
    elif sys.argv[1] == 'stop':
        puppet_master.stop()
