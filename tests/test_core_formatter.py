import os
from io import StringIO

from comet_pqc.core.formatter import CSVFormatter, PQCFormatter


def test_csv_formatter():
    fp = StringIO()
    fmt = CSVFormatter(fp)
    fmt.add_column("key")
    fmt.add_column("value", "+E")
    fmt.write_header()
    fmt.write_row({"key": "spam", "value": 42.0})
    fmt.write_row({"key": "eggs", "value": -1.0})
    fp.seek(0)
    assert [line.strip() for line in fp] == [
        "key,value",
        "spam,+4.200000E+01",
        "eggs,-1.000000E+00",
    ]


def test_pqc_formatter():
    fp = StringIO()
    fmt = PQCFormatter(fp)
    fmt.add_column("key")
    fmt.add_column("value", "+E")
    fmt.write_meta("param", 1.23, "G")
    fmt.write_header()
    fmt.write_row({"key": "spam", "value": 42.0})
    fp.seek(0)
    assert [line.strip() for line in fp] == [
        "param: 1.23",
        "key\tvalue",
        "spam\t+4.200000E+01",
    ]
