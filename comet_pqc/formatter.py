import csv
import os

class FormatterError(Exception):

    pass

class Formatter:

    pass

class CSVFormatter(Formatter):
    """CSV formatter.

    >>> with open('data.csv', 'w', newline='') as f:
    >>>     fmt = CSVFormatter(f)
    >>>     fmt.add_column('key')
    >>>     fmt.add_column('value', '+E')
    >>>     fmt.write_header()
    >>>     fmt.write_row(dict(key='spam', value=42.0))
    """

    def __init__(self, f, linesep=None, **kwargs):
        self.__writer = csv.DictWriter(f, [], lineterminator='', **kwargs)
        self.__format_specs = {}
        self.__f = f
        self.__has_rows = False
        if linesep is None:
            linesep = os.linesep
        self.linesep = linesep

    @property
    def columns(self):
        return self.__writer.fieldnames

    def format_spec(self, name):
        return self.__format_specs.get(name, '')

    def add_column(self, name, format_spec=None):
        """Add table column, optional format spec for values."""
        if name in self.__writer.fieldnames:
            raise ValueError(f"column name already exists: {name}")
        if format_spec is None:
            format_spec = ''
        self.__writer.fieldnames.append(name)
        self.__format_specs[name] = format_spec

    def write_header(self):
        """Write CSV header.

        Raise `FormatterError` if `write_row` was called.
        """
        if self.__has_rows:
            raise FormatterError("header must be written before rows")
        self.__writer.writeheader()
        self.__f.write(self.linesep)
        self.__has_rows = True

    def write_row(self, row):
        """Write CSV row, applying column formats."""
        for key in row:
            row[key] = format(row[key], self.format_spec(key))
        self.__writer.writerow(row)
        self.__f.write(self.linesep)
        self.__has_rows = True

    def flush(self):
        """Flush write buffer."""
        self.__f.flush()

class PQCHeader:

    def __init__(self, name, unit=None):
        self.name = name
        self.unit = unit

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other

    def __str__(self):
        if self.unit is not None:
            return f'{self.name}[{self.unit}]'
        return self.name

class PQCFormatter(CSVFormatter):
    """PQC formatter.

    >>> with open('data.csv', 'w', newline='') as f:
    >>>     fmt = PQCFormatter(f)
    >>>     fmt.add_column('key')
    >>>     fmt.add_column('value', '+E')
    >>>     fmt.write_meta('ham', 1.23, 'G')
    >>>     fmt.write_header()
    >>>     fmt.write_row(dict(key='spam', value=42.0))
    """

    Header = PQCHeader

    def __init__(self, f):
        super().__init__(f, dialect='excel-tab')
        self.__f = f
        self.__has_rows = False

    def write_meta(self, key, value, format_spec=None):
        """Write meta information, optional format spec.

        Raise `FormatterError` if `write_header` or `write_row` was called before.
        """
        if self.__has_rows:
            raise FormatterError("meta data must be written before header/rows")
        if format_spec is None:
            format_spec = ''
        value = format(value, format_spec)
        self.__f.write(f"{key}: {value}")
        self.__f.write(os.linesep)
        self.__f.flush()

    def add_column(self, name, format_spec=None, unit=None):
        super().add_column(type(self).Header(name, unit), format_spec)

    def write_header(self):
        """Write CSV header.

        Raise `FormatterError` if `write_row` was called.
        """
        super().write_header()
        self.__has_rows = True

    def write_row(self, row):
        """Write CSV row, applying column formats."""
        super().write_row(row)
        self.__has_rows = True
