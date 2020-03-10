import re

# TODO: integrate into comet.Range
def auto_step(start, stop, step):
    """Returns positive/negative step according to start and stop value."""
    return -abs(step) if start > stop else abs(step)

# TODO: intefgrate into comet.utils
def safe_filename(filename):
    return re.sub(r'[^\w\+\-\.\_]+', '_', filename)
