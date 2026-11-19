"""Standalone narrowband radio waterfall QA, not a Voyager detection.

Four assumptions: regularly spaced time-frequency samples, power in linear
nonnegative units, independent reference channels for the baseline estimate,
and no calibration from instrumental units to flux density.
"""
from __future__ import annotations
import math
import statistics
from numbers import Integral


def robust_channel_snr(power, exclusion_index: int):
    """Median/MAD standardized channel excess for one spectrum.

    The target channel is excluded from the baseline; this statistic is not
    Gaussian significance without calibration of noise and trial factors.
    """
    x = [float(v) for v in power]
    if len(x) < 5 or any(not math.isfinite(v) or v < 0 for v in x):
        raise ValueError("need >=5 finite nonnegative power channels")
    if (isinstance(exclusion_index, bool) or not isinstance(exclusion_index, Integral)
            or not 0 <= exclusion_index < len(x)):
        raise ValueError("invalid target index")
    ref = [v for i, v in enumerate(x) if i != exclusion_index]
    med = statistics.median(ref)
    mad = statistics.median(abs(v - med) for v in ref)
    if mad <= 0:
        raise ValueError("zero robust baseline scale")
    return (x[exclusion_index] - med) / (1.4826 * mad)


def drift_track_power(waterfall, start_channel: int, drift_channels_per_row: float):
    """Nearest-bin drift-track mean and indices; no sub-channel interpolation."""
    rows = [[float(v) for v in row] for row in waterfall]
    if not rows or len(rows[0]) < 3 or any(
        len(row) != len(rows[0]) or any(not math.isfinite(v) or v < 0 for v in row)
        for row in rows
    ) or not math.isfinite(drift_channels_per_row):
        raise ValueError("invalid rectangular power waterfall or drift")
    if isinstance(start_channel, bool) or not isinstance(start_channel, Integral):
        raise ValueError("start channel must be integer")
    start_channel = int(start_channel)
    idx = [math.floor(start_channel + t * drift_channels_per_row + 0.5)
           for t in range(len(rows))]
    if any(i < 0 or i >= len(rows[0]) for i in idx):
        raise ValueError("track exits measured band")
    return {"mean_power": statistics.fmean(row[i] for row, i in zip(rows, idx)),
            "indices": idx}


if __name__ == "__main__":
    import unittest

    class AuditTests(unittest.TestCase):
        def test_robust_excess(self):
            self.assertGreater(robust_channel_snr([1, 2, 3, 4, 5, 30], 5), 10)

        def test_drift(self):
            result = drift_track_power([[0, 5, 0, 0], [0, 0, 5, 0],
                                        [0, 0, 0, 5]], 1, 1)
            self.assertEqual(result["indices"], [1, 2, 3])
            self.assertEqual(result["mean_power"], 5)

        def test_invalid(self):
            with self.assertRaises(ValueError):
                robust_channel_snr([1, 1, 1, 1, 5], 4)
            for invalid_index in (True, 1.5, -1):
                with self.subTest(index=invalid_index), self.assertRaises(ValueError):
                    robust_channel_snr([1, 2, 3, 4, 5], invalid_index)
            self.assertEqual(drift_track_power([[1, 2, 3]], 2, 1)["indices"], [2])
            with self.assertRaisesRegex(ValueError, "track exits measured band"):
                drift_track_power([[1, 2, 3], [4, 5, 6]], 2, 1)

    unittest.main()
