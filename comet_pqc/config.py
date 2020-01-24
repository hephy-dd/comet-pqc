import glob
import re
import os

import jsonschema
import yaml

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

    def __init__(self, id, name, description="", slots=[]):
        self.id = id
        self.name = name
        self.description = description
        self.slots = list(map(lambda kwargs: ChuckSlot(**kwargs), slots))

class ChuckSlot:

    def __init__(self, id, name, pos, description=""):
        self.id = id,
        self.name = name
        self.pos = Position(**pos)
        self.description = description

class Wafer:

    def __init__(self, id, name, description="", references=[], sockets=[]):
        self.id = id
        self.name = name
        self.description = description
        self.references = list(map(lambda kwargs: WaferReference(**kwargs), references))
        self.sockets = list(map(lambda kwargs: WaferSocket(**kwargs), sockets))

class WaferReference:

    def __init__(self, id, name, pos, type=None, description=""):
        self.id = id
        self.name = name
        self.type = type
        self.pos = Position(**pos)
        self.description = description

class WaferSocket:

    def __init__(self, id, name, pos, type=None, description=""):
        self.id = id
        self.name = name
        self.type = type
        self.pos = Position(**pos)
        self.description = description

class Sequence:

    def __init__(self, id, name, enabled=True, description="", items=[]):
        self.id = id
        self.name = name
        self.enabled = enabled
        self.description = description
        self.items = list(map(lambda kwargs: SequenceItem(**kwargs), items))

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

class SequenceItem:

    def __init__(self, name, socket, enabled=True, description="", measurements=[]):
        self.name = name
        self.socket = socket
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
                if re.match(r'^[+-]?\d+', value.strip()):
                    value = comet.ureg(value)
            self.parameters[key] = value
