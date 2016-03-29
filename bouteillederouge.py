import os

from flask import (Flask,
                   redirect, url_for,
                   render_template, flash,
                   send_from_directory)

from puppet_master import PuppetMaster
from poppyd import PoppyDaemon


app = Flask(__name__)
app.secret_key = os.urandom(24)

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

    host = pm.config.robot.name
    host = host if host == 'localhost' else '{}.local'.format(host)

    return redirect('http://{}:8888'.format(host))


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


@app.route('/example')
def example():
    return render_template('example.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
