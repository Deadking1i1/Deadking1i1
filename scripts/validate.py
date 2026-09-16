from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent.parent
errors = []

for svg in sorted(list((root / "assets").glob("*.svg")) + list((root / "generated").glob("*.svg"))):
    try:
        ET.parse(svg)
    except ET.ParseError as exc:
        errors.append(f"Invalid SVG/XML in {svg.relative_to(root)}: {exc}")

for workflow in sorted((root / ".github" / "workflows").glob("*.yml")):
    text = workflow.read_text(encoding="utf-8")
    for key in ("name:", "on:", "jobs:"):
        if key not in text:
            errors.append(f"Workflow {workflow.name} is missing {key}")
    if "\t" in text:
        errors.append(f"Workflow {workflow.name} contains tab indentation")

if errors:
    print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
    raise SystemExit(1)

print("SVG/XML and workflow structure checks passed.")
