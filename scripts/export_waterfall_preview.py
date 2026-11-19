"""Extract the saved waterfall from the versioned observation notebook."""

from base64 import b64decode
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
notebook = root / "Reading Voyager data and plotting.ipynb"
cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
images = [
    output["data"]["image/png"]
    for cell in cells if "obs.plot_waterfall(" in "".join(cell.get("source", []))
    for output in cell.get("outputs", []) if "image/png" in output.get("data", {})
]
if len(images) != 1:
    raise ValueError(f"Expected one saved waterfall, found {len(images)}")
image = b64decode("".join(images[0]).replace("\n", ""), validate=True)
if not image.startswith(b"\x89PNG\r\n\x1a\n"):
    raise ValueError("Saved output is not a PNG")
destination = root / "assets/voyager1-waterfall.png"
destination.parent.mkdir(exist_ok=True)
destination.write_bytes(image)
