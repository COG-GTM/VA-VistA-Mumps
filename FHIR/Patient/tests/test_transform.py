import json

from conftest import FIXTURES, run


def by_url(res, url_tail):
    return [e for e in res.get("extension", []) if e["url"].endswith(url_tail)]


def test_full_record_matches_golden(full):
    golden = json.loads((FIXTURES / "patient_7187.expected.json").read_text())
    assert full == golden


def test_names(full):
    official, usual, old = full["name"]
    assert official == {"use": "official", "text": "FHIRTEST,JANE QUINN JR", "family": "FHIRTEST",
                        "given": ["JANE", "QUINN"], "suffix": ["JR"]}
    assert usual == {"use": "usual", "text": "JANIE", "given": ["JANIE"]}
    assert old["use"] == "old" and old["given"] == ["JANIE"]


def test_identifiers(full, legacy):
    sys_val = {(i.get("system"), i["value"], i.get("use")) for i in full["identifier"]}
    assert ("http://hl7.org/fhir/sid/us-ssn", "000001234", "official") in sys_val
    assert ("http://va.gov/mpi", "1008520438V882204", "official") in sys_val
    assert ("http://va.gov/mpi", "1008500000V123456", "old") in sys_val
    assert all(i.get("system") for i in full["identifier"])  # US Core requires system
    # pseudo-SSN dropped; ICN built from ICN^checksum; locally assigned -> temp
    assert not [i for i in legacy["identifier"] if i.get("system") == "http://hl7.org/fhir/sid/us-ssn"]
    icn = [i for i in legacy["identifier"] if i.get("system") == "http://va.gov/mpi"][0]
    assert icn["value"] == "1012345678V654321" and icn["use"] == "temp"


def test_core_fields(full, legacy):
    assert full["gender"] == "female" and full["birthDate"] == "1975-04-12"
    assert full["maritalStatus"]["coding"][0]["code"] == "M"
    assert legacy["maritalStatus"]["coding"][0]["code"] == "S"  # VistA N (never married) -> v3 S
    assert legacy["birthDate"] == "1975-04" and legacy["deceasedDateTime"] == "2024-03-15"
    assert full["multipleBirthBoolean"] is False and legacy["multipleBirthBoolean"] is True
    assert full["meta"]["security"][0]["code"] == "HTEST"
    assert legacy["link"] == [{"other": {"reference": "Patient/7190"}, "type": "replaced-by"}]


def test_race_ethnicity(full, legacy):
    race = by_url(full, "us-core-race")[0]["extension"]
    assert [e["valueCoding"]["code"] for e in race if e["url"] == "ombCategory"] == ["2028-9", "2106-3"]
    eth = by_url(full, "us-core-ethnicity")[0]["extension"]
    assert eth[0]["valueCoding"]["code"] == "2186-5"
    assert by_url(legacy, "us-core-race")[0]["extension"] == [
        {"url": "text", "valueString": "WHITE, NOT OF HISPANIC ORIGIN"}]


def test_gender_identity(full, legacy):
    assert by_url(full, "genderIdentity")[0]["valueCodeableConcept"]["coding"][0]["code"] == "446141000124107"
    assert by_url(legacy, "genderIdentity")[0]["valueCodeableConcept"]["coding"][0]["code"] == "407377005"


def test_addresses(full, legacy):
    postal, physical, temp, conf = full["address"]
    assert postal == {"use": "home", "type": "postal", "line": ["123 MAIN ST", "APT 4", "BLDG C"],
                      "city": "SACRAMENTO", "district": "SACRAMENTO", "state": "CA",
                      "postalCode": "95814-1234", "country": "USA"}
    assert physical["type"] == "physical" and physical["district"] == "YOLO"
    assert temp["period"] == {"start": "2024-10-01", "end": "2024-12-31"} and temp["state"] == "NV"
    assert conf["state"] == "OR"
    assert legacy["address"][0]["state"] == "ONTARIO" and legacy["address"][0]["postalCode"] == "M5H 1A1"


def test_confidential_data_is_opt_in():
    res, rec = run("7187")
    assert len(res["address"]) == 3
    assert "503-555-0199" not in json.dumps(res)
    assert "2:.1411" not in rec.trace and "2:.1315" not in rec.trace


def test_contacts(full, legacy):
    codes = [c["relationship"][0].get("coding", [{}])[0].get("code") or c["relationship"][0]["text"]
             for c in full["contact"]]
    assert codes == ["N", "N", "C", "C", "DESIGNEE", "E", "GUARD", "GUARD"]
    nok = full["contact"][0]
    assert nok["name"]["given"] == ["JOHN", "A"] and nok["relationship"][1] == {"text": "HUSBAND"}
    assert full["contact"][5]["organization"] == {"display": "ACME CORP"}
    assert full["contact"][6]["organization"] == {"reference": "Organization/500"}
    # emergency contact "same as NOK" folds into the NOK contact; "same as patient" copies address
    first = legacy["contact"][0]
    assert [r["coding"][0]["code"] for r in first["relationship"]] == ["N", "C"]
    assert first["address"]["line"] == ["10 KING ST W"]


def test_communication(full):
    assert full["communication"][0] == {
        "language": {"text": "SPANISH", "coding": [{"system": "urn:ietf:bcp:47", "code": "es", "display": "Spanish"}]},
        "preferred": True}
    assert "preferred" not in full["communication"][1]


def test_references(full):
    assert full["generalPractitioner"] == [{"reference": "Practitioner/1001"}]
    assert full["managingOrganization"] == {"reference": "Organization/500"}


def test_minimal_record_gets_unknown_gender_under_us_core():
    from vista_fhir_patient import PatientRecord, patient_to_fhir
    rec = PatientRecord.from_zwr(['^DPT(9,0)="DOE,JOHN"'])
    res = patient_to_fhir(rec)
    assert res["gender"] == "unknown" and res["name"][0]["family"] == "DOE"
