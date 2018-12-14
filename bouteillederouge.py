import os
import sys
import requests
import argparse
import subprocess

from threading import Thread

from flask import (Flask, request,
                   redirect, url_for,
                   render_template, flash,
                   send_from_directory, Response,
                   copy_current_request_context)

from pypot.creatures import installed_poppy_creatures

from poppyd import PoppyDaemon

if sys.version_info < (3, 3):
    from urlparse import urlparse
else:
    from urllib.parse import urlparse


parser = argparse.ArgumentParser(description='Serve the webinterface '
                                             'for controlling Poppy robots')
parser.add_argument('--debug', action='store_true',
                    help='use the debug mode')
parser.add_argument('--test', action='store_true',
                    help='does not modify anything on your machine '
                         '(except from a config file in /tmp)')
parser.add_argument('--creature', choices=installed_poppy_creatures.keys(),
                    help='Which creature to use (by default will use the one set in the yaml config).')
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
    if not args.creature:
        print('You must choose a creature in test mode!\n')
        parser.print_help()
        sys.exit(1)

    configfile = '/tmp/poppy_config.yaml'
    subprocess.call(['python', 'bootstrap.py',
                     '--config-path', configfile,
                     'localhost', args.creature])
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


@app.after_request
def cache_buster(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/monitor')
def monitor():
    if not pm.running:
        pm.start()

    return render_template(
        'base-iframe.html',
        iframe_src=url_for(
            'base_static_monitor',
            filename='{}.html'.format(pm.config.robot.creature)
        )
    )


@app.route('/monitor/<path:filename>')
def base_static_monitor(filename):
    return send_from_directory(app.root_path + '/monitor/', filename)


@app.route('/snap')
def snap():
    if not pm.running:
        pm.start()

    return render_template(
        'base-iframe.html',
        iframe_src=url_for('base_static_snap', filename='snap.html')
    )


@app.route('/snap/<path:filename>')
def base_static_snap(filename):
    return send_from_directory(app.root_path + '/snap/', filename)


@app.route('/jupyter')
def jupyter():
    if pm.running:
        pm.stop()

    return render_template(
        'base-iframe.html',
        iframe_src='http://{}:8888'.format(urlparse(request.url_root).hostname)
    )


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/change_hostname', methods=['POST'])
def change_hostname():
    name = request.form['hostname']
    pm.update_config('robot.name', name)
    flash('Robot name was changed to {}'.format(name), 'warning')
    return ('', 204)


@app.route('/logs')
def logs():
    try:
        with open(pm.config.info.logfile) as f:
            content = f.read()
    except IOError:
        content = 'No log found...'
    return render_template('logs.html', logs_content=content)


@app.route('/update-logs')
def update_logs():
    try:
        with open(pm.config.update.logfile) as f:
            content = f.read()
    except IOError:
        content = 'No log found...'
    return render_template('update.html', update_logs_content=content)


@app.route('/reset')
def reset():
    if pm.running:
        pm.stop()

    pm.start()
    flash('Your robot has been restarted.', 'warning')
    return redirect(url_for('index'))


@app.route('/update')
def update():
    @copy_current_request_context
    def update_in_bg():
        success = pm.self_update()

        if success:
            flash('Your robot is now up-to-date!', 'success')
        else:
            flash('Update failed, check logs for details!', 'alert')

    flash('Your robot is currently updating. '
          'Please do not turn it off before it\'s done!', 'warning')

    if not pm.is_updating:
        Thread(target=update_in_bg).start()

    return redirect(url_for('update_logs'))


@app.route('/updating')
def is_updating():
    return 'true' if pm.is_updating else 'false'


@app.route('/done-updating')
def done_updating():
    flash('Your robot is now up-to-date!', 'success')
    return redirect(url_for('index'))


@app.route('/camera', methods=['POST'])
def switch_camera():
    checked = request.form['checked']
    pm.update_config('robot.camera', True if checked == 'on' else False)
    flash('Your robot camera is now turned {}!'.format(checked), 'success')
    return ('', 204)


@app.route('/configure-motors')
def configure_motors():
    # Remove old poppy-configure output to avoid user confusion
    try:
        os.remove(pm.config.poppy_configure.logfile)
    except OSError:
        pass
    return render_template('motor-configuration.html', motors=pm._get_robot_motor_list())


@app.route('/call_poppy_configure', methods=['POST'])
def call_poppy_configure():
    motor = request.form['motor']
    pm.update_config('robot.motors', motor)
    return ('', 204)

@app.route('/settings/wifi')
def configure_wifi():
    return render_template('wifi.html')

@app.route('/wifi/list')
def wifi_list():
    return

@app.route('/configure_hostspot', methods=['POST'])
def hostspot_configuration():
    return


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


@app.route('/shutdown')
def shutdown():
    pm.shutdown()
    return render_template(
        'shutdown.html',
        shutdown_msg='Your {} will now be halted in a few seconds.'.format(pm.config.info.board)
    )


@app.route('/api/raw_logs')
def raw_logs():
    try:
        with open(pm.config.info.logfile) as f:
            content = f.read()
    except IOError:
        content = 'No log found...'
    return Response(content, mimetype='text/plain')


@app.route('/api/update_raw_logs')
def update_raw_logs():
    try:
        with open(pm.config.update.logfile) as f:
            content = f.read()
    except IOError:
        content = 'No log found...'
    return Response(content, mimetype='text/plain')


@app.route('/api/configure_motors_logs')
def poppy_config_logs():
    try:
        with open(pm.config.poppy_configure.logfile) as f:
            content = f.read()
    except IOError:
        content = ''
    return Response(content, mimetype='text/plain')


def get_host():
    host = pm.config.robot.name
    host = host if host == 'localhost' else '{}.local'.format(host)
    return host


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=2280)
