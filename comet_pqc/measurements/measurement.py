import datetime
import logging
import time
import json
import os

import comet
from comet.resource import ResourceMixin
from comet.process import ProcessMixin
from ..formatter import PQCFormatter

__all__ = ['Measurement']

QUICK_RAMP_DELAY = 0.100

class ComplianceError(ValueError): pass

def format_estimate(est):
    """Format estimation message without milliseconds."""
    elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
    remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
    average = datetime.timedelta(seconds=round(est.average.total_seconds()))
    return "Elapsed {} | Remaining {} | Average {}".format(elapsed, remaining, average)

class ParameterType:

    def __init__(self, key, default, values, unit, type, required):
        self.key = key
        self.default = default
        self.values = values
        self.unit = unit
        self.type = type
        self.required = required

class Measurement(ResourceMixin, ProcessMixin):
    """Base measurement class."""

    type = "measurement"

    sample_name = ""
    sample_type = ""
    operator = ""
    output_dir = ""
    write_logfiles = False

    measurement_item = None
    output_basename = None

    KEY_META = "meta"
    KEY_SERIES = "series"
    KEY_SERIES_UNITS = "series_units"

    FORMAT_ISO = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, process):
        self.process = process
        self.registered_parameters = {}
        self.__timestamp_start = 0
        self.__data = {}

    @property
    def timestamp_start(self):
        """Returns start timestamp in seconds."""
        return self.__timestamp_start

    @property
    def timestamp_start_iso(self):
        """Returns start timestamp as ISO formatted string."""
        return datetime.datetime.fromtimestamp(self.timestamp_start).strftime(self.FORMAT_ISO)

    @property
    def data(self):
        """Measurement data property."""
        return self.__data

    def register_parameter(self, key, default=None, *, values=None, unit=None, type=None,
                           required=False):
        """Register measurement parameter."""
        if key in self.registered_parameters:
            raise KeyError(f"parameter already registered: {key}")
        self.registered_parameters[key] = ParameterType(
            key, default, values, unit, type, required
        )

    def get_parameter(self, key):
        """Get measurement parameter."""
        if key not in self.registered_parameters:
            raise KeyError(f"no such parameter: {key}")
        parameter = self.registered_parameters[key]
        if key not in self.measurement_item.parameters:
            if parameter.required:
                raise ValueError(f"missing required parameter: {key}")
        value = self.measurement_item.parameters.get(key, parameter.default)
        if parameter.unit:
            ### TODO !!!
            ### return comet.ureg(value).to(spec.unit).m
            return value.to(parameter.unit).m
        if callable(parameter.type):
            value = parameter.type(value)
        if parameter.values:
            if not value in parameter.values:
                raise ValueError(f"invalid parameter value: {value}")
        return value

    def create_filename(self, dt=None, suffix=''):
        """Return standardized measurement filename.

        >>> self.create_filename(suffix='.txt')
        'HPK_VPX1234_001_HM_WW_PQCFlutesRight_PQC_Flute_1_Diode_IV_2020-03-04T12-27-03.txt'
        """
        iso_timestamp = comet.make_iso(dt or self.timestamp_start)
        sample_name = self.sample_name
        sample_type = self.sample_type
        contact_id = self.measurement_item.contact.id
        measurement_id = self.measurement_item.id
        basename = "_".join((
            sample_name,
            sample_type,
            contact_id,
            measurement_id,
            iso_timestamp
        ))
        return comet.safe_filename(f"{basename}{suffix}")

    def set_meta(self, key, value):
        self.data.get(self.KEY_META)[key] = value

    def set_series_unit(self, key, value):
        self.data.get(self.KEY_SERIES_UNITS)[key] = value

    def register_series(self, key):
        series = self.data.get(self.KEY_SERIES)
        if key in series:
            raise KeyError(f"Series already exists: {key}")
        series[key] = []

    def append_series(self, **kwargs):
        series = self.data.get(self.KEY_SERIES)
        if sorted(series.keys()) != sorted(kwargs.keys()):
            raise KeyError("Inconsistent series keys")
        for key, value in kwargs.items():
            series.get(key).append(value)

    def create_logger(self):
        """Create log file handler."""
        log_filename = os.path.join(self.output_dir, self.create_filename(suffix='.log'))
        if not os.path.exists(os.path.dirname(log_filename)):
            os.makedirs(os.path.dirname(log_filename))
        log_handler = logging.FileHandler(filename=log_filename)
        log_handler.setFormatter(logging.Formatter(
            fmt='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        ))
        return log_handler

    def serialize_json(self):
        """Serialize data dictionary to JSON."""
        with open(os.path.join(self.output_dir, self.create_filename(suffix='.json')), 'w') as f:
            json.dump(self.data, f, indent=2)

    def serialize_txt(self):
        """Serialize data dictionary to plain text."""
        with open(os.path.join(self.output_dir, self.create_filename(suffix='.txt')), 'w') as f:
            meta = self.data.get("meta", {})
            series_units = self.data.get("series_units", {})
            series = self.data.get("series", {})
            fmt = PQCFormatter(f)
            # Write meta data
            for key, value in meta.items():
                fmt.write_meta(key, value)
            # Create columns
            columns = list(series.keys())
            for key in columns:
                fmt.add_column(key, "E", unit=series_units.get(key))
            # Write header
            fmt.write_header()
            # Write series
            if columns:
                size = len(series.get(columns[0]))
                for i in range(size):
                    row = {}
                    for key in columns:
                        row[key] = series.get(key)[i]
                    fmt.write_row(row)
            fmt.flush()

    def before_initialize(self, **kwargs):
        self.data.clear()
        self.data["meta"] = {}
        self.data["series_units"] = {}
        self.data["series"] = {}
        self.set_meta("sample_name", self.sample_name)
        self.set_meta("sample_type", self.sample_type)
        self.set_meta("contact_name", self.measurement_item.contact.name)
        self.set_meta("measurement_name", self.measurement_item.name)
        self.set_meta("measurement_type", self.type)
        self.set_meta("start_timestamp", self.timestamp_start_iso)
        self.set_meta("operator", self.operator)

    def initialize(self, **kwargs):
        pass

    def after_initialize(self, **kwargs):
        pass

    def measure(self, **kwargs):
        pass

    def before_finalize(self, **kwargs):
        pass

    def finalize(self, **kwargs):
        pass

    def after_finalize(self, **kwargs):
        pass

    def run(self, **kwargs):
        """Run measurement."""
        self.__timestamp_start = time.time()
        # Start measurement log file
        log_handler = None
        if self.write_logfiles:
            log_handler = self.create_logger()
            logging.getLogger().addHandler(log_handler)
        try:
            logging.info(f"Initialize...")
            self.before_initialize(**kwargs)
            self.initialize(**kwargs)
            self.after_initialize(**kwargs)
            logging.info(f"Initialize... done.")
            logging.info(f"Measure...")
            self.measure(**kwargs)
            logging.info(f"Measure... done.")
        except Exception as exc:
            logging.error(exc)
            raise
        finally:
            logging.info(f"Finalize...")
            self.before_finalize(**kwargs)
            self.finalize(**kwargs)
            self.after_finalize(**kwargs)
            # Stop measurement log file
            if log_handler is not None:
                logging.getLogger().removeHandler(log_handler)
            logging.info(f"Finalize... done.")
