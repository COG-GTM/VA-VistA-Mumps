from vista_fhir_patient.fileman import fm_date, name_from_components, parse_name, postal_code
from vista_fhir_patient.zwr import canonical_number, decode_value, parse_line, piece


def test_parse_line_quoted_and_numeric_subscripts():
    n = parse_line('^DD(2,".01",0)="NAME^RFXa^^0;1^K:$L(X)>30 X I $D(X) S X=""A"""', 7)
    assert n.global_name == "DD" and n.subscripts == ("2", ".01", "0") and n.line_no == 7
    assert n.value.endswith('S X="A"')
    assert parse_line('^DD(2,0,"DT")=3191125').value == "3191125"
    assert parse_line("OSEHRA ZGO Export: PATIENT") is None


def test_canonical_numbers_match_m():
    assert [canonical_number(x) for x in ("0.85", "10.20", "2.0991", "537025")] == [".85", "10.2", "2.0991", "537025"]


def test_decode_char_concatenation():
    assert decode_value('"a"_$C(9)_"b"') == "a\tb"


def test_piece():
    assert piece("A^B^^D", 2) == "B" and piece("A^B", 5) == ""


def test_fm_date_precision_and_time():
    assert fm_date("2750412") == "1975-04-12"
    assert fm_date("2750400") == "1975-04"
    assert fm_date("2750000") == "1975"
    assert fm_date("3241001.1430") == "2024-10-01"
    assert fm_date("3241001.1430", tz="-05:00") == "2024-10-01T14:30:00-05:00"
    assert fm_date("") is None and fm_date("JUNK") is None


def test_parse_name_with_suffix():
    assert parse_name("FHIRTEST,JANE QUINN JR") == {
        "text": "FHIRTEST,JANE QUINN JR", "family": "FHIRTEST", "given": ["JANE", "QUINN"], "suffix": ["JR"]}
    assert parse_name("CHER,") == {"text": "CHER,", "family": "CHER"}


def test_name_components():
    assert name_from_components("SMITH^JOHN^A B^DR^III^MD", "SMITH,JOHN A B III") == {
        "text": "SMITH,JOHN A B III", "family": "SMITH", "given": ["JOHN", "A", "B"],
        "prefix": ["DR"], "suffix": ["III", "MD"]}


def test_postal_code_prefers_zip4():
    assert postal_code("95814", "958141234") == "95814-1234"
    assert postal_code("95814", "") == "95814"
    assert postal_code("", "") is None
