from typing import Dict, Type

from .generic import Instrument
from .k2410 import K2410Instrument
from .k2470 import K2470Instrument
from .k2657a import K2657AInstrument
from .k6517b import K6517BInstrument
from .e4980a import E4980AInstrument

instrument_registry: Dict[str, Type[Instrument]] = {
    "K2410": K2410Instrument,
    "K2470": K2470Instrument,
    "K2657A": K2657AInstrument,
    "K6517B": K6517BInstrument,
    "E4980A": E4980AInstrument,
}


def get_instrument(model: str) -> Type[Instrument]:
    if model not in instrument_registry:
        raise KeyError(f"No such instrument model: {model!r}")
    return instrument_registry[model]
