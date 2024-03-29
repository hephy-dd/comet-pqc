from typing import List

from comet.settings import SettingsMixin

from .instruments.k2410 import K2410Instrument
from .instruments.k2470 import K2470Instrument
from .instruments.k2657a import K2657AInstrument
from .core.position import Position
from .utils import from_table_unit, to_table_unit

__all__ = ["settings"]


def safe_value(type, value, default):
    try:
        return type(value)
    except (ValueError, TypeError):
        return type(default)


def safe_bool(value, default=False):
    return safe_value(bool, value, default)


def safe_int(value, default=0):
    return safe_value(int, value, default)


def safe_float(value, default=0):
    return safe_value(float, value, default)


class TablePosition(Position):

    def __init__(self, name: str, x, y, z, comment=None):
        super().__init__(x, y, z)
        self.name: str = name
        self.comment = comment

    def __str__(self):
        return f"{self.name}"


class Settings(SettingsMixin):

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def __getitem__(self, key):
        return self.settings[key]

    def __setitem__(self, key, value):
        self.settings[key] = value

    @property
    def table_positions(self):
        """List of user defined table positions for movement operations."""
        positions = []
        for position in self.settings.get("table_positions") or []:
            name = position.get("name")
            x = from_table_unit(position.get("x") or 0)
            y = from_table_unit(position.get("y") or 0)
            z = from_table_unit(position.get("z") or 0)
            comment = position.get("comment")
            positions.append(TablePosition(name, x, y, z, comment))
        return positions

    @table_positions.setter
    def table_positions(self, value):
        positions = []
        for position in value:
            positions.append({
                "name": position.name,
                "x": to_table_unit(position.x),
                "y": to_table_unit(position.y),
                "z": to_table_unit(position.z),
                "comment": position.comment,
            })
        self.settings["table_positions"] = positions

    @property
    def table_z_limit(self):
        """Table Z limit in millimeters."""
        return from_table_unit(self.settings.get("z_limit_movement") or 0)

    @table_z_limit.setter
    def table_z_limit(self, value):
        self.settings["z_limit_movement"] = to_table_unit(value)

    @property
    def table_probecard_maximum_limits(self):
        default = 0.0, 0.0, 0.0
        try:
            limits = self.settings.get("table_probecard_maximum_limits") or default
            return (
                from_table_unit(limits.get("x", 0.0)),
                from_table_unit(limits.get("y", 0.0)),
                from_table_unit(limits.get("z", 0.0))
            )
        except Exception:
            return default

    @table_probecard_maximum_limits.setter
    def table_probecard_maximum_limits(self, value):
        x, y, z = value
        self.settings["table_probecard_maximum_limits"] = {
            "x": to_table_unit(x),
            "y": to_table_unit(y),
            "z": to_table_unit(z)
        }

    @property
    def table_temporary_z_limit(self) -> bool:
        return self.settings.get("table_temporary_z_limit") or False

    @table_temporary_z_limit.setter
    def table_temporary_z_limit(self, value: bool) -> None:
        self.settings["table_temporary_z_limit"] = bool(value)

    @property
    def table_joystick_maximum_limits(self):
        default = 0.0, 0.0, 0.0
        try:
            limits = self.settings.get("table_joystick_maximum_limits") or default
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
        self.settings["table_joystick_maximum_limits"] = {
            "x": to_table_unit(x),
            "y": to_table_unit(y),
            "z": to_table_unit(z)
        }

    default_table_control_update_interval = 1.0

    @property
    def table_control_update_interval(self):
        return safe_float(self.settings.get("table_control_update_interval"), self.default_table_control_update_interval)

    @table_control_update_interval.setter
    def table_control_update_interval(self, value):
        self.settings["table_control_update_interval"] = float(value)

    default_table_control_dodge_enabled = False

    @property
    def table_control_dodge_enabled(self):
        return bool(self.settings.get("table_control_dodge_enabled") or self.default_table_control_dodge_enabled)

    @table_control_dodge_enabled.setter
    def table_control_dodge_enabled(self, value):
        self.settings["table_control_dodge_enabled"] = bool(value)

    default_table_control_dodge_height = 500 # micron

    @property
    def table_control_dodge_height(self):
        return from_table_unit(safe_int(self.settings.get("table_control_dodge_height"), self.default_table_control_dodge_height))

    @table_control_dodge_height.setter
    def table_control_dodge_height(self, value):
        self.settings["table_control_dodge_height"] = to_table_unit(value)

    @property
    def table_contact_delay(self) -> float:
        return safe_float(self.settings.get("table_contact_delay"), 0)

    @table_contact_delay.setter
    def table_contact_delay(self, value: float) -> None:
        self.settings["table_contact_delay"] = float(value)

    @property
    def operators(self):
        return list(self.settings.get("operators") or [])

    @operators.setter
    def operators(self, value):
        self.settings["operators"] = list(value)

    @property
    def current_operator(self):
        index = safe_int(self.settings.get("current_operator"), 0)
        operators = self.operators
        if 0 <= index < len(operators):
            return operators[index]
        return None

    @current_operator.setter
    def current_operator(self, value):
        operators = self.operators
        index = 0
        if value in operators:
            index = operators.index(value)
        self.settings["current_operator"] = index

    @property
    def output_path(self):
        output_path = self.settings.get("output_path") or []
        if isinstance(output_path, str):
            output_path = [output_path] # provide backward compatibility
        return output_path

    @output_path.setter
    def output_path(self, value):
        if isinstance(value, str):
            value = [value] # provide backward compatibility
        self.settings["output_path"] = value

    @property
    def current_output_path(self):
        index = safe_int(self.settings.get("current_output_path"), 0)
        output_path = self.output_path
        if 0 <= index < len(output_path):
            return output_path[index]
        return None

    @current_output_path.setter
    def current_output_path(self, value):
        output_path = self.output_path
        index = 0
        if value in output_path:
            index = output_path.index(value)
        self.settings["current_output_path"] = index

    @property
    def vsrc_instrument(self):
        vsrc_instrument = self.settings.get("vsrc_instrument") or "K2657A"
        return {
            "K2410": K2410Instrument,
            "K2470": K2470Instrument,
            "K2657A": K2657AInstrument,
        }.get(vsrc_instrument)

    @property
    def hvsrc_instrument(self):
        hvsrc_instrument = self.settings.get("hvsrc_instrument") or "K2410"
        return {
            "K2410": K2410Instrument,
            "K2470": K2470Instrument,
            "K2657A": K2657AInstrument,
        }.get(hvsrc_instrument)

    @property
    def retry_measurement_count(self):
        return safe_int(self.settings.get("retry_measurement_count"), 0)

    @retry_measurement_count.setter
    def retry_measurement_count(self, value):
        self.settings["retry_measurement_count"] = int(value)

    @property
    def retry_contact_count(self):
        return safe_int(self.settings.get("retry_contact_count"), 0)

    @retry_contact_count.setter
    def retry_contact_count(self, value):
        self.settings["retry_contact_count"] = int(value)

    @property
    def retry_contact_radius(self):
        return from_table_unit(self.settings.get("retry_contact_radius", 10.0))

    @retry_contact_radius.setter
    def retry_contact_radius(self, value):
        self.settings["retry_contact_radius"] = to_table_unit(value)

    @property
    def retry_contact_distance(self):
        return from_table_unit(self.settings.get("retry_contact_distance", 1.0))

    @retry_contact_distance.setter
    def retry_contact_distance(self, value):
        self.settings["retry_contact_distance"] = to_table_unit(value)

    @property
    def retry_contact_overdrive(self):
        return from_table_unit(self.settings.get("retry_contact_overdrive", 0.0))

    @retry_contact_overdrive.setter
    def retry_contact_overdrive(self, value):
        self.settings["retry_contact_overdrive"] = to_table_unit(value)

    @property
    def export_json(self) -> bool:
        return bool(self.settings.get("export_json", True))

    @export_json.setter
    def export_json(self, value: bool) -> None:
        self.settings["export_json"] = bool(value)

    @property
    def export_txt(self) -> bool:
        return bool(self.settings.get("export_txt", True))

    @export_txt.setter
    def export_txt(self, value: bool) -> None:
        self.settings["export_txt"] = bool(value)

    @property
    def png_analysis(self) -> bool:
        return bool(self.settings.get("png_analysis", False))

    @png_analysis.setter
    def png_analysis(self, value: bool) -> None:
        self.settings["png_analysis"] = bool(value)

    @property
    def sequence_filenames(self) -> List[str]:
        filenames = []
        for filename in self.settings.get("custom_sequences", []):
            filenames.append(filename)
        return filenames

    @sequence_filenames.setter
    def sequence_filenames(self, value: List[str]) -> None:
        filenames = [filename for filename in value]
        self.settings["custom_sequences"] = filenames


settings = Settings()
