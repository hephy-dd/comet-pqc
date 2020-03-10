from comet.device import DeviceMixin

__all__ = ["Measurement"]

class Measurement(DeviceMixin):
    """Base measurement class."""

    type = "measurement"

    def __init__(self, process):
        self.process = process

    def run(self, *args, **kwargs):
        """Run measurement."""
        return self.code(**kwargs)

    def code(self, *args, **kwargs):
        """Implement custom measurement logic in method `code()`."""
        raise NotImplementedError(f"Method `{self.__class__.__name__}.code()` not implemented.")
