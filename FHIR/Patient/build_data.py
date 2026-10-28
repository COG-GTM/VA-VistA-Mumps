"""Regenerate data/dd_file2.json, data/lookups.json, MAPPING.md and mapping.csv.

Run from this directory with the repo's DD.zwr and pointer-file globals checked out:

    python build_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

from vista_fhir_patient import citations, dd, lookups  # noqa: E402
from vista_fhir_patient.report import write_reports  # noqa: E402


def build_dd() -> dict:
    files = dd.extract_from_repo(REPO_ROOT)
    out: dict = {"source": dd.DD_RELPATH, "source_sha": citations.SOURCE_SHA, "files": {}}
    for fileno in sorted(files, key=float):
        fields = {}
        for num in sorted(files[fileno], key=float):
            fd = files[fileno][num]
            row = fd.to_json()
            row["routine_citations"] = []
            for ref in fd.routine_refs:
                cit = citations.resolve(REPO_ROOT, ref)
                if cit is None:
                    raise SystemExit(f"cannot resolve {ref} for {fd.key}; check out its routine")
                row["routine_citations"].append(
                    {"ref": cit.ref, "path": cit.path, "line": cit.line, "text": cit.text}
                )
            fields[num] = row
        out["files"][fileno] = fields
    return out


def main() -> None:
    data_dir = HERE / "data"
    data_dir.mkdir(exist_ok=True)
    dd_json = build_dd()
    (data_dir / "dd_file2.json").write_text(json.dumps(dd_json, indent=1, sort_keys=True) + "\n")
    (data_dir / "lookups.json").write_text(
        json.dumps(lookups.build(REPO_ROOT), indent=1, sort_keys=True) + "\n"
    )
    write_reports(HERE, dd_json)
    total = sum(len(v) for v in dd_json["files"].values())
    print(f"wrote {total} field definitions, lookups, MAPPING.md, mapping.csv")


if __name__ == "__main__":
    main()
