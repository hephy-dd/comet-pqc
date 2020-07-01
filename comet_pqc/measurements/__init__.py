from .iv_ramp import *
from .iv_ramp_elm import *
from .iv_ramp_bias import *
from .iv_ramp_bias_elm import *
from .iv_ramp_4_wire import *
from .cv_ramp import *
from .cv_ramp_hv import *
from .cv_ramp_alt import *
from .frequency_scan import *

def measurement_factory(type, *args, **kwargs):
    """Factory function to create a new measurement instance by type.

    >>> meas = measurement_factory("iv_ramp")
    >>> meas.run()
    """
    for cls in globals().values():
        if hasattr(cls, "type"):
            if cls.type == type:
                return cls(*args, **kwargs)
