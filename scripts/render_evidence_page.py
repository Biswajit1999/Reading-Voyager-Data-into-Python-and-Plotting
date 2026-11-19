"""Render a static evidence browser from the checked-in evidence inventory."""

import argparse
import html
import json
import subprocess
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "evidence/manifest.json"
PAGE = "evidence.html"


def escape(value):
    return html.escape(str(value), quote=True)


def preview(item):
    if not item.get("headers") or not item.get("preview"):
        return ""
    headers = "".join(f'<th scope="col">{escape(cell)}</th>' for cell in item["headers"])
    rows = []
    for row in item["preview"]:
        cells = "".join(
            f"<td>{escape(row[index]) if index < len(row) else ''}</td>"
            for index in range(len(item["headers"]))
        )
        rows.append(f"<tr>{cells}</tr>")
    return (
        "<details><summary>Preview the first records</summary>"
        '<div class="table-scroll" tabindex="0" role="region" aria-label="Table preview"><table aria-label="First records from this file">'
        f"<thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        "</details>"
    )


def facts(item):
    values = [item["format"], f'{item["bytes"]:,} bytes']
    if "rows" in item:
        values.append(f'{item["rows"]:,} data records')
        values.append(f'{item["columns"]:,} columns')
    if "records" in item:
        values.append(f'{item["records"]:,} records')
    if item.get("arrays"):
        counts = [f"{key}: {length:,}" for key, length in list(item["arrays"].items())[:4]]
        values.append("Array lengths " + ", ".join(counts))
    return " · ".join(values)


def file_id(path):
    return "file-" + sha256(path.encode("utf-8")).hexdigest()[:16]


def card(item):
    target = quote(item["path"], safe="/")
    name = escape(item["label"])
    heading = f'<h3><a href="{target}">{name}</a></h3>'
    meta = f'<p class="meta">{escape(facts(item))}</p>'
    links = f'<a href="{target}" download>Download {escape(item["format"])}</a>'
    digest = (
        f'<details><summary>SHA-256, {escape(item["hash_basis"])}</summary>'
        f'<code>{escape(item["sha256"])}</code></details>'
    )
    permalink = f'<a href="#{file_id(item["path"])}" aria-label="Link to {name}">Permalink</a>'
    return (f'<article id="{file_id(item["path"])}">{heading}{meta}{preview(item)}'
            f'<p>{links} · {permalink}</p>{digest}</article>')


STYLES = """
:root{color-scheme:light;background:#f1f3f4;color:#162631;font:1rem/1.55 system-ui,sans-serif}
*{box-sizing:border-box}main{max-width:74rem;margin:auto;padding:clamp(1rem,5vw,4rem)}
header{background:#142b3a;color:#fff;padding:clamp(1rem,3vw,2.75rem);border-radius:12px}
h1{max-width:30ch;font-size:clamp(1.7rem,4.5vw,3.2rem);line-height:1.12;margin:.5rem 0 0}
h2{font-size:clamp(1.35rem,3vw,1.9rem);margin:2rem 0 .75rem}h3{font-size:1.09rem;margin:0}
header p,figcaption,.scope{max-width:76ch}a{color:#0b536e;text-underline-offset:.16em}
header a{color:#b2e5f7}nav{display:flex;gap:.75rem 1.2rem;flex-wrap:wrap}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,17rem),1fr));gap:.8rem}
article,figure{background:#fff;border:1px solid #cdd6dc;border-radius:9px;padding:1rem;min-width:0}
figure{margin:1rem 0}img{display:block;max-width:100%;height:auto;margin:auto}
figcaption{margin-top:.6rem;color:#3b5362}.meta{color:#3b5362;font-size:.9rem}
details{margin:.55rem 0}summary{cursor:pointer}code{overflow-wrap:anywhere}
.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:.85rem}
th,td{text-align:left;vertical-align:top;padding:.4rem;border-bottom:1px solid #dce3e7}
.index ul{display:flex;flex-wrap:wrap;gap:.5rem 1.25rem;margin:1rem 0 0;padding:0;list-style:none}
.skip{position:absolute;top:0;left:.5rem;background:#fff;padding:.7rem;transform:translateY(-120%)}
.skip:focus{transform:none;z-index:1}article:target{outline:3px solid #44687d;scroll-margin-top:1rem}
.table-scroll:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid #7b4107;outline-offset:3px}
"""


def render(manifest):
    title = escape(manifest["project"])
    repository = escape(manifest["repository"])
    files = manifest["files"]
    groups = []
    index = []
    for role in ("Data and provenance", "Tables and numerical results", "Figures"):
        selected = [item for item in files if item["role"] == role]
        if selected:
            entries = "".join(card(item) for item in selected)
            anchor = "group-" + role.lower().replace(" ", "-")
            index.append(f'<li><a href="#{anchor}">{escape(role)} ({len(selected)})</a></li>')
            groups.append(f'<section id="{anchor}"><h2>{escape(role)}</h2><div class="grid">{entries}</div></section>')
    figures = []
    for item in files:
        if item["role"] == "Figures" and item["bytes"] <= 600_000 and len(figures) < 2:
            url = quote(item["path"], safe="/")
            label = escape(item["label"])
            figures.append(
                f'<figure><a href="{url}"><img src="{url}" loading="lazy" alt="{label}"></a>'
                f'<figcaption>{label}. Open the image for the full-resolution file.</figcaption></figure>'
            )
    lead = "<section id=\"selected-figures\"><h2>Selected figures</h2>" + "".join(figures) + "</section>" if figures else ""
    if figures:
        index.insert(0, '<li><a href="#selected-figures">Selected figures</a></li>')
    jump = '<nav aria-label="On this page" class="index"><ul>' + "".join(index) + '</ul></nav>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Research evidence</title>
<style>{STYLES}</style>
</head>
<body>
<a class="skip" href="#evidence-content">Skip to file list</a>
<main>
<header>
<nav aria-label="Evidence links"><a href="{repository}#readme">Methods and references</a><a href="{MANIFEST}" download>Download the file inventory</a></nav>
<h1>{title}</h1>
<p>Browse {len(files)} versioned evidence files. Table previews simply display stored rows. Consult the project report for the source, processing steps, and inference assumptions.</p>
</header>
<div id="evidence-content">
{jump}
{lead}
{''.join(groups)}
</div>
<p class="scope">SHA-256 values verify the stored files. They do not independently validate the scientific analysis. Rebuild this page with <code>python scripts/evidence_catalog.py</code> followed by <code>python scripts/render_evidence_page.py</code>.</p>
</main>
</body>
</html>
"""


def read(path, committed):
    if committed:
        return subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=ROOT)
    return (ROOT / path).read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-committed", action="store_true")
    args = parser.parse_args()
    rendered = render(json.loads(read(MANIFEST, args.check_committed))).encode("utf-8")
    if args.check or args.check_committed:
        if read(PAGE, args.check_committed).replace(b"\r\n", b"\n") != rendered:
            parser.exit(1, "Evidence page is stale. Run python scripts/render_evidence_page.py.\n")
        print("Evidence page verified.")
    else:
        (ROOT / PAGE).write_bytes(rendered)


if __name__ == "__main__":
    main()
