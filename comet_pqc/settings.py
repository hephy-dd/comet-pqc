from typing import Any, Dict, Iterable, List, Tuple, Type

from comet.settings import SettingsMixin

from .instruments import get_instrument
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

    def tablePositions(self) -> List[TablePosition]:
        """List of user defined table positions for movement operations."""
        positions: List[TablePosition] = []
        for position in self.settings.get("table_positions", []):
            name = position.get("name", "")
            x = from_table_unit(position.get("x", 0.))
            y = from_table_unit(position.get("y", 0.))
            z = from_table_unit(position.get("z", 0.))
            comment = position.get("comment", "")
            positions.append(TablePosition(name, x, y, z, comment))
        return positions

    def setTablePositions(self, positions: Iterable[TablePosition]) -> None:
        table_positions = []
        for position in positions:
            table_positions.append({
                "name": position.name,
                "x": to_table_unit(position.x),
                "y": to_table_unit(position.y),
                "z": to_table_unit(position.z),
                "comment": position.comment,
            })
        self.settings["table_positions"] = table_positions

    def tableZLimit(self) -> float:
        """Table Z limit in millimeters."""
        return from_table_unit(self.settings.get("z_limit_movement", 0))

    def setTableZLimit(self, value: float) -> None:
        self.settings["z_limit_movement"] = to_table_unit(value)

    def tableProbecardMaximumLimits(self) -> Tuple[float, float, float]:
        default = 0.0, 0.0, 0.0
        try:
            limits = self.settings.get("table_probecard_maximum_limits", default)
            return (
                from_table_unit(limits.get("x", 0.0)),
                from_table_unit(limits.get("y", 0.0)),
                from_table_unit(limits.get("z", 0.0))
            )
        except Exception:
            return default

    def setTableProbecardMaximumLimits(self, position: Tuple[float, float, float]) -> None:
        x, y, z = position
        self.settings["table_probecard_maximum_limits"] = {
            "x": to_table_unit(x),
            "y": to_table_unit(y),
            "z": to_table_unit(z)
        }

    def tableTemporaryZLimit(self) -> bool:
        return self.settings.get("table_temporary_z_limit", False)

    def setTableTemporaryZLimit(self, value: bool) -> None:
        self.settings["table_temporary_z_limit"] = bool(value)

    def tableJoystickMaximumLimits(self) -> Tuple[float, float, float]:
        default = 0.0, 0.0, 0.0
        try:
            limits = self.settings.get("table_joystick_maximum_limits", default)
            return (
                from_table_unit(limits.get("x", 0.0)),
                from_table_unit(limits.get("y", 0.0)),
                from_table_unit(limits.get("z", 0.0))
            )
        except Exception:
            return default

    def setTableJoystickMaximumLimits(self, value:Tuple[float, float, float]) -> None:
        x, y, z = value
        self.settings["table_joystick_maximum_limits"] = {
            "x": to_table_unit(x),
            "y": to_table_unit(y),
            "z": to_table_unit(z)
        }

    DefaultTableControlUpdateInterval: float = 1.0

    def tableControlUpdateInterval(self) -> float:
        return safe_float(self.settings.get("table_control_update_interval"), self.DefaultTableControlUpdateInterval)

    def setTableControlUpdateInterval(self, value: float) -> None:
        self.settings["table_control_update_interval"] = float(value)

    DefaultTableControlDodgeEnabled: bool = False

    def tableControlDodgeEnabled(self) -> bool:
        return safe_bool(self.settings.get("table_control_dodge_enabled"), self.DefaultTableControlDodgeEnabled)

    def setTableControlDodgeEnabled(self, value: bool):
        self.settings["table_control_dodge_enabled"] = bool(value)

    DefaultTableControlDodgeHeight: int = 500  # micron

    def tableControlDodgeHeight(self) -> float:
        return from_table_unit(safe_int(self.settings.get("table_control_dodge_height"), self.DefaultTableControlDodgeHeight))

    def setTableControlDodgeHeight(self, value: float):
        self.settings["table_control_dodge_height"] = to_table_unit(value)

    def tableContactDelay(self) -> float:
        return safe_float(self.settings.get("table_contact_delay"), 0)

    def setTableContactDelay(self, value: float) -> None:
        self.settings["table_contact_delay"] = float(value)

    def operators(self) -> List[str]:
        return list(self.settings.get("operators", []))

    def setOperators(self, operators: List[str]) -> None:
        self.settings["operators"] = list(operators)

    def currentOperator(self) -> str:
        index = safe_int(self.settings.get("current_operator"), 0)
        operators = self.operators()
        if 0 <= index < len(operators):
            return operators[index]
        return ""

    def setCurrentOperator(self, operator: str) -> None:
        operators = self.operators()
        index = 0
        if operator in operators:
            index = operators.index(operator)
        self.settings["current_operator"] = index

    def outputPath(self) -> List[str]:
        output_path = self.settings.get("output_path", [])
        if isinstance(output_path, str):
            output_path = [output_path] # provide backward compatibility
        return output_path

    def setOutputPath(self, path: Iterable[str]) -> None:
        if isinstance(path, str):
            self.settings["output_path"] = [path]  # provide backward compatibility
        else:
            self.settings["output_path"] = path

    def currentOutputPath(self) -> str:
        index = safe_int(self.settings.get("current_output_path"), 0)
        output_path = self.outputPath()
        if 0 <= index < len(output_path):
            return output_path[index]
        return ""

    def setCurrentOutputPath(self, value: str) -> None:
        output_path = self.outputPath()
        index = 0
        if value in output_path:
            index = output_path.index(value)
        self.settings["current_output_path"] = index

    def instrumentModels(self, name: str) -> List[str]:
        return {
            "matrix": ["K707B"],
            "vsrc": ["K2410", "K2470", "K2657A"],
            "hvsrc": ["K2410", "K2470", "K2657A"],
            "lcr": ["E4980A"],
            "elm": ["K6517B"],
            "environ": ["EnvironmentBox"],
            "table": ["Venus1"],
        }[name]

    def instrumentModel(self, name: str) -> str:
        if name == "matrix":
            return self.settings.get("matrix_instrument", "K707B")
        if name == "vsrc":
            return self.settings.get("vsrc_instrument", "K2657A")
        if name == "hvsrc":
            return self.settings.get("hvsrc_instrument", "K2410")
        if name == "lcr":
            return self.settings.get("lcr_instrument", "E4980A")
        if name == "elm":
            return self.settings.get("elm_instrument", "K6517B")
        if name == "environ":
            return self.settings.get("environ_instrument", "EnvironmentBox")
        if name == "table":
            return self.settings.get("table_instrument", "Venus1")
        raise ValueError(name)

    def resources(self) -> Dict[str, Dict[str, Any]]:
        resources_: Dict[str, Dict[str, Any]] = {}
        for name, resource in self.settings.get("resources", {}).items():  # for compatibility
            resources_.update({name: {
                "models": self.instrumentModels(name),
                "model": self.instrumentModel(name),
                "address": resource.get("resource_name", ""),
                "termination": resource.get("read_termination", "\r\n"),
                "timeout": resource.get("timeout", 8000) / 1e3,
            }})
        return resources_

    def setResources(self, resources: Dict[str, Dict[str, Any]]) -> None:
        resources_: Dict[str, Dict[str, Any]] = {}
        for name, resource in resources.items():  # for compatibility
            resources_.update({name: {
                "resource_name": resource.get("address", ""),
                "read_termination": resource.get("termination", "\r\n"),
                "write_termination": resource.get("termination", "\r\n"),
                "visa_library": "@py",
                "timeout": resource.get("timeout", 4.0) * 1e3,
            }})
            self.settings[f"{name}_instrument"] = resource.get("model", "")
        self.settings["resources"] = resources_

    def getInstrumentType(self, name: str) -> Type:
        model = self.instrumentModel(name)
        if model not in self.instrumentModels(name):
            raise KeyError(f"No such {name!r} instrument model: {model!r}")
        return get_instrument(model)

    def retryMeasurementCount(self) -> int:
        return safe_int(self.settings.get("retry_measurement_count"), 0)

    def setRetryMeasurementCount(self, value: int) -> None:
        self.settings["retry_measurement_count"] = int(value)

    def retryContactCount(self) -> int:
        return safe_int(self.settings.get("retry_contact_count"), 0)

    def setRetryContactCount(self, value: int) -> None:
        self.settings["retry_contact_count"] = int(value)

    def retryContactOverdrive(self):
        return from_table_unit(self.settings.get("retry_contact_overdrive", 0))

    def setRetryContactOverdrive(self, value):
        self.settings["retry_contact_overdrive"] = to_table_unit(value)

    def isPngPlots(self) -> bool:
        return safe_bool(self.settings.get("png_plots"), False)

    def setPngPlots(self, value: bool):
        self.settings["png_plots"] = bool(value)

    def isPointsInPlots(self) -> bool:
        return safe_bool(self.settings.get("points_in_plots"), False)

    def setPointsInPlots(self, value: bool):
        self.settings["points_in_plots"] = bool(value)

    def isPngAnalysis(self) -> bool:
        return safe_bool(self.settings.get("png_analysis"), False)

    def setPngAnalysis(self, value: bool):
        self.settings["png_analysis"] = bool(value)

    def isExportJson(self) -> bool:
        return safe_bool(self.settings.get("export_json"), True)

    def setExportJson(self, value: bool):
        self.settings["export_json"] = bool(value)

    def isExportTxt(self) -> bool:
        return safe_bool(self.settings.get("export_txt"), False)

    def setExportTxt(self, value: bool):
        self.settings["export_txt"] = bool(value)

    def isWriteLogfiles(self) -> bool:
        return safe_bool(self.settings.get("write_logfiles"), True)

    def setWriteLogfiles(self, value: bool):
        self.settings["write_logfiles"] = bool(value)

    def summaryFilename(self) -> str:
        return self.settings.get("summary_filename", "summary.csv")


settings = Settings()
