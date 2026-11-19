"""Replot the observed Breakthrough Listen Voyager sample in a fixed 1 kHz band."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import urlopen

import h5py
import hdf5plugin  # noqa: F401 - filter registration for the released HDF5
import matplotlib.pyplot as plt
import numpy as np


FILENAME = "Voyager1.single_coarse.fine_res.h5"
SOURCE = "http://blpd0.ssl.berkeley.edu/Voyager_data/" + FILENAME
EXPECTED_SHA256 = "c9a9a54f4140e3754ffb2455fae4eeb2eb70c8207123116ee953e4fce15c36ac"
EXPECTED_SIZE = 50_549_227
LOW, HIGH = 8419.2740, 8419.2750
RIDGE_WINDOWS_HZ = ((220, 460), (490, 760))


def verify(path):
    if path.stat().st_size != EXPECTED_SIZE:
        raise ValueError("Source byte count differs from the recorded Voyager sample.")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != EXPECTED_SHA256:
            raise ValueError("Source SHA-256 differs from the recorded Voyager sample.")


def acquire(path):
    if path.exists():
        verify(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".h5.part")
    try:
        with urlopen(SOURCE, timeout=60) as response, partial.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        verify(partial)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def read_band(path):
    verify(path)
    with h5py.File(path, "r") as handle:
        raw = handle["data"]
        attrs = raw.attrs
        count = int(attrs["nchans"])
        if raw.ndim != 3 or raw.shape[1:] != (1, count) or attrs["source_name"] != "Voyager1":
            raise ValueError("Unexpected observed source or filterbank shape.")
        frequency = float(attrs["fch1"]) + np.arange(count) * float(attrs["foff"])
        indices = np.flatnonzero((frequency >= LOW) & (frequency <= HIGH))
        if not len(indices):
            raise ValueError("Requested frequencies are outside the released spectrum.")
        start, stop = indices[0], indices[-1] + 1
        order = np.argsort(frequency[start:stop])
        power = np.asarray(raw[:, 0, start:stop], dtype=float)[:, order]
        time = np.arange(len(power)) * float(attrs["tsamp"])
        axis = (frequency[start:stop][order] - LOW) * 1e6
        return time, axis, power, float(attrs["tsamp"]), abs(float(attrs["foff"])) * 1e6


def plot_band(time, frequency, power, spacing_s, spacing_hz, output):
    if not np.isfinite(power).all() or np.min(power) <= 0:
        raise ValueError("The decibel display requires positive finite recorded powers.")
    relative_db = 10 * np.log10(power / np.median(power))
    fig, ax = plt.subplots(figsize=(8.2, 4.6), layout="constrained")
    image = ax.imshow(relative_db, cmap="cividis", origin="lower", aspect="auto",
                      interpolation="nearest", extent=(frequency[0] - spacing_hz / 2,
                          frequency[-1] + spacing_hz / 2, time[0] - spacing_s / 2,
                          time[-1] + spacing_s / 2))
    ax.set(title="Voyager 1 observation · Breakthrough Listen / GBT",
           xlabel=f"Frequency offset from {LOW:.4f} MHz (Hz)",
           ylabel="Time from first integration centre (s)")
    fig.colorbar(image, ax=ax, label="Power relative to the window median (dB)")
    fig.savefig(output, dpi=210, facecolor="white")
    plt.close(fig)


def replay(path, output):
    time, frequency, power, cadence, spacing = read_band(path)
    output.mkdir(parents=True, exist_ok=True)
    plot_band(time, frequency, power, cadence, spacing, output / "voyager_waterfall.png")
    ridges = []
    for low, high in RIDGE_WINDOWS_HZ:
        keep = (frequency >= low) & (frequency <= high)
        peak = frequency[keep][np.argmax(power[:, keep], axis=1)]
        ridges.append({"offset_window_hz": [low, high],
                       "apparent_slope_hz_per_s": float(np.polyfit(time, peak, 1)[0])})
    result = {
        "source": SOURCE, "sha256": EXPECTED_SHA256, "band_mhz": [LOW, HIGH],
        "time_rows": len(time), "frequency_channels": len(frequency),
        "row_cadence_s": cadence, "channel_width_hz": spacing, "local_ridges": ridges,
        "interpretation": "Descriptive slopes for selected visible ridges in topocentric frequency. Instrumental power is uncalibrated."
    }
    (output / "voyager_replay.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(FILENAME))
    parser.add_argument("--output", type=Path, default=Path("voyager_output"))
    args = parser.parse_args()
    acquire(args.input)
    print(json.dumps(replay(args.input, args.output), indent=2))


if __name__ == "__main__":
    main()
