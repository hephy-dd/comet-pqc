from typing import Any, Iterable, List, Tuple, Type

from comet.settings import SettingsMixin
from comet.driver.keithley import K707B as K707BInstrument

from .core.position import Position
from .instruments.k2410 import K2410Instrument
from .instruments.k2470 import K2470Instrument
from .instruments.k2657a import K2657AInstrument
from .utils import (from_table_unit, safe_bool, safe_float, safe_int,
                    to_table_unit)

__all__ = ["settings"]


class TablePosition(Position):

    def __init__(self, name: str, x: float, y: float, z: float, comment: str) -> None:
        super().__init__(x, y, z)
        self.name: str = name
        self.comment: str = comment

    def __str__(self) -> str:
        return f"{self.name}"


class Settings(SettingsMixin):

    def value(self, key: str, default: Any, type: Type) -> Any:
        return type(self.settings.get(key, default))

    def setValue(self, key: str, value: Any) -> None:
        self.settings[key] = value

    def table_positions(self) -> List[TablePosition]:
        """List of user defined table positions for movement operations."""
        positions: List[TablePosition] = []
        for position in self.value("table_positions", [], list):
            name = position.get("name")
            x = from_table_unit(position.get("x") or 0)
            y = from_table_unit(position.get("y") or 0)
            z = from_table_unit(position.get("z") or 0)
            comment = position.get("comment")
            positions.append(TablePosition(name, x, y, z, comment))
        return positions

    def set_table_positions(self, positions: Iterable[TablePosition]) -> None:
        table_positions = []
        for position in positions:
            table_positions.append({
                "name": position.name,
                "x": to_table_unit(position.x),
                "y": to_table_unit(position.y),
                "z": to_table_unit(position.z),
                "comment": position.comment,
            })
        self.setValue("table_positions", table_positions)

    def table_z_limit(self) -> float:
        """Table Z limit in millimeters."""
        return from_table_unit(self.value("z_limit_movement", 0, float))

    def set_table_z_limit(self, value: float) -> None:
        self.setValue("z_limit_movement", to_table_unit(value))

    def table_probecard_maximum_limits(self) -> Tuple[float, float, float]:
        default = 0.0, 0.0, 0.0
        try:
            limits = self.value("table_probecard_maximum_limits", {}, dict)
            return (
                from_table_unit(limits.get("x", 0.0)),
                from_table_unit(limits.get("y", 0.0)),
                from_table_unit(limits.get("z", 0.0)),
            )
        except Exception:
            return default

    def set_table_probecard_maximum_limits(self, value: Tuple[float, float, float]) -> None:
        x, y, z = value
        self.setValue("table_probecard_maximum_limits", {
            "x": to_table_unit(x),
            "y": to_table_unit(y),
            "z": to_table_unit(z),
        })

    def table_temporary_z_limit(self) -> bool:
        return self.value("table_temporary_z_limit", False, bool)

    def set_table_temporary_z_limit(self, value: bool) -> None:
        self.setValue("table_temporary_z_limit", bool(value))

    @property
    def table_joystick_maximum_limits(self):
        default = 0.0, 0.0, 0.0
        try:
            limits = self.value("table_joystick_maximum_limits", {}, dict)
            return (
                from_table_unit(limits.get("x", 0.0)),
                from_table_unit(limits.get("y", 0.0)),
                from_table_unit(limits.get("z", 0.0))
            )
        except Exception:
            return default

    @table_joystick_maximum_limits.setter
    def table_joystick_maximum_limits(self, value):
        x, y, z = value
        self.setValue("table_joystick_maximum_limits", {
            "x": to_table_unit(x),
            "y": to_table_unit(y),
            "z": to_table_unit(z)
        })

    @property
    def table_control_update_interval(self) -> float:
        return safe_float(self.value("table_control_update_interval", 1.0, float))

    @table_control_update_interval.setter
    def table_control_update_interval(self, value: float):
        self.setValue("table_control_update_interval", float(value))

    @property
    def table_control_dodge_enabled(self):
        return self.value("table_control_dodge_enabled", False, bool)

    @table_control_dodge_enabled.setter
    def table_control_dodge_enabled(self, value):
        self.setValue("table_control_dodge_enabled", bool(value))

    @property
    def table_control_dodge_height(self):
        return from_table_unit(safe_int(self.value("table_control_dodge_height", 500, float)))  # from micron

    @table_control_dodge_height.setter
    def table_control_dodge_height(self, value):
        self.setValue("table_control_dodge_height", to_table_unit(value))

    def operators(self) -> List[str]:
        return self.value("operators", [], list)

    def setOperators(self, operators: List[str]) -> None:
        self.setValue("operators", operators)

    def currentOperator(self) -> int:
        return self.value("current_operator", 0, int)

    def setCurrentOperator(self, index: int) -> None:
        self.setValue("current_operator", index)

    def outputPaths(self) -> List[str]:
        return self.value("output_path", [], list)

    def setOutputPaths(self, paths: List[str]) -> None:
        self.setValue("output_path", paths)

    def currentOutputPath(self) -> int:
        return safe_int(self.value("current_output_path", 0, int))

    def setCurrentOutputPath(self, index: int) -> None:
        self.setValue("current_output_path", index)

    @property
    def matrix_instrument(self):
        matrix_instrument = self.value("matrix_instrument", "K707B", str)
        return {
            "K707B": K707BInstrument,
        }.get(matrix_instrument)

    @property
    def vsrc_instrument(self):
        vsrc_instrument = self.value("vsrc_instrument", "K2657A", str)
        return {
            "K2410": K2410Instrument,
            "K2470": K2470Instrument,
            "K2657A": K2657AInstrument,
        }.get(vsrc_instrument)

    @property
    def hvsrc_instrument(self):
        hvsrc_instrument = self.value("hvsrc_instrument", "K2410", str)
        return {
            "K2410": K2410Instrument,
            "K2470": K2470Instrument,
            "K2657A": K2657AInstrument,
        }.get(hvsrc_instrument)

    def retry_measurement_count(self) -> int:
        return safe_int(self.value("retry_measurement_count", 0, int))

    def set_retry_measurement_count(self, value: int) -> None:
        self.setValue("retry_measurement_count", int(value))

    def retry_contact_count(self) -> int:
        return safe_int(self.value("retry_contact_count", 0, int))

    def set_retry_contact_count(self, value: int) -> None:
        self.setValue("retry_contact_count", int(value))

    def retry_contact_overdrive(self) -> float:
        return from_table_unit(self.value("retry_contact_overdrive", 0, float))

    def set_retry_contact_overdrive(self, value: float) -> None:
        self.setValue("retry_contact_overdrive", to_table_unit(value))

    def use_table(self) -> bool:
        return safe_bool(self.value("use_table", False, bool))

    def set_use_table(self, enabled: bool) -> None:
        self.setValue("use_table", safe_bool(enabled))

    def use_environ(self) -> bool:
        return safe_bool(self.value("use_environ", False, bool))

    def set_use_environ(self, enabled: bool) -> None:
        self.setValue("use_environ", safe_bool(enabled))

settings = Settings()
