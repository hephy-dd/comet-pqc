from abc import ABC

__all__ = ["Instrument"]


class Instrument(ABC):

    def __init__(self, context) -> None:
        self.context = context
