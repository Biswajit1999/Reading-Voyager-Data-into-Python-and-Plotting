"""Build an offline inventory for this repository's selected research evidence."""

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CONFIG = "evidence/sources.json"
MANIFEST = "evidence/manifest.json"
TEXT_TYPES = {".csv", ".tsv", ".json", ".md", ".txt", ".svg", ".yaml", ".yml"}
PREVIEW_ROWS = 4
PREVIEW_COLUMNS = 7


def read_bytes(path, committed=False):
    relative = PurePosixPath(path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Evidence path must be relative to this repository: {path}")
    if committed:
        return subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=ROOT)
    return (ROOT / path).read_bytes()


def trimmed(value):
    text = str(value)
    return text if len(text) <= 130 else text[:127] + "..."


def describe(path, content):
    suffix = PurePosixPath(path).suffix.lower()
    if suffix in {".csv", ".tsv"}:
        source = io.StringIO(content.decode("utf-8-sig"), newline="")
        reader = csv.reader(source, delimiter="\t" if suffix == ".tsv" else ",")
        header = next(reader, [])
        rows = 0
        preview = []
        for row in reader:
            if not any(cell.strip() for cell in row):
                continue
            rows += 1
            if len(preview) < PREVIEW_ROWS:
                preview.append([trimmed(cell) for cell in row[:PREVIEW_COLUMNS]])
        return {
            "format": suffix[1:].upper(),
            "rows": rows,
            "columns": len(header),
            "headers": header[:PREVIEW_COLUMNS],
            "preview": preview,
        }
    if suffix == ".json":
        value = json.loads(content.decode("utf-8-sig"))
        if isinstance(value, list):
            result = {"format": "JSON", "records": len(value)}
            if value and isinstance(value[0], dict):
                result["fields"] = list(value[0])[:PREVIEW_COLUMNS]
            return result
        if isinstance(value, dict):
            return {
                "format": "JSON",
                "keys": list(value)[:PREVIEW_COLUMNS],
                "arrays": {key: len(item) for key, item in value.items() if isinstance(item, list)},
            }
    if suffix in {".fits", ".fit"}:
        return {"format": "FITS"}
    return {"format": suffix.lstrip(".").upper()}


def build_manifest(committed=False):
    config = json.loads(read_bytes(CONFIG, committed))
    files = []
    for source in config["files"]:
        path = source["path"]
        content = read_bytes(path, committed)
        canonical_lf = PurePosixPath(path).suffix.lower() in TEXT_TYPES
        if canonical_lf:
            content = content.replace(b"\r\n", b"\n")
        files.append({
            **source,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "hash_basis": "LF-normalised text" if canonical_lf else "exact bytes",
            **describe(path, content),
        })
    return {"schema": 1, "project": config["project"], "repository": config["repository"], "files": files}


def manifest_bytes(committed=False):
    payload = json.dumps(build_manifest(committed), indent=2, ensure_ascii=False) + "\n"
    return payload.encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify the current files")
    mode.add_argument("--check-committed", action="store_true", help="verify the HEAD snapshot")
    args = parser.parse_args()
    rendered = manifest_bytes(args.check_committed)
    if args.check or args.check_committed:
        current = read_bytes(MANIFEST, args.check_committed).replace(b"\r\n", b"\n")
        if current != rendered:
            parser.exit(1, "Evidence inventory is stale. Run python scripts/evidence_catalog.py.\n")
        print("Evidence inventory verified.")
    else:
        (ROOT / MANIFEST).write_bytes(rendered)


if __name__ == "__main__":
    main()
