import comet
from comet.resource import ResourceMixin

__all__ = ["Measurement"]

class Measurement(ResourceMixin):
    """Base measurement class."""

    type = "measurement"
    sample_name = ""
    sample_type = ""
    output_dir = ""

    def __init__(self, process):
        self.process = process

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
