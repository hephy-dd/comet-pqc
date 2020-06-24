import comet
from comet.resource import ResourceMixin

__all__ = ["Measurement"]

class ParameterType:

    def __init__(self, key, default, values, unit, type, required):
        self.key = key
        self.default = default
        self.values = values
        self.unit = unit
        self.type = type
        self.required = required

class Measurement(ResourceMixin):
    """Base measurement class."""

    type = "measurement"

    sample_name = ""
    sample_type = ""
    output_dir = ""

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
        '2020-03-04T12-27-03_HPK_VPX1234_001_HM_WW_PQC_Flute_1_Diode_IV.txt'
        """
        iso_timestamp = comet.make_iso(dt)
        sample_name = self.sample_name
        sample_type = self.sample_type
        contact_name = self.measurement_item.contact.name
        measurement_name = self.measurement_item.name
        basename = "_".join((
            iso_timestamp,
            sample_name,
            sample_type,
            contact_name,
            measurement_name
        ))
        suffix = suffix or "txt"
        return comet.safe_filename(f"{basename}.{suffix}")

    def run(self, *args, **kwargs):
        """Run measurement."""
        return self.code(**kwargs)

    def code(self, *args, **kwargs):
        """Implement custom measurement logic in method `code()`."""
        raise NotImplementedError(f"Method `{self.__class__.__name__}.code()` not implemented.")
