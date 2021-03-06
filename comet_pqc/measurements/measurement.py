import datetime
import logging
import time
import json
import math

import numpy as np

import comet
from comet.resource import ResourceMixin
from comet.process import ProcessMixin

from .. import __version__
from ..formatter import PQCFormatter

__all__ = ['Measurement']

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

class ComplianceError(ValueError):
    """Compliance tripped error."""

class InstrumentError(RuntimeError):
    """Generic instrument error."""

def format_estimate(est):
    """Format estimation message without milliseconds."""
    elapsed = datetime.timedelta(seconds=round(est.elapsed.total_seconds()))
    remaining = datetime.timedelta(seconds=round(est.remaining.total_seconds()))
    average = datetime.timedelta(seconds=round(est.average.total_seconds()))
    return "Elapsed {} | Remaining {} | Average {}".format(elapsed, remaining, average)

def annotate_step(name):
    def annotate_step(method):
        def annotate_step(self, *args, **kwargs):
            logging.info(f"%s %s...", name, self.type)
            try:
                method(self, *args, **kwargs)
            except Exception as exc:
                logging.error(exc)
                logging.error(f"%s %s... failed.", name, self.type)
                raise
            else:
                logging.info(f"%s %s... done.", name, self.type)
        return annotate_step
    return annotate_step

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

    type = NotImplemented

    measurement_item = None # HACK

    KEY_META = "meta"
    KEY_SERIES = "series"
    KEY_SERIES_UNITS = "series_units"
    KEY_ANALYSIS = "analysis"

    FORMAT_ISO = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, process, sample_name, sample_type, table_position, operator, timestamp=None):
        self.process = process
        self.sample_name = sample_name
        self.sample_type = sample_type
        self.table_position = table_position
        self.operator = operator
        self.quality = "Check"
        self.registered_parameters = {}
        self.__timestamp = timestamp or time.time()
        self.__data = {}

    @property
    def timestamp(self):
        """Returns start timestamp in seconds."""
        return self.__timestamp

    @property
    def timestamp_iso(self):
        """Returns start timestamp as ISO formatted string."""
        return datetime.datetime.fromtimestamp(self.timestamp).strftime(self.FORMAT_ISO)

    @property
    def basename(self):
        """Return standardized measurement basename."""
        return "_".join(map(format, (
            self.sample_name,
            self.sample_type,
            self.measurement_item.contact.id,
            self.measurement_item.id,
            comet.make_iso(self.timestamp)
        )))

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

    def validate_parameters(self):
        for key in self.measurement_item.default_parameters.keys():
            if key not in self.registered_parameters:
                logging.warning("Unknown parameter: %s", key)
        missing_keys = []
        for key, parameter in self.registered_parameters.items():
            if parameter.required:
                if key not in self.measurement_item.parameters:
                    missing_keys.append(key)
        if missing_keys:
            ValueError(f"missing required parameter(s): {missing_keys}")

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

    def set_meta(self, key, value):
        self.data.get(self.KEY_META)[key] = value

    def set_series_unit(self, key, value):
        self.data.get(self.KEY_SERIES_UNITS)[key] = value

    def register_series(self, key):
        series = self.data.get(self.KEY_SERIES)
        if key in series:
            raise KeyError(f"Series already exists: {key}")
        series[key] = []

    def get_series(self, key):
        return self.data.get(self.KEY_SERIES).get(key, [])

    def set_analysis(self, key, value):
        self.data.get(self.KEY_ANALYSIS)[key] = value

    def append_series(self, **kwargs):
        series = self.data.get(self.KEY_SERIES)
        if sorted(series.keys()) != sorted(kwargs.keys()):
            raise KeyError("Inconsistent series keys")
        for key, value in kwargs.items():
            series.get(key).append(value)

    def serialize_json(self, fp):
        """Serialize data dictionary to JSON."""
        json.dump(self.data, fp, indent=2, cls=NumpyEncoder)

    def serialize_txt(self, fp):
        """Serialize data dictionary to plain text."""
        meta = self.data.get("meta", {})
        series_units = self.data.get("series_units", {})
        series = self.data.get("series", {})
        fmt = PQCFormatter(fp)
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

    def wait(self, seconds, interval=1.0):
        logging.info("Waiting %s s...", seconds)
        interval = abs(interval)
        steps = math.ceil(seconds / interval)
        remaining = seconds
        self.process.emit("message", f"Waiting {seconds} s...")
        for step in range(steps):
            self.process.emit("progress", step + 1, steps)
            if remaining >= interval:
                time.sleep(interval)
            else:
                time.sleep(remaining)
            remaining -= interval
            if not self.process.running:
                return
        logging.info("Waiting %s s... done.", seconds)
        self.process.emit("message", "")

    def before_initialize(self, **kwargs):
        self.validate_parameters()
        self.data.clear()
        self.data[self.KEY_META] = {}
        self.data[self.KEY_SERIES_UNITS] = {}
        self.data[self.KEY_SERIES] = {}
        self.data[self.KEY_ANALYSIS] = {}
        self.set_meta("sample_name", self.sample_name)
        self.set_meta("sample_type", self.sample_type)
        self.set_meta("contact_name", self.measurement_item.contact.name)
        self.set_meta("measurement_name", self.measurement_item.name)
        self.set_meta("measurement_type", self.type)
        self.set_meta("table_position", tuple(self.table_position))
        self.set_meta("start_timestamp", self.timestamp_iso)
        self.set_meta("operator", self.operator)
        self.set_meta("pqc_version", __version__)

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

    def analyze(self, **kwargs):
        pass

    def run(self, **kwargs):
        """Run measurement."""
        self.__run(**kwargs)

    @annotate_step("Initialize")
    def __initialize(self, **kwargs):
        self.process.emit("message", "Initialize...")
        self.before_initialize(**kwargs)
        self.initialize(**kwargs)
        self.after_initialize(**kwargs)
        self.process.emit("message", "Initialize... done.")

    @annotate_step("Measure")
    def __measure(self, **kwargs):
        self.process.emit("message", "Measure...")
        self.measure(**kwargs)
        self.process.emit("message", "Measure... done.")

    @annotate_step("Finalize")
    def __finalize(self, **kwargs):
        self.process.emit("message", "Finalize...")
        self.before_finalize(**kwargs)
        self.finalize(**kwargs)
        self.after_finalize(**kwargs) # is not executed on error
        self.process.emit("message", "Finalize... done.")

    @annotate_step("Analyze")
    def __analyze(self, **kwargs):
        self.process.emit("message", "Analyze...")
        self.analyze(**kwargs)
        self.process.emit("message", "Analyze... done.")

    def __run(self, **kwargs):
        """Run measurement.

        If initialize, measure or analyze fails, finalize is executed before
        raising any exception.
        """
        try:
            self.__initialize(**kwargs)
            self.__measure(**kwargs)
        finally:
            try:
                self.__finalize(**kwargs)
            finally:
                self.__analyze(**kwargs)
