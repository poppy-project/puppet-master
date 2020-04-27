import yaml


class Config(object):
    def __init__(self, dict, filename=None):
        object.__setattr__(self, '_{}__config'.format(type(self).__name__), dict)
        object.__setattr__(self, '_{}__file'.format(type(self).__name__), filename)

    def close(self):
        filename = self.__dict__['_{}__file'.format(type(self).__name__)]

        if filename is not None:
            with open(filename, 'w') as f:
                f.write(yaml.safe_dump(self.as_dict(), default_flow_style=False))

    def as_dict(self):
        return self.__dict__['_{}__config'.format(type(self).__name__)]

    @classmethod
    def from_file(cls, filename):
        with open(filename) as f:
            return cls(yaml.load(f, Loader=yaml.SafeLoader), filename)

    def __repr__(self):
        return str(self.as_dict())

    def __getattr__(self, key):
        value = self.__config[key]
        if isinstance(value, dict):
            return Config(value)

        return value

    def __setattr__(self, key, value):
        config = self.__dict__['_{}__config'.format(type(self).__name__)]
        config[key] = value


def attrsetter(item):
    def resolve_attr(obj, attr):
        if not attr:
            return obj
        for name in attr.split('.'):
            obj = getattr(obj, name)
        return obj

    def g(obj, value):
        var_path, _, var_name = item.rpartition('.')
        setattr(resolve_attr(obj, var_path), var_name, value)

    return g

if __name__ == '__main__':
    from contextlib import closing

    with closing(Config.from_file('/tmp/config.yaml')) as c:
        print(c)
        print(c.robot)
        print(c.robot.name)

        c.robot.dummy = 42
        print(c.robot)
