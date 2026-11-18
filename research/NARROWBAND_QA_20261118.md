# Narrowband waterfall conditional QA — 18 November 2026

Author: Biswajit Jana. AI-assisted code preparation disclosed.

Two independent methods in `narrowband_qa_20261118.py`:
(1) robust per-spectrum excess using a median and MAD computed after excluding the target frequency channel;
(2) nearest-bin linear drift-track power extraction across time-frequency rows.

The input is a rectangular matrix of nonnegative linear power (arbitrary units). No background removal, flux calibration, Doppler correction, barycentric correction, RFI excision, or frequency/time metadata are inferred. The robust statistic is not a detection significance without a calibrated noise null, multiple-trial correction, and instrumental verification. The drift parameter has units channels per row; conversion to Hz/s requires measured channel width and row cadence. Nearest-bin tracking incurs discretization error, particularly for fractional drift.

Reproduce: `python research/narrowband_qa_20261118.py`.
No Voyager observations have been loaded, and no spacecraft signal detection or measured SNR is claimed.
