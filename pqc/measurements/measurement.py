import contextlib
import json
import logging
import math
import time
from datetime import timedelta
from typing import Callable, List, Optional

import comet
import numpy as np

from ..core.formatter import PQCFormatter

__all__ = ["Measurement"]

logger = logging.getLogger(__name__)

KEY_META = "meta"
KEY_SERIES = "series"
KEY_SERIES_UNITS = "series_units"
KEY_ANALYSIS = "analysis"


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
    elapsed = timedelta(seconds=round(est.elapsed.total_seconds()))
    remaining = timedelta(seconds=round(est.remaining.total_seconds()))
    average = timedelta(seconds=round(est.average.total_seconds()))
    return "Elapsed {} | Remaining {} | Average {}".format(elapsed, remaining, average)


def annotate_step(name):
    def annotate_step(method):
        def annotate_step(self, *args, **kwargs):
            logger.info("%s %s...", name, self.type)
            try:
                method(self, *args, **kwargs)
            except Exception as exc:
                logger.error(exc)
                logger.error("%s %s... failed.", name, self.type)
                raise
            else:
                logger.info("%s %s... done.", name, self.type)
        return annotate_step
    return annotate_step


def serialize_json(data: dict, fp) -> None:
    """Serialize data dictionary to JSON."""
    json.dump(data, fp, indent=2, cls=NumpyEncoder)


def serialize_txt(data: dict, fp) -> None:
    """Serialize data dictionary to plain text."""
    meta = data.get("meta", {})
    series_units = data.get("series_units", {})
    series = data.get("series", {})
    fmt = PQCFormatter(fp)
    # Write meta data
    for key, value in meta.items():
        if key == "measurement_tags":
            value = ", ".join([tag for tag in value if tag])
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


class ParameterType:

    def __init__(self, key, default, values, unit, type, required):
        self.key = key
        self.default = default
        self.values = values
        self.unit = unit
        self.type = type
        self.required = required


class Measurement:
    """Base measurement class."""

    type: str = ""

    required_instruments: list = []

    def __init__(self, process, measurement_parameters, measurement_default_parameters, timestamp: float) -> None:
        self.process = process
        self.measurement_parameters: dict = measurement_parameters
        self.measurement_default_parameters: dict = measurement_default_parameters
        self.registered_parameters: dict = {}
        self.timestamp = timestamp
        self._data: dict = {}
        self._data[KEY_META] = {}
        self._data[KEY_SERIES_UNITS] = {}
        self._data[KEY_SERIES] = {}
        self._data[KEY_ANALYSIS] = {}

    @property
    def data(self):
        """Measurement data property."""
        return self._data

    def register_parameter(self, key, default=None, *, values=None, unit=None, type=None,
                           required=False):
        """Register measurement parameter."""
        if key in self.registered_parameters:
            raise KeyError(f"parameter already registered: {key}")
        self.registered_parameters[key] = ParameterType(
            key, default, values, unit, type, required
        )

    def validate_parameters(self):  # TODO
        for key in self.measurement_default_parameters.keys():
            if key not in self.registered_parameters:
                logger.warning("Unknown parameter: %s", key)
        missing_keys = []
        for key, parameter in self.registered_parameters.items():
            if parameter.required:
                if key not in self.measurement_parameters:
                    missing_keys.append(key)
        if missing_keys:
            ValueError(f"missing required parameter(s): {missing_keys}")

    def get_parameter(self, key):  # TODO
        """Get measurement parameter."""
        if key not in self.registered_parameters:
            raise KeyError(f"no such parameter: {key}")
        parameter = self.registered_parameters[key]
        if key not in self.measurement_parameters:
            if parameter.required:
                raise ValueError(f"missing required parameter: {key}")
        value = self.measurement_parameters.get(key, parameter.default)
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
        logger.info("Meta %s: %s", key, value)
        self.data.get(KEY_META)[key] = value

    def set_series_unit(self, key, value):
        self.data.get(KEY_SERIES_UNITS)[key] = value

    def register_series(self, key):
        series = self.data.get(KEY_SERIES)
        if key in series:
            raise KeyError(f"Series already exists: {key}")
        series[key] = []

    def get_series(self, key):
        return self.data.get(KEY_SERIES).get(key, [])

    def set_analysis(self, key, value):
        self.data.get(KEY_ANALYSIS)[key] = value

    def append_series(self, **kwargs):
        series = self.data.get(KEY_SERIES)
        if sorted(series.keys()) != sorted(kwargs.keys()):
            raise KeyError("Inconsistent series keys")
        for key, value in kwargs.items():
            series.get(key).append(value)

    def wait(self, seconds, interval=1.0):
        logger.info("Waiting %s s...", seconds)
        interval = abs(interval)
        steps = math.ceil(seconds / interval)
        remaining = seconds
        self.process.set_message(f"Waiting {seconds} s...")
        for step in range(steps):
            self.process.set_progress(step + 1, steps)
            if remaining >= interval:
                time.sleep(interval)
            else:
                time.sleep(remaining)
            remaining -= interval
            if self.process.stop_requested:
                return
        logger.info("Waiting %s s... done.", seconds)
        self.process.set_message("")

    def before_initialize(self, **kwargs):
        self.validate_parameters()

    def initialize(self, **kwargs):
        ...

    def after_initialize(self, **kwargs):
        ...

    def measure(self, **kwargs):
        ...

    def before_finalize(self, **kwargs):
        ...

    def finalize(self, **kwargs):
        ...

    def after_finalize(self, **kwargs):
        ...

    def analyze(self, **kwargs):
        ...

    @annotate_step("Initialize")
    def _initialize(self, **kwargs):
        self.process.set_message("Initialize...")
        self.before_initialize(**kwargs)
        self.initialize(**kwargs)
        self.after_initialize(**kwargs)
        self.process.set_message("Initialize... done.")

    @annotate_step("Measure")
    def _measure(self, **kwargs):
        self.process.set_message("Measure...")
        self.measure(**kwargs)
        self.process.set_message("Measure... done.")

    @annotate_step("Finalize")
    def _finalize(self, **kwargs):
        self.process.set_message("Finalize...")
        self.before_finalize(**kwargs)
        self.finalize(**kwargs)
        self.after_finalize(**kwargs) # is not executed on error
        self.process.set_message("Finalize... done.")

    @annotate_step("Analyze")
    def _analyze(self, **kwargs):
        self.process.set_message("Analyze...")
        self.analyze(**kwargs)
        self.process.set_message("Analyze... done.")

    def run(self, station) -> None:
        """Run measurement.

        If initialize, measure or analyze fails, finalize is executed before
        raising any exception.
        """
        with contextlib.ExitStack() as es:
            kwargs = {}
            for key in type(self).required_instruments:
                cls = station.create_instrument(key)
                resource = station.resources.get(key)
                kwargs.update({key: cls(es.enter_context(resource))})
            try:
                self._initialize(**kwargs)
                self._measure(**kwargs)
            finally:
                try:
                    self._finalize(**kwargs)
                finally:
                    self._analyze(**kwargs)
