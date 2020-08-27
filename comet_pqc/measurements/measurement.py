import datetime

import comet
from comet.resource import ResourceMixin
from comet.process import ProcessMixin

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
    output_dir = ""

    measurement_item = None

    def __init__(self, process):
        self.process = process
        self.registered_parameters = {}

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

    def create_filename(self, dt=None, suffix=None):
        """Return standardized measurement filename.

        >>> self.create_filename()
        'HPK_VPX1234_001_HM_WW_PQCFlutesRight_PQC_Flute_1_Diode_IV_2020-03-04T12-27-03.txt'
        """
        iso_timestamp = comet.make_iso(dt)
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
        suffix = suffix or "txt"
        return comet.safe_filename(f"{basename}.{suffix}")

    def run(self, *args, **kwargs):
        """Run measurement."""
        return self.code(**kwargs)

    def code(self, *args, **kwargs):
        """Implement custom measurement logic in method `code()`."""
        raise NotImplementedError(f"Method `{self.__class__.__name__}.code()` not implemented.")
