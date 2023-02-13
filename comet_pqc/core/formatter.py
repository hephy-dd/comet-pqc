import csv
import os
from typing import Any, Dict, Optional

__all__ = ["FormatterError", "Formatter", "CSVFormatter", "PQCFormatter"]


class FormatterError(Exception):

    ...


class Formatter:

    def __init__(self, f) -> None:
        self._f = f


class CSVFormatter(Formatter):
    """CSV formatter.

    >>> with open("data.csv", "wt", newline="") as f:
    >>>     fmt = CSVFormatter(f)
    >>>     fmt.add_column("key")
    >>>     fmt.add_column("value", "+E")
    >>>     fmt.write_header()
    >>>     fmt.write_row({"key": "spam", "value": 42.0})
    """

    def __init__(self, f, linesep=None, **kwargs) -> None:
        super().__init__(f)
        self._writer: csv.DictWriter = csv.DictWriter(f, fieldnames=[], lineterminator="", **kwargs)
        self._format_specs: dict = {}
        self._has_rows: bool = False
        if linesep is None:
            linesep = os.linesep
        self.linesep = linesep

    @property
    def columns(self):
        return self._writer.fieldnames

    def format_spec(self, name) -> str:
        return self._format_specs.get(name, "")

    def add_column(self, name, format_spec=None) -> None:
        """Add table column, optional format spec for values."""
        if name in self._writer.fieldnames:
            raise ValueError(f"column name already exists: {name}")
        if format_spec is None:
            format_spec = ""
        self._writer.fieldnames.append(name)  # type: ignore
        self._format_specs[name] = format_spec

    def write_header(self) -> None:
        """Write CSV header.

        Raise `FormatterError` if `write_row` was called.
        """
        if self._has_rows:
            raise FormatterError("header must be written before rows")
        self._writer.writeheader()
        self._f.write(self.linesep)
        self._has_rows = True

    def write_row(self, row: Dict[str, Any]) -> None:
        """Write CSV row, applying column formats."""
        for key in row:
            row[key] = format(row[key], self.format_spec(key))
        self._writer.writerow(row)
        self._f.write(self.linesep)
        self._has_rows = True

    def write_line(self, line: str) -> None:
        self._f.write(line)
        self._f.write(os.linesep)

    def flush(self) -> None:
        """Flush write buffer."""
        self._f.flush()


class PQCHeaderItem:

    def __init__(self, name: str, unit: Optional[str] = None) -> None:
        self.name: str = name
        self.unit: Optional[str] = unit

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other) -> bool:
        return self.name == other

    def __str__(self) -> str:
        if self.unit is not None:
            return f"{self.name}[{self.unit}]"
        return f"{self.name}"


class PQCFormatter(CSVFormatter):
    """PQC formatter.

    >>> with open("data.csv", "wt", newline="") as f:
    >>>     fmt = PQCFormatter(f)
    >>>     fmt.add_column("key")
    >>>     fmt.add_column("value", "+E")
    >>>     fmt.write_meta("ham", 1.23, "G")
    >>>     fmt.write_header()
    >>>     fmt.write_row({"key": "spam", "value": 42.0})
    """

    def __init__(self, f) -> None:
        super().__init__(f, dialect="excel-tab")
        self._has_rows = False

    def write_meta(self, key, value, format_spec=None) -> None:
        """Write meta information, optional format spec.

        Raise `FormatterError` if `write_header` or `write_row` was called before.
        """
        if self._has_rows:
            raise FormatterError("Meta data must be written before header/rows")
        if format_spec is None:
            format_spec = ""
            # Lower case boolean
            if isinstance(value, bool):
                value = format(value).lower()
        value = format(value, format_spec)
        self.write_line(f"{key}: {value}")
        self.flush()

    def add_column(self, name, format_spec=None, unit=None) -> None:
        super().add_column(PQCHeaderItem(name, unit), format_spec)
