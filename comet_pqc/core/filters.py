from typing import Iterable

import numpy as np

__all__ = ["std_mean_filter"]


def std_mean_filter(values: Iterable[float], threshold: float) -> bool:
    """Return True if standard deviation (sample) / mean < threshold.

    >>> std_mean_filter([0.250, 0.249], threshold=0.005)
    True
    """
    a = np.array(values)
    mean = np.mean(a)
    # Sample standard deviation with ddof=1 (not population standard deviation)
    # http://stackoverflow.com/questions/34050491/ddg#34050706
    # https://www.sharpsightlabs.com/blog/numpy-standard-deviation/
    sample_std_dev = np.std(a, ddof=1)
    ratio = sample_std_dev / mean
    return ratio < threshold
