import copy
import glob
import os
import re

import jsonschema
import yaml
import pint.errors

import comet

from .utils import make_path
from .position import Position

__all__ = [
    'load_config',
    'load_chuck',
    'load_sample',
    'load_sequence',
    'list_configs'
]

ASSETS_DIR = make_path('assets')
SCHEMA_DIR = os.path.join(ASSETS_DIR, 'schema')
CONFIG_DIR = os.path.join(ASSETS_DIR, 'config')
CHUCK_DIR = os.path.join(CONFIG_DIR, 'chuck')
SAMPLE_DIR = os.path.join(CONFIG_DIR, 'sample')
SEQUENCE_DIR = os.path.join(CONFIG_DIR, 'sequence')

def make_id(name):
    """Construct a mixed case ID string without special characters from name.

    >>> make_id('Nobody, expects THE (spanish) inquisition!')
    'Nobody_expects_THE_spanish_inquisition_'
    """
    return re.sub(r'[^\w\-]+', '_', name.strip()).strip('_')

def load_schema(name):
    """Loads a YAML validation schema from the schema directory.

    >>> load_schema("sample")
    {...}
    """
    with open(os.path.join(SCHEMA_DIR, f'{name}.yaml')) as f:
        return yaml.safe_load(f.read())

def validate_config(data, schema):
    """Validate config data using schema name."""
    schema_data = load_schema(schema)
    jsonschema.validate(data, schema_data)

def load_config(filename, schema=None):
    """Loads a YAML configuration file and optionally validates the content
    using the provided schema.

    >>> load_config("sample.yaml", schema="sample")
    {...}
    """
    with open(filename) as f:
        config_data = yaml.safe_load(f.read())
    if schema is not None:
        validate_config(config_data, schema)
    return config_data

def load_chuck(filename):
    """Returns a chuck configuration object, provided for convenience.

    >>> load_chuck("chuck.yaml")
    <Chuck ...>
    """
    return Chuck(**load_config(filename, schema='chuck'))

def load_sample(filename):
    """Returns a sample configuration object, provided for convenience.

    >>> load_chuck("sample.yaml")
    <Sample ...>
    """
    return Sample(**load_config(filename, schema='sample'))

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

    >>> list_configs("config/sample")
    [('Default HMW N', 'config/sample/default_hmw_n.yaml')]
    """
    items = []
    for filename in glob.glob(os.path.join(directory, '*.yaml')):
        data = load_config(filename)
        items.append((data.get('name'), filename))
    return items

class Chuck:
    """Chuck configuration."""

    def __init__(self, id, name, enabled=True, description="", positions=None):
        self.id = id
        self.name = name
        self.enabled = enabled
        self.description = description
        self.positions = list(map(lambda kwargs: ChuckSamplePosition(**kwargs), positions or []))

    def __str__(self):
        return self.name

class ChuckSamplePosition:
    """Chuck sample position."""

    def __init__(self, id, name, pos, enabled=True, description=""):
        self.id = id
        self.name = name
        self.pos = Position(**pos)
        self.enabled = enabled
        self.description = description

class Sample:
    """Silicon sample."""

    def __init__(self, id, name, enabled=True, description="", contacts=None):
        self.id = id
        self.name = name
        self.enabled = enabled
        self.description = description
        self.contacts = list(map(lambda kwargs: SampleContact(**kwargs), contacts or []))

    def __str__(self):
        return self.name

class SampleContact:
    """Sample contact geometry."""

    def __init__(self, id, name, pos, type=None, enabled=True, description=""):
        self.id = id
        self.name = name
        self.type = type
        self.enabled = enabled
        self.pos = Position(**pos)
        self.description = description

class Sequence:
    """Sequence configuration."""

    def __init__(self, id, name, enabled=True, description="", contacts=None):
        self.id = id
        self.name = name
        self.enabled = enabled
        self.description = description
        self.contacts = list(map(lambda kwargs: SequenceContact(**kwargs), contacts or []))

    def __str__(self):
        return self.name

    def __iter__(self):
        return iter(self.contacts)

    def __len__(self):
        return len(self.contacts)

class SequenceContact:
    """Sequence contact point."""

    def __init__(self, name, contact_id, id=None, enabled=True, description="", measurements=None):
        self.id = id or make_id(name)
        self.name = name
        self.contact_id = contact_id
        self.enabled = enabled
        self.description = description
        self.measurements = list(map(lambda kwargs: SequenceMeasurement(**kwargs), measurements or []))

    def __iter__(self):
        return iter(self.measurements)

    def __len__(self):
        return len(self.measurements)

class SequenceMeasurement:
    """Sequence measurement configuration."""

    key_ignorelist = ["matrix_enable", "matrix_channels"]

    def __init__(self, name, type, id=None, enabled=True, description="", parameters=None):
        self.id = id or make_id(name)
        self.name = name
        self.type = type
        self.enabled = enabled
        self.description = description
        self.parameters = {}
        for key, value in (parameters or {}).items():
            if key not in self.key_ignorelist:
                if isinstance(value, str):
                    value = self.to_quantity(value)
                if isinstance(value, list):
                    for i in range(len(value)):
                        if isinstance(value[i], str):
                            value[i] = self.to_quantity(value[i])
            self.parameters[key] = value
        self.default_parameters = copy.deepcopy(self.parameters)

    @classmethod
    def to_quantity(cls, value):
        """Auto convert to quantity for Pint units."""
        try:
            return comet.ureg(value)
        except pint.errors.UndefinedUnitError:
            return value
