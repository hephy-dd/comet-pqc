import copy
import glob
import re
import os

import jsonschema
import yaml
import pint.errors

import comet

__all__ = [
    'load_config',
    'load_chuck',
    'load_wafer',
    'load_sequence',
    'list_configs'
]

PACKAGE_DIR = os.path.dirname(__file__)
SCHEMA_DIR = os.path.join(PACKAGE_DIR, 'schema')
CONFIG_DIR = os.path.join(PACKAGE_DIR, 'config')
CHUCK_DIR = os.path.join(CONFIG_DIR, 'chuck')
WAFER_DIR = os.path.join(CONFIG_DIR, 'wafer')
SEQUENCE_DIR = os.path.join(CONFIG_DIR, 'sequence')

def load_schema(name):
    """Loads a YAML validation schema from the schema directory.

    >>> load_schema("wafer")
    {...}
    """
    with open(os.path.join(SCHEMA_DIR, f'{name}.yaml')) as f:
        return yaml.safe_load(f.read())

def load_config(filename, schema=None):
    """Loads a YAML configuration file and optionally validates the content
    using the provided schema.

    >>> load_config("sample.yaml", schema="wafer")
    {...}
    """
    with open(filename) as f:
        config_data = yaml.safe_load(f.read())
    if schema is not None:
        schema_data = load_schema(schema)
        jsonschema.validate(config_data, schema_data)
    return config_data

def load_chuck(filename):
    """Returns a chuck configuration object, provided for convenience.

    >>> load_chuck("chuck.yaml")
    <Chuck ...>
    """
    return Chuck(**load_config(filename, schema='chuck'))

def load_wafer(filename):
    """Returns a wafer configuration object, provided for convenience.

    >>> load_chuck("wafer.yaml")
    <Wafer ...>
    """
    return Wafer(**load_config(filename, schema='wafer'))

def load_sequence(filename):
    """Returns a measurement sequence configuration object, provided for
    convenience.

    >>> load_sequence("sequence.yaml")
    <Sequence ...>
    """
    return Sequence(**load_config(filename, schema='sequence'))

def list_configs(directory):
    """Retruns list of located configuration files as tuples containing
    configuration name and filename.

    >>> list_configs("config/wafer")
    [('Default HMW N', 'config/wafer/default_hmw_n.yaml')]
    """
    items = []
    for filename in glob.glob(os.path.join(directory, '*.yaml')):
        data = load_config(filename)
        items.append((data.get('name'), filename))
    return items

class Position:

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class Chuck:

    def __init__(self, id, name, enabled=True, description="", positions=[]):
        self.id = id
        self.name = name
        self.enabled = enabled
        self.description = description
        self.positions = list(map(lambda kwargs: ChuckPosition(**kwargs), positions))

    def __str__(self):
        return self.name

class ChuckPosition:

    def __init__(self, id, name, pos, enabled=True, description=""):
        self.id = id
        self.name = name
        self.pos = Position(**pos)
        self.enabled = enabled
        self.description = description

class Wafer:

    def __init__(self, id, name, enabled=True, description="", connections=[]):
        self.id = id
        self.name = name
        self.enabled = enabled
        self.description = description
        self.connections = list(map(lambda kwargs: WaferConnection(**kwargs), connections))

    def __str__(self):
        return self.name

class WaferConnection:

    def __init__(self, id, name, pos, type=None, enabled=True, description=""):
        self.id = id
        self.name = name
        self.type = type
        self.enabled = enabled
        self.pos = Position(**pos)
        self.description = description

class Sequence:

    def __init__(self, id, name, enabled=True, description="", connections=[]):
        self.id = id
        self.name = name
        self.enabled = enabled
        self.description = description
        self.connections = list(map(lambda kwargs: SequenceConnection(**kwargs), connections))

    def __str__(self):
        return self.name

    def __iter__(self):
        return iter(self.connections)

    def __len__(self):
        return len(self.connections)

class SequenceConnection:

    def __init__(self, name, connection, enabled=True, description="", measurements=[]):
        self.name = name
        self.connection = connection
        self.enabled = enabled
        self.description = description
        self.measurements = list(map(lambda kwargs: SequenceMeasurement(**kwargs), measurements))

    def __iter__(self):
        return iter(self.measurements)

    def __len__(self):
        return len(self.measurements)

class SequenceMeasurement:

    def __init__(self, name, type, enabled=True, description="", parameters={}):
        self.name = name
        self.type = type
        self.enabled = enabled
        self.description = description
        self.parameters = {}
        for key, value in parameters.items():
            if isinstance(value, str):
                try:
                    value = comet.ureg(value)
                except pint.errors.UndefinedUnitError:
                    pass
            if isinstance(value, list):
                for i in range(len(value)):
                    if isinstance(value[i], str):
                        try:
                            value[i] = comet.ureg(value[i])
                        except pint.errors.UndefinedUnitError:
                            pass
            self.parameters[key] = value
        self.default_parameters = copy.deepcopy(self.parameters)
