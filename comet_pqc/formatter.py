import csv
import os
from typing import Optional

__all__ = [
    "FormatterError",
    "Formatter",
    "CSVFormatter",
    "PQCFormatter"
]


class FormatterError(Exception):

    ...


class Formatter:

    ...


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
        self._writer: csv.DictWriter = csv.DictWriter(f, fieldnames=[], lineterminator="", **kwargs)
        self._format_specs: dict = {}
        self._has_rows: bool = False
        if linesep is None:
            linesep = os.linesep
        self.linesep = linesep
        self._f = f

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
        self._writer.fieldnames.append(name)
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

    def write_row(self, row) -> None:
        """Write CSV row, applying column formats."""
        for key in row:
            row[key] = format(row[key], self.format_spec(key))
        self._writer.writerow(row)
        self._f.write(self.linesep)
        self._has_rows = True

    def flush(self) -> None:
        """Flush write buffer."""
        self._f.flush()


class PQCHeader:

    def __init__(self, name: str, unit: str = None) -> None:
        self.name: str = name
        self.unit: Optional[str] = unit

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other) -> bool:
        return self.name == other

    def __str__(self) -> str:
        if self.unit is not None:
            return f"{self.name}[{self.unit}]"
        return self.name


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

    Header = PQCHeader

    def __init__(self, f) -> None:
        super().__init__(f, dialect="excel-tab")
        self._f = f
        self._has_rows = False

    def write_meta(self, key, value, format_spec=None) -> None:
        """Write meta information, optional format spec.

        Raise `FormatterError` if `write_header` or `write_row` was called before.
        """
        if self._has_rows:
            raise FormatterError("meta data must be written before header/rows")
        if format_spec is None:
            format_spec = ""
            # Lower case boolean
            if isinstance(value, bool):
                value = format(value).lower()
        value = format(value, format_spec)
        self._f.write(f"{key}: {value}")
        self._f.write(os.linesep)
        self._f.flush()

    def add_column(self, name, format_spec=None, unit=None) -> None:
        super().add_column(type(self).Header(name, unit), format_spec)

    def write_header(self) -> None:
        """Write CSV header.

        Raise `FormatterError` if `write_row` was called.
        """
        super().write_header()
        self._has_rows = True

    def write_row(self, row) -> None:
        """Write CSV row, applying column formats."""
        super().write_row(row)
        self._has_rows = True
