"""Every field is classified, and the table agrees with what the transform actually reads."""

import csv

from conftest import PKG_ROOT, run

from vista_fhir_patient.field_map import EXPLICIT, GROUPS, NONE, PARTIAL, PATIENT, STATUSES, classify
from vista_fhir_patient.record import load_dd


def all_fields():
    for fileno, fields in load_dd()["files"].items():
        for num, fd in fields.items():
            yield f"{fileno}:{num}", fd


def test_every_field_classified():
    for key, fd in all_fields():
        m = classify(fd)
        assert m.status in STATUSES, key
        if m.status in (PATIENT, PARTIAL):
            assert m.fhir.startswith("Patient."), key
        if m.status == NONE:
            assert m.note, key


def test_explicit_keys_exist_in_dd():
    keys = {k for k, _ in all_fields()}
    assert not (set(EXPLICIT) | set(GROUPS)) - keys
    assert not set(EXPLICIT) & set(GROUPS)


def test_mapped_fields_equal_fields_the_transform_consumes():
    claimed = {k for k, fd in all_fields() if classify(fd).status in (PATIENT, PARTIAL)}
    traced = set()
    for dfn in ("7187", "7188"):
        _, rec = run(dfn, include_confidential=True)
        traced |= rec.trace
    assert claimed - traced == set(), "mapped in table but never read by transform"
    assert traced - claimed == set(), "read by transform but not mapped in table"


def test_generated_csv_is_current():
    with open(PKG_ROOT / "mapping.csv", newline="", encoding="utf-8") as fh:
        rows = {f"{r['file']}:{r['field']}": r for r in csv.DictReader(fh)}
    for key, fd in all_fields():
        m = classify(fd)
        assert rows[key]["status"] == m.status and rows[key]["fhir_element"] == m.fhir, key
        assert int(rows[key]["dd_line"]) == fd["dd_line"]
        assert rows[key]["no_fhir_equivalent"] == ("YES" if m.status == NONE else "")
