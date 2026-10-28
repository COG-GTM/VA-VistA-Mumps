# VistA PATIENT (file #2) → FHIR R4 Patient

Field-by-field mapping of FileMan file #2 (`^DPT`) to the FHIR R4 (4.0.1) Patient
resource, with a Python transform and tests. Every field is cited to the line in
`Packages/VA FileMan/Globals/DD.zwr` that defines it, and to the M routine lines its
input transform calls.

| File | What it is |
|---|---|
| [MAPPING.md](MAPPING.md) | Mapping table: VistA field → FHIR element, status, notes, DD line (M), logic routine lines |
| [mapping.csv](mapping.csv) | Same rows, untruncated, with the full DD 0-node M text |
| [vista_fhir_patient/](vista_fhir_patient) | Parser, field classification, and transform |
| [data/](data) | `dd_file2.json` (file #2 DD snapshot with line numbers) and `lookups.json` (pointer files #5, #10, #10.2, #10.3, #11, #13, #779.004, #.85) |
| [tests/](tests) | pytest suite and synthetic `^DPT` fixtures |
| [validation/](validation) | Transform output for both fixtures and the HL7 validator report (R4 + US Core 6.1.0) |

## Coverage

All 524 top-level fields of file #2 (`^DD(2,0)="FIELD^NL^537042^524"`) plus 14 fields in
the ALIAS, RACE, ETHNICITY, LANGUAGE and ICN-history subfiles:

| Status | Fields | Meaning |
|---|---|---|
| Patient | 173 | Lands on a Patient element or published Patient extension |
| Partial | 23 | Lands on Patient with a loss or caveat (note says which) |
| No FHIR equivalent | 234 | Flagged. No element in base R4 or US Core; would need a VA extension |
| Other resource | 99 | FHIR has it, but not on Patient (Encounter, Provenance, Coverage, Flag, ...) |
| Derived | 9 | Computed in VistA (FileMan type C or triggered); not exchanged |

Most of the 234 flagged fields are VA benefit, eligibility, military-service and exposure
data (service connection, means test, Agent Orange, POW, Camp Lejeune, My HealtheVet).

## Decisions worth reviewing

- **SEX (.02)** is the only sex/gender field besides SELF IDENTIFIED GENDER (.024). It maps to
  `Patient.gender`; .024 maps to `us-core-genderIdentity` using the ONC 2015 SNOMED CT codes.
- **Marital status** codes collide: VistA `S` = separated → v3 `L`; VistA `N` = never married → v3 `S`.
- **Race/ethnicity** use the CDC code in piece 3 of files #10/#10.2. Declined (0000-0) → `ASKU`,
  unknown (9999-4) → `UNK`. Pre-2003 race entries have no code and become text only.
- **Pseudo-SSNs** (ending in `P`, see `SSN^DGRPDD1`) are dropped.
- **Confidential address and phone** (.141x, .1315) are not emitted unless
  `TransformConfig(include_confidential=True)`. FHIR has no "confidential" address use.
- **Temporary address/phone** are emitted only when TEMPORARY ADDRESS ACTIVE? (.12105) = Y.
- **Identifier systems** for DFN, ICN, claim number, Medicaid, military and MPI temporary/foreign
  IDs are placeholders in `TransformConfig`. Confirm them with the receiving system.
- **Dates with times** are emitted date-only unless `TransformConfig(tz="-05:00")` is set,
  because FHIR requires a zone on dateTimes that carry a time.

## Usage

```python
from vista_fhir_patient import PatientRecord, TransformConfig, patient_to_fhir

with open("patient.zwr") as fh:          # ZWR export of ^DPT(DFN,...) (+ optional ^VA(20,...))
    record = PatientRecord.from_zwr(fh)
patient = patient_to_fhir(record, config=TransformConfig(station="500"))
```

## Tests

```bash
cd FHIR/Patient
pip install -r requirements-dev.txt
pytest -q
```

What they check:

- every cited DD line in `dd_file2.json` is that field's `^DD(file,field,0)` line in `DD.zwr`,
  and every routine citation lands on its tag (skipped where the file isn't checked out);
- `dd_file2.json` and `mapping.csv` are current with `DD.zwr` and `field_map.py`;
- every field is classified, and the set of fields marked Patient/Partial equals the set the
  transform actually reads across the fixtures (the record traces each non-empty read);
- transform output for each branch (golden file for the full fixture) and parse as an R4B Patient
  (`fhir.resources`; R4B made no changes to Patient).

Profile validation was run with the HL7 validator against R4 4.0.1 + US Core 6.1.0:
0 errors on both fixtures. Remaining warnings are extensible-binding notes (v2-0203 SS/MA/MI/NI
are outside the R4 IdentifierType subset; designee/guardian relationships have no
v2-0131 code; religion is text only) and the narrative best-practice check. See
[validation/hl7-validator-us-core-6.1.0.txt](validation/hl7-validator-us-core-6.1.0.txt).

## Regenerating

```bash
python build_data.py                 # dd_file2.json, lookups.json, MAPPING.md, mapping.csv
python tests/fixtures/build_fixtures.py
```

`build_data.py` needs `DD.zwr`, the pointer-file globals listed above, and the routines
cited in `mapping.csv` checked out.
