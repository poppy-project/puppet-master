import os
import argparse

from string import Template


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deploy script for puppet master',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('hostname', type=str, help='Hostname of the machine used')
    parser.add_argument('creature', type=str, help='Creature used')

    parser.add_argument('--config-path', type=str,
                        default=os.path.expanduser('~/.poppy_config.yaml'),
                        help='Path to deploy the config file.')

    args = parser.parse_args()

    # Install config from default template
    with open('default_config.yaml') as f:
        s = Template(f.read())

    s = s.substitute(name=args.hostname, creature=args.creature,
                     home=os.path.expanduser('~'))

    with open(args.config_path, 'w') as f:
        f.write(s)
