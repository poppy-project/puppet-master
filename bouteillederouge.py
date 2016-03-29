import os
import requests
import argparse

from flask import (Flask,
                   redirect, url_for,
                   render_template, flash,
                   send_from_directory, Response)

from poppyd import PoppyDaemon


parser = argparse.ArgumentParser(description='Serve the webinterface '
                                             'for controlling Poppy robots')
parser.add_argument('--debug', action='store_true',
                    help='use the debug mode')
parser.add_argument('--test', action='store_true',
                    help='does not modify anything on your machine '
                         '(except from a config file in /tmp)')
args = parser.parse_args()


if args.test:
    from dummy_pm import PuppetMaster
else:
    from puppet_master import PuppetMaster


app = Flask(__name__)
app.secret_key = os.urandom(24)

if args.debug:
    app.debug = True

if args.test:
    from subprocess import call
    configfile = '/tmp/poppy_config.yaml'
    call(['python', 'bootstrap.py',
          '--config-path', configfile,
          'localhost', 'poppy-ergo-jr'])
else:
    configfile = os.path.expanduser('~/.poppy_config.yaml')

pidfile = '/tmp/puppet-master-pid.lock'

pm = PuppetMaster(DaemonCls=PoppyDaemon,
                  configfile=configfile,
                  pidfile=pidfile)

if os.path.exists(pidfile):
    pm.force_clean()
pm.start()


@app.context_processor
def inject_robot_config():
    return dict(robot=pm.config.robot, info=pm.config.info)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/monitor')
def monitor():
    if not pm.running:
        pm.start()

    return render_template('monitor.html')


@app.route('/snap')
def snap():
    if not pm.running:
        pm.start()

    return redirect(url_for('base_static', filename='snap.html'))


@app.route('/snap/<path:filename>')
def base_static(filename):
    return send_from_directory(app.root_path + '/snap/', filename)


@app.route('/jupyter')
def jupyter():
    if pm.running:
        pm.stop()

    return redirect('http://{}:8888'.format(get_host()))


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/change_hostname/<name>')
def change_hostname(name):
    pm.update_config('robot.name', name)
    flash('Robot name was changed to {}'.format(name))
    return 'OK'


@app.route('/logs')
def logs():
    try:
        with open(pm.config.info.logfile) as f:
            content = f.read()
    except IOError:
        content = 'No log found...'
    return render_template('logs.html', logs_content=content)


@app.route('/reset')
def reset():
    if pm.running:
        pm.stop()

    pm.start()
    flash('Your robot has been restarted.')
    return redirect(url_for('index'))


@app.route('/udpate')
def update():
    pm.self_update()
    flash('Your robot is currently updating. Please do not turn it off before it\' done!')


@app.route('/updating')
def is_updating():
    return pm.is_updating


@app.route('/done-updating')
def done_updating():
    flash('Your robot is now up-to-date!')
    return redirect(url_for('index'))


@app.route('/camera/<checked>')
def switch_camera(checked):
    pm.update_config('robot.camera', True if checked == 'on' else False)
    return 'OK'


@app.route('/ready-to-roll')
def ready_to_roll():
    with open(pm.config.info.logfile) as f:
        content = f.read()

    if 'SnapRobotServer is now running on' not in content:
        return 'KO'

    try:
        r = requests.get('http://{}:6969/motors/get/positions'.format(get_host()))
        if r.status_code == 200:
            return 'OK'
    except:
        pass

    return 'KO'


@app.route('/example')
def example():
    return render_template('example.html')


@app.route('/api/raw_logs')
def raw_logs():
    try:
        with open(pm.config.info.logfile) as f:
            content = f.read()
    except IOError:
        content = 'No log found...'
    return Response(content, mimetype='text/plain')


def get_host():
    host = pm.config.robot.name
    host = host if host == 'localhost' else '{}.local'.format(host)
    return host


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
