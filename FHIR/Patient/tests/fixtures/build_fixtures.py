"""Write the synthetic ^DPT fixtures used by the tests (no real patient data).

Values are given per FileMan field number; node/piece placement comes from
data/dd_file2.json, so the fixtures exercise the same DD storage the transform reads.
Run: python tests/fixtures/build_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DD = json.loads((HERE.parent.parent / "data" / "dd_file2.json").read_text())["files"]

# State IENs from file #5: 6=CA, 32=NV, 41=OR. County IENs are within each state.
# Country IENs from file #779.004: 1=USA, 39=CAN.
FULL = {
    ".01": "FHIRTEST,JANE QUINN JR", "1.01": "501", ".02": "F", ".024": "F", ".03": "2750412",
    ".05": "2", ".08": "3", ".09": "000001234", ".092": "SACRAMENTO", ".093": "6", ".0931": "1",
    ".111": "123 MAIN ST", ".112": "APT 4", ".113": "BLDG C", ".114": "SACRAMENTO", ".115": "6",
    ".116": "95814", ".1112": "958141234", ".117": "38", ".1173": "1",
    ".1151": "456 OAK AVE", ".1152": "UNIT 2", ".1153": "REAR", ".1154": "DAVIS", ".1155": "6",
    ".1156": "956160000", ".1157": "59", ".11573": "1",
    ".12105": "Y", ".1211": "789 PINE RD", ".1212": "STE 100", ".1213": "FLOOR 2", ".1214": "RENO",
    ".1215": "32", ".1216": "89501", ".12112": "895011111", ".12111": "12", ".1223": "1",
    ".1217": "3241001", ".1218": "3241231", ".1219": "775-555-0100",
    ".14105": "Y", ".1411": "PO BOX 99", ".1412": "C/O SMITH", ".1413": "DEPT 7", ".1414": "PORTLAND",
    ".1415": "41", ".1416": "97201", ".14111": "7", ".14116": "1", ".1417": "3240101",
    ".1418": "3251231", ".1315": "503-555-0199",
    ".131": "916-555-0101", ".132": "916-555-0102", ".133": "jane.fhirtest@example.org",
    ".134": "916-555-0103", ".135": "916-555-0104",
    ".211": "FHIRTEST,JOHN A", ".212": "HUSBAND", ".2125": "N", ".213": "123 MAIN ST", ".214": "APT 4",
    ".215": "BLDG C", ".216": "SACRAMENTO", ".217": "6", ".218": "95814", ".2207": "958141234",
    ".219": "916-555-0201", ".21011": "916-555-0202", "1.02": "502",
    ".2191": "FHIRTEST,MARY", ".2192": "MOTHER", ".21925": "N", ".2193": "1 ELM ST", ".2194": "UNIT 1",
    ".2195": "SIDE", ".2196": "FRESNO", ".2197": "6", ".2198": "93701", ".2203": "937010001",
    ".2199": "559-555-0301", ".211011": "559-555-0302", "1.03": "503",
    ".3305": "N", ".331": "DOE,RICHARD", ".332": "FRIEND", ".333": "2 ELM ST", ".334": "#2",
    ".335": "BACK", ".336": "FRESNO", ".337": "6", ".338": "93702", ".2201": "937020002",
    ".339": "559-555-0401", ".33011": "559-555-0402", "1.07": "504",
    ".3311": "ROE,SALLY", ".3312": "SISTER", ".3313": "3 ELM ST", ".3314": "#3", ".3315": "FRONT",
    ".3316": "FRESNO", ".3317": "6", ".3318": "93703", ".2204": "937030003", ".3319": "559-555-0501",
    ".331011": "559-555-0502", "1.08": "505",
    ".341": "FHIRTEST,PAUL", ".342": "SON", ".3405": "N", ".343": "4 ELM ST", ".344": "#4",
    ".345": "TOP", ".346": "FRESNO", ".347": "6", ".348": "93704", ".2202": "937040004",
    ".349": "559-555-0601", ".34011": "559-555-0602", "1.09": "506",
    ".3111": "ACME CORP", ".3113": "5 INDUSTRIAL WAY", ".3114": "BLDG 9", ".3115": "DOCK 3",
    ".3116": "SACRAMENTO", ".3117": "6", ".3118": "95815", ".2205": "958150005", ".3119": "916-555-0700",
    ".2912": "GUARD,VERA", ".2913": "BROTHER", ".2914": "6 ELM ST", ".2915": "#6", ".2916": "FRESNO",
    ".2917": "6", ".2918": "93706", ".29013": "937060006", ".2919": "559-555-0800", ".2911": "500",
    ".2922": "GUARD,CARL", ".2923": "ATTORNEY", ".2924": "7 ELM ST", ".2925": "#7", ".2926": "FRESNO",
    ".2927": "6", ".2928": "93707", ".290012": "937070007", ".2929": "559-555-0900",
    ".2921": "FRESNO COUNTY COURT",
    ".2403": "SMITH,ANNE", ".2405": "JANIE", ".383": "CA1234567", ".313": "C12345678",
    ".328": "RA11111111", ".3294": "RA22222222", ".3299": "RA33333333", ".6": "1",
    "404.01": "1001", "991.01": "1008520438", "991.02": "882204", "991.1": "1008520438V882204",
    "991.04": "N", "991.03": "500", "991.08": "TMP123", "991.09": "FRN456", "994": "N",
}
FULL_MULTIPLES = {
    ".01": {"1": "FHIRTEST,JANIE^000001234^507"},          # ALIAS: name^alias SSN^components
    ".02": {"8": "8^1", "13": "13^1"},                      # RACE: ASIAN, WHITE (DINUM)
    ".06": {"2": "2^1"},                                    # ETHNICITY: NOT HISPANIC OR LATINO
    ".207": {"1": "3200101^ENGLISH", "2": "3240601^SPANISH"},
    "MPIFICNHIS": {"1": "1008520438V882204", "2": "1008500000V123456"},
    "MPIFHIS": {"1": "1008500000^123456^500^3150101"},
}
NAME_COMPONENTS = {
    "501": "FHIRTEST^JANE^QUINN^^JR^", "502": "FHIRTEST^JOHN^A^^^", "503": "FHIRTEST^MARY^^^^",
    "504": "DOE^RICHARD^^^^", "505": "ROE^SALLY^^^^", "506": "FHIRTEST^PAUL^^^^",
    "507": "FHIRTEST^JANIE^^^^",
}

# Exercises the other branches: legacy race, pseudo-SSN, imprecise DOB, death, merge,
# foreign addresses, "same as" flags, ICN without FULL ICN, locally assigned ICN.
LEGACY = {
    ".01": "LEGACY,PAT", ".02": "M", ".024": "TM", ".03": "2750400", ".05": "6", ".06": "3",
    ".082": "7190", ".09": "000005678P", ".0931": "39", ".0932": "ONTARIO",
    ".111": "10 KING ST W", ".114": "TORONTO", ".1171": "ONTARIO", ".1172": "M5H 1A1", ".1173": "39",
    ".1151": "20 BAY ST", ".1154": "TORONTO", ".11571": "ONTARIO", ".11572": "M5J 2N8", ".11573": "39",
    ".12105": "Y", ".1211": "30 FRONT ST", ".1214": "OTTAWA", ".1221": "ONTARIO", ".1222": "K1A 0A6",
    ".1223": "39",
    ".14105": "Y", ".1411": "40 SPARKS ST", ".1414": "OTTAWA", ".14114": "ONTARIO", ".14115": "K1P 5A9",
    ".14116": "39",
    ".211": "LEGACY,KIN", ".2125": "Y", ".2191": "LEGACY,KIN TWO", ".21925": "Y", ".3305": "Y",
    ".341": "LEGACY,DES", ".3405": "Y", ".351": "3240315",
    "991.01": "1012345678", "991.02": "654321", "991.04": "Y", "994": "Y",
}


def to_zwr(dfn: str, values: dict, multiples: dict | None = None, comps: dict | None = None) -> str:
    nodes: dict[str, list[str]] = {}
    for num, value in values.items():
        fd = DD["2"][num]
        pieces = nodes.setdefault(fd["node"], [])
        p = int(fd["piece"])
        pieces.extend([""] * (p - len(pieces)))
        pieces[p - 1] = value

    def sub(s: str) -> str:
        try:
            float(s)
            return s
        except ValueError:
            return f'"{s}"'

    lines = ["Synthetic fixture for FHIR/Patient tests", "ZWR"]
    for node in sorted(nodes, key=lambda n: (not n.replace(".", "").isdigit(), n)):
        val = "^".join(nodes[node]).replace('"', '""')
        lines.append(f'^DPT({dfn},{sub(node)})="{val}"')
    for node, entries in (multiples or {}).items():
        for ien, val in entries.items():
            lines.append(f'^DPT({dfn},{sub(node)},{ien},0)="{val}"')
    for ien, val in (comps or {}).items():
        lines.append(f'^VA(20,{ien},1)="{val}"')
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    (HERE / "patient_7187.zwr").write_text(to_zwr("7187", FULL, FULL_MULTIPLES, NAME_COMPONENTS))
    (HERE / "patient_7188.zwr").write_text(to_zwr("7188", LEGACY))
    print("wrote patient_7187.zwr, patient_7188.zwr")
