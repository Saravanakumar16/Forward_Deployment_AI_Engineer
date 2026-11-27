"""Download the 30 selected Kubernetes Markdown files at the pinned commit.

Files are written to data/k8s-docs/<original source path> so the original
filenames and paths are retained. Uses raw.githubusercontent.com (no git needed).

    python scripts/fetch_dataset.py            # skip files that already exist
    python scripts/fetch_dataset.py --force    # re-download everything
"""
import json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
force = "--force" in sys.argv
base = f"https://raw.githubusercontent.com/kubernetes/website/{manifest['commit']}/"

for d in manifest["documents"]:
    dest = ROOT / "data/k8s-docs" / d["source_path"]
    if dest.exists() and not force:
        print(f"exists  {d['document_id']:10} {d['source_path']}")
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(base + d["source_path"], timeout=30) as r:
        dest.write_bytes(r.read())
    print(f"fetched {d['document_id']:10} {d['source_path']}")
print(f"Done: {len(manifest['documents'])} files under data/k8s-docs/ (commit {manifest['commit'][:7]})")
