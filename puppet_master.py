import os
import time
import requests

from subprocess import call, check_call, Popen
from contextlib import closing
from threading import Thread

from poppyd import PoppyDaemon
from config import Config, attrsetter
from pypot.creatures import installed_poppy_creatures
from pypot.server.snap import find_local_ip

class PuppetMaster(object):
    def __init__(self, DaemonCls, configfile, pidfile):
        self.configfile = os.path.abspath(configfile)
        self.pidfile = os.path.abspath(pidfile)
        self.logfile = self.config.poppyLog.puppetMaster

        self.daemon = DaemonCls(self.configfile, self.pidfile)

        self.config_handlers = {
            'robot.name': self._change_hostname,
            'robot.motors': self._configure_motors,
            'wifi.start': self._set_wifi,
            'wifi.ssid': self._change_wifi,
            'wifi.psk': self._change_wifi,
            'hotspot.start': self._set_hotspot,
            'hotspot.ssid': self._set_hotspot,
            'hotspot.psk': self._set_hotspot
        }
        self._updating = False
        self.nb_clone = 0

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

        if os.path.exists(self.config.poppyLog.update):
            os.remove(self.config.poppyLog.update)
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
        call(['sudo', 'systemctl', 'restart', 'networking.service']) #needed for change hostname
        call(['sudo', 'systemctl', 'restart', 'avahi-daemon.service']) #needed for change hostname
        call(['sudo', 'systemctl', 'restart', self.config.info.serviceNetwork ]) #needed for change wifi or hotspot
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
        with open(self.config.poppyLog.configMotor,"wb") as f:
            check_call(['poppy-configure', creature, motor], stdout=f, stderr=f)
            f.close()

        if flag: self.start()

    def _set_wifi(self, state):
        tmp_file='/tmp/tmp.txt'
        with open(tmp_file, 'w') as f:
            #tricks to pass through of the permission denied in conf file
            call(['sudo', 'cat', self.config.wifi.confFile], stdout=f)
            f.close()
        with open(tmp_file, 'r') as f:
            data = f.readlines()
            f.close()
        if state:
            add= [
                '#default_Network\n',
                'network={\n',
                '\tssid=\"{}\"\n'.format(self.config.wifi.ssid),
                '\tpsk=\"{}\"\n'.format(self.config.wifi.psk),
                '}\n'
            ]
            data+=add
        else:
            for i,line in enumerate(data):
                if '#default_Network' in line:
                    for _ in range(5):
                        del data[i]
        with open(tmp_file, 'w') as f:
            f.writelines(data)
            f.close()
        call(['sudo', 'cp', tmp_file, self.config.wifi.confFile])
        call(['sudo', 'rm', tmp_file])

    def _change_wifi(self, _):
        if self.config.wifi.start:
            self._set_wifi(False)#remove old config
            self._set_wifi(True)#set new config

    def _set_hotspot(self, _):
        if self.config.hotspot.start:
            tmp_file='/tmp/tmp.txt'
            with open(tmp_file, 'w') as f:
                f.write('ssid={}\npassphrase={}\n'.format(self.config.hotspot.ssid, self.config.hotspot.psk))
                f.close()
            call(['sudo', 'cp', tmp_file, self.config.hotspot.confFile])
            call(['sudo', 'rm', tmp_file])
        else:
            try:
                call(['sudo', 'rm', self.config.hotspot.confFile])
            except OSError:
                pass

    def clone(self, number=1):
        http, snap, ws = int(self.config.poppyPort.http), int(self.config.poppyPort.snap), int(self.config.poppyPort.ws)
        nb_try = 0
        status = 'occuped'
        while status == 'occuped':
            nb_try+=1
            http+=1
            snap+=1
            ws+=1
            try:
                requests.get('http://localhost:{}'.format(http))
            except:
                status = 'free'
        for nb in range (number):
            with open(self.config.poppyLog.virtualBot.replace('.log', '_{}.log'.format(nb+nb_try)), 'wb') as f:
                try:
                    Popen(['poppy-services', '--poppy-simu', '--no-browser',
                           '--http', '--http-port', str(http),
                           '--snap', '--snap-port', str(snap),
                           '--ws', '--ws-port', str(ws),
                           self.config.robot.creature],
                           stdout=f, stderr=f)
                    f.close()
                except:
                    f.write('>> ERROR <<')
                    f.close()
                    return 'ECHEC'
            self.nb_clone+=1
            http+=1
            snap+=1
            ws+=1

    def restart_services(self):
        services=[s.split(': ') for s in str(self.config.services).replace('\'','').split(',')]
        cmd=['sudo','systemctl','restart']
        for name, service in services:
            service=service.replace('{','').replace('}','')
            cmd.append(service)
        Popen(cmd)

    def reboot(self):
        try:
            if not self.running: self.start()
            for m in self.get_motors():
                self.send_value(m, 'compliant', True)
                self.send_value(m, 'led', 'off')
            self.stop()
        except:
            pass

        def delayed_halt(sec=3):
            time.sleep(sec)
            call(['sudo', 'reboot'])
        Thread(target=delayed_halt).start()


    def shutdown(self):
        try:
            if not self.running: self.start()
            for m in self.get_motors():
                self.send_value(m, 'compliant', True)
                self.send_value(m, 'led', 'off')
            self.stop()
        except:
            pass

        def delayed_halt(sec=3):
            time.sleep(sec)
            call(['sudo', 'halt'])
        Thread(target=delayed_halt).start()

    def get_motors(self, alias='motors'):
        r = requests.get('http://localhost:{}/motor/{}/list.json'.format(self.config.poppyPort.http, alias)).json()
        return r[alias]

    def send_value(self, motor, register, value):
        url = 'http://localhost:{}/motor/{}/register/{}/value.json'
        r = requests.post(url.format(self.config.poppyPort.http, motor, register), json=value)
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
