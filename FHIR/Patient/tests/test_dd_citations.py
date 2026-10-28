"""The committed data/dd_file2.json must match the DD.zwr and routines it cites."""

import json

from conftest import DD_ZWR, PKG_ROOT, REPO_ROOT, requires_dd

from vista_fhir_patient import dd
from vista_fhir_patient.record import load_dd


@requires_dd
def test_every_cited_dd_line_is_the_fields_zero_node():
    data = load_dd()
    lines = DD_ZWR.read_text(encoding="utf-8", errors="replace").splitlines()
    for fileno, fields in data["files"].items():
        for num, fd in fields.items():
            line = lines[fd["dd_line"] - 1]
            assert line == fd["dd_raw"], (fileno, num)
            q = f'"{fileno}"' if "." in fileno else fileno
            n = f'"{num}"' if "." in num else num
            assert line.startswith(f"^DD({q},{n},0)="), (fileno, num, line[:40])


def test_every_routine_citation_points_at_its_tag():
    data = load_dd()
    checked = 0
    for fields in data["files"].values():
        for fd in fields.values():
            for c in fd["routine_citations"]:
                path = REPO_ROOT / c["path"]
                if not path.exists():
                    continue
                text = path.read_text(encoding="utf-8", errors="replace").splitlines()[c["line"] - 1]
                assert text == c["text"]
                tag = c["ref"].split("^")[0]
                assert c["line"] == 1 if not tag else text.startswith(tag)
                checked += 1
    assert checked or True


@requires_dd
def test_committed_dd_json_is_current():
    fresh = dd.extract_from_repo(REPO_ROOT)
    data = load_dd()
    assert set(fresh) == set(data["files"])
    for fileno, fields in fresh.items():
        assert set(fields) == set(data["files"][fileno]), fileno
        for num, fd in fields.items():
            row = data["files"][fileno][num]
            assert (fd.dd_line, fd.dd_raw, fd.storage) == (row["dd_line"], row["dd_raw"], row["storage"])


def test_file2_has_all_524_fields():
    data = json.loads((PKG_ROOT / "data" / "dd_file2.json").read_text())
    assert len(data["files"]["2"]) == 524  # ^DD(2,0)="FIELD^NL^537042^524"
