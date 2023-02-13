from io import StringIO

from comet_pqc.view.sequencetreewidget import load_sequence_tree, dump_sequence_tree


def test_load_sequence():
    fp = StringIO("""{"version": 1, "sequence": [1, 2, 3]}""")
    sequence = load_sequence_tree(fp)
    assert sequence == [1, 2, 3]


def test_dump_sequence():
    sequence = [1, 2, 3]
    fp = StringIO()
    dump_sequence_tree(sequence, fp)
    fp.seek(0)
    assert load_sequence_tree(fp) == sequence
