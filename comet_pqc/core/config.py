import copy
import glob
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import comet
import jsonschema
import pint.errors
import yaml

from .position import Position
from .utils import make_path

__all__ = [
    "load_config",
    "load_chuck",
    "load_sample",
    "load_sequence",
    "list_configs"
]

ASSETS_DIR: str = make_path("assets")
SCHEMA_DIR: str = os.path.join(ASSETS_DIR, "schema")
CONFIG_DIR: str = os.path.join(ASSETS_DIR, "config")
CHUCK_DIR: str = os.path.join(CONFIG_DIR, "chuck")
SAMPLE_DIR: str = os.path.join(CONFIG_DIR, "sample")
SEQUENCE_DIR: str = os.path.join(CONFIG_DIR, "sequence")


def make_id(name: str) -> str:
    """Construct a mixed case ID string without special characters from name.

    >>> make_id("Nobody, expects THE (spanish) inquisition!")
    'Nobody_expects_THE_spanish_inquisition_'
    """
    return re.sub(r"[^\w\-]+", "_", name.strip()).strip("_")


def load_schema(name: str) -> dict:
    """Loads a YAML validation schema from the schema directory.

    >>> load_schema("sample")
    {...}
    """
    with open(os.path.join(SCHEMA_DIR, f"{name}.yaml"), "rt") as f:
        return yaml.safe_load(f.read())


def validate_config(data: dict, schema: str) -> None:
    """Validate config data using schema name."""
    schema_data = load_schema(schema)
    jsonschema.validate(data, schema_data)


def load_config(filename: str, schema: Optional[str] = None) -> dict:
    """Loads a YAML configuration file and optionally validates the content
    using the provided schema.

    >>> load_config("sample.yaml", schema="sample")
    {...}
    """
    with open(filename, "rt") as f:
        config_data = yaml.safe_load(f.read())
    if schema is not None:
        validate_config(config_data, schema)
    return config_data


def load_chuck(filename: str) -> "Chuck":
    """Returns a chuck configuration object, provided for convenience.

    >>> load_chuck("chuck.yaml")
    <Chuck ...>
    """
    return Chuck(**load_config(filename, schema="chuck"), filename=filename)


def load_sample(filename: str) -> "Sample":
    """Returns a sample configuration object, provided for convenience.

    >>> load_chuck("sample.yaml")
    <Sample ...>
    """
    return Sample(**load_config(filename, schema="sample"), filename=filename)


def load_sequence(filename: str) -> "Sequence":
    """Returns a measurement sequence configuration object, provided for
    convenience.

    >>> load_sequence("sequence.yaml")
    <Sequence ...>
    """
    return Sequence(**load_config(filename, schema="sequence"), filename=filename)


def list_configs(directory: str) -> List[Tuple[str, str]]:
    """Retruns list of located configuration files as tuples containing
    configuration name and filename.

    >>> list_configs("config/sample")
    [('Default HMW N', 'config/sample/default_hmw_n.yaml')]
    """
    items = []
    for filename in glob.glob(os.path.join(directory, "*.yaml")):
        data = load_config(filename)
        items.append((data.get("name", ""), filename))
    return items


class Chuck:
    """Chuck configuration."""

    def __init__(self, id: str, name: str, enabled: bool = True, description: Optional[str] = None, positions: Optional[List] = None, filename: Optional[str] = None) -> None:
        self.id: str = id
        self.name: str = name
        self.enabled: bool = enabled
        self.description: str = description or ""
        self.positions: List = list(map(lambda kwargs: ChuckSamplePosition(**kwargs), positions or []))
        self.filename: str = filename or ""

    def __str__(self) -> str:
        return self.name


class ChuckSamplePosition:
    """Chuck sample position."""

    def __init__(self, id: str, name: str, pos, enabled: bool = True, description: Optional[str] = None):
        self.id: str = id
        self.name: str = name
        self.pos: Position = Position(**pos)
        self.enabled: bool = enabled
        self.description: str = description or ""


class Sample:
    """Silicon sample."""

    def __init__(self, id: str, name: str, enabled: bool = True, description: Optional[str] = None, contacts: Optional[List] = None, filename: Optional[str] =None):
        self.id: str = id
        self.name: str = name
        self.enabled: bool = enabled
        self.description: str = description or ""
        self.contacts: List = list(map(lambda kwargs: SampleContact(**kwargs), contacts or []))
        self.filename: str = filename or ""

    def __str__(self) -> str:
        return self.name


class SampleContact:
    """Sample contact geometry."""

    def __init__(self, id: str, name: str, pos, type: Optional[str] = None, enabled: bool = True, description: Optional[str] = None):
        self.id: str = id
        self.name: str = name
        self.type: str = type or ""
        self.enabled: bool = enabled
        self.pos: Position = Position(**pos)
        self.description: str = description or ""


class Sequence:
    """Sequence configuration."""

    def __init__(self, id: str, name: str, enabled: bool = True, description: Optional[str] = None, contacts: Optional[List] = None, filename: Optional[str] = None):
        self.id: str = id
        self.name: str = name
        self.enabled: bool = enabled
        self.description: str = description or ""
        self.contacts: List = list(map(lambda kwargs: SequenceContact(**kwargs), contacts or []))
        self.filename: str = filename or ""

    def __str__(self) -> str:
        return self.name

    def __iter__(self) -> Iterable:
        return iter(self.contacts)

    def __len__(self) -> int:
        return len(self.contacts)


class SequenceContact:
    """Sequence contact point."""

    def __init__(self, name: str, contact_id: str, id: Optional[str] = None, enabled: bool = True, description: Optional[str] = None, measurements: Optional[List] = None):
        self.id: str = id or make_id(name)
        self.name: str = name
        self.contact_id: str = contact_id
        self.enabled: bool = enabled
        self.description: str = description or ""
        self.measurements: List = list(map(lambda kwargs: SequenceMeasurement(**kwargs), measurements or []))

    def __iter__(self) -> Iterable:
        return iter(self.measurements)

    def __len__(self) -> int:
        return len(self.measurements)


class SequenceMeasurement:
    """Sequence measurement configuration."""

    key_ignorelist = ["matrix_enable", "matrix_channels", "analyze_function"]

    def __init__(self, name: str, type: str, id: Optional[str] = None, enabled: bool = True, tags: Optional[List] = None, description: Optional[str] = None, parameters: Optional[Dict] = None):
        self.id: str = id or make_id(name)
        self.name: str = name
        self.type: str = type
        self.enabled: bool = enabled
        self.tags: List = list(map(format, tags or []))
        self.description: str = description or ""
        self.parameters: Dict = {}
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
    def to_quantity(cls, value: Any) -> Any:
        """Auto convert to quantity for Pint units."""
        try:
            return comet.ureg(value)
        except pint.errors.UndefinedUnitError:
            return value
