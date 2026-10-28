"""Classification of every file #2 field (and mapped subfile fields) against FHIR R4.

Status values:

* ``Patient``  - lands on a FHIR R4 Patient element or a published Patient extension.
* ``Partial``  - lands on Patient with a loss or caveat (see note).
* ``Other resource`` - FHIR R4 has the concept, but on a different resource.
* ``No FHIR equivalent`` - no element in base FHIR R4 or US Core; needs a VA-defined extension.
* ``Derived`` - computed/triggered in VistA from other fields; not exchanged.

Keys are ``"<file>:<field>"`` using FileMan canonical numbers (e.g. ``"2:.01"``).
Every field in ``data/dd_file2.json`` must resolve here; ``tests/test_field_map.py``
fails on any gap.
"""

from __future__ import annotations

from dataclasses import dataclass

PATIENT = "Patient"
PARTIAL = "Partial"
OTHER = "Other resource"
NONE = "No FHIR equivalent"
DERIVED = "Derived"
STATUSES = (PATIENT, PARTIAL, OTHER, NONE, DERIVED)

US_CORE = "http://hl7.org/fhir/us/core/StructureDefinition"
EXT = "http://hl7.org/fhir/StructureDefinition"


@dataclass(frozen=True)
class Mapping:
    status: str
    fhir: str
    note: str = ""


def _m(status: str, fhir: str, note: str = "") -> Mapping:
    return Mapping(status, fhir, note)


def _block(fields: dict[str, str], status: str, prefix: str, note: str = "") -> dict[str, Mapping]:
    return {f"2:{num}": _m(status, f"{prefix}{suffix}", note) for num, suffix in fields.items()}


_ADDR = {"line1": ".line[0]", "line2": ".line[1]", "line3": ".line[2]", "city": ".city",
         "state": ".state", "zip": ".postalCode", "zip4": ".postalCode", "county": ".district",
         "province": ".state", "postal": ".postalCode", "country": ".country"}


def _addr(prefix: str, nums: dict[str, str], status: str = PATIENT, note: str = "") -> dict[str, Mapping]:
    return {f"2:{num}": _m(status, f"{prefix}{_ADDR[part]}", note) for part, num in nums.items()}


def _contact(prefix: str, nums: dict[str, str], note: str) -> dict[str, Mapping]:
    parts = {"name": ".name.text", "rel": ".relationship.text", "line1": ".address.line[0]",
             "line2": ".address.line[1]", "line3": ".address.line[2]", "city": ".address.city",
             "state": ".address.state", "zip": ".address.postalCode", "zip4": ".address.postalCode",
             "phone": ".telecom[use=home]", "work": ".telecom[use=work]",
             "same": ".address (copied from patient mailing address when Y)",
             "comp": ".name.family/given/suffix (NAME COMPONENTS file #20)",
             "org": ".organization.display", "orgref": ".organization (Reference Organization, file #4)"}
    return {f"2:{num}": _m(PATIENT, f"{prefix}{parts[p]}", note) for p, num in nums.items()}


EXPLICIT: dict[str, Mapping] = {
    "2:.01": _m(PATIENT, "Patient.name[use=official].family/given/suffix/text",
                "Stored as LAST,FIRST MIDDLE SUFFIX; parts come from NAME COMPONENTS (#1.01) when present."),
    "2:1.01": _m(PATIENT, "Patient.name[use=official].family/given/prefix/suffix",
                 "Pointer to NAME COMPONENTS file #20 (^VA(20,ien,1) family^given^middle^prefix^suffix)."),
    "2:.02": _m(PATIENT, "Patient.gender", "M->male, F->female. VistA SEX is birth sex; no separate administrative gender field exists."),
    "2:.024": _m(PATIENT, f"Patient.extension[{US_CORE}/us-core-genderIdentity]",
                 "M/F/TM/TF to SNOMED CT (ONC 2015 gender identity value set); O->OTH, N->ASKU (v3-NullFlavor)."),
    "2:.03": _m(PATIENT, "Patient.birthDate", "FileMan date YYYMMDD (YYY=year-1700); imprecise 00 month/day become YYYY or YYYY-MM."),
    "2:.05": _m(PATIENT, "Patient.maritalStatus",
                "File #11 code to v3-MaritalStatus: D->D, M->M, W->W, S(separated)->L, N(never married)->S, U->UNK. Note S means different things in each system."),
    "2:.06": _m(PARTIAL, f"Patient.extension[{US_CORE}/us-core-race].text",
                "Historical single-race field; used only when RACE INFORMATION (#2) is empty. Pre-2003 file #10 entries carry no CDC code, so text only."),
    "2:.08": _m(PARTIAL, f"Patient.extension[{EXT}/patient-religion].text",
                "File #13 CODE is a VA code, not v3-ReligiousAffiliation; emitted as text only."),
    "2:.082": _m(PATIENT, "Patient.link[type=replaced-by].other", "Reference to the surviving Patient record after a merge."),
    "2:.09": _m(PATIENT, "Patient.identifier[type=SS, system=http://hl7.org/fhir/sid/us-ssn]",
                "Pseudo-SSNs (value ending in P, see SSN^DGRPDD1) are not emitted."),
    "2:.092": _m(PATIENT, f"Patient.extension[{EXT}/patient-birthPlace].valueAddress.city"),
    "2:.093": _m(PATIENT, f"Patient.extension[{EXT}/patient-birthPlace].valueAddress.state", "File #5 abbreviation."),
    "2:.0931": _m(PATIENT, f"Patient.extension[{EXT}/patient-birthPlace].valueAddress.country", "File #779.004 ISO 3166 alpha-3 code."),
    "2:.0932": _m(PATIENT, f"Patient.extension[{EXT}/patient-birthPlace].valueAddress.state", "Foreign province; used when no US state."),
    "2:.1219": _m(PATIENT, "Patient.telecom[system=phone,use=temp]", "Period from TEMPORARY ADDRESS START/END DATE; emitted only when TEMPORARY ADDRESS ACTIVE?=Y."),
    "2:.131": _m(PATIENT, "Patient.telecom[system=phone,use=home]"),
    "2:.132": _m(PATIENT, "Patient.telecom[system=phone,use=work]"),
    "2:.133": _m(PATIENT, "Patient.telecom[system=email]"),
    "2:.134": _m(PATIENT, "Patient.telecom[system=phone,use=mobile]"),
    "2:.135": _m(PATIENT, "Patient.telecom[system=pager]"),
    "2:.1315": _m(PARTIAL, "Patient.telecom[system=phone,use=temp]",
                  "FHIR has no 'confidential' contact-point use; emitted only with include_confidential=True, with the confidential address period."),
    "2:.12105": _m(PATIENT, "Patient.address[use=temp] (gate)", "Temporary address/phone are emitted only when Y."),
    "2:.14105": _m(PARTIAL, "Patient.address[use=temp] (gate)", "Confidential address emitted only when Y and include_confidential=True."),
    "2:.1217": _m(PATIENT, "Patient.address[use=temp].period.start"),
    "2:.1218": _m(PATIENT, "Patient.address[use=temp].period.end"),
    "2:.1417": _m(PARTIAL, "Patient.address[use=temp].period.start", "Confidential address (opt-in)."),
    "2:.1418": _m(PARTIAL, "Patient.address[use=temp].period.end", "Confidential address (opt-in)."),
    "2:.2403": _m(PATIENT, f"Patient.extension[{EXT}/patient-mothersMaidenName].valueString"),
    "2:.2405": _m(PARTIAL, "Patient.name[use=usual].text/given", "Free text (may be a rank plus last name); US Core us-core-6 needs given or family, so the whole value also goes in given[0]."),
    "2:.351": _m(PATIENT, "Patient.deceasedDateTime"),
    "2:.383": _m(PATIENT, "Patient.identifier[type=MA]", "v2-0203 MA = Patient Medicaid number. Issuing state is not stored; system is configurable."),
    "2:.313": _m(PARTIAL, "Patient.identifier[type.text=VA claim number]", "No standard identifier type or system for a VA claim number; system is configurable."),
    "2:.328": _m(PARTIAL, "Patient.identifier[type=MI]", "v2-0203 MI = military ID number; issuing branch is not encoded."),
    "2:.3294": _m(PARTIAL, "Patient.identifier[type=MI]", "Next-to-last service episode."),
    "2:.3299": _m(PARTIAL, "Patient.identifier[type=MI]", "Second-to-last-but-one service episode."),
    "2:.6": _m(PATIENT, "Patient.meta.security[code=HTEST]", "v3-ActReason HTEST (test health data) when 1."),
    "2:1": _m(PATIENT, "Patient.name[use=old]", "ALIAS multiple (subfile #2.01)."),
    "2.01:.01": _m(PATIENT, "Patient.name[use=old].family/given/suffix/text"),
    "2.01:100.03": _m(PATIENT, "Patient.name[use=old] parts", "Pointer to NAME COMPONENTS file #20."),
    "2.01:1": _m(NONE, "", "ALIAS SSN: FHIR identifiers cannot be scoped to one name."),
    "2:2": _m(PATIENT, f"Patient.extension[{US_CORE}/us-core-race]", "RACE INFORMATION multiple (subfile #2.02)."),
    "2.02:.01": _m(PATIENT, f"Patient.extension[{US_CORE}/us-core-race].ombCategory/text",
                   "File #10 piece 3 is the CDC race code; 0000-0 (declined)->ASKU, 9999-4 (unknown)->UNK."),
    "2.02:.02": _m(NONE, "", "METHOD OF COLLECTION (self-identified/observer): us-core-race has no slot."),
    "2:6": _m(PATIENT, f"Patient.extension[{US_CORE}/us-core-ethnicity]", "ETHNICITY INFORMATION multiple (subfile #2.06)."),
    "2.06:.01": _m(PATIENT, f"Patient.extension[{US_CORE}/us-core-ethnicity].ombCategory/text",
                   "File #10.2 piece 3 is the CDC ethnicity code; 0000-0->ASKU, 9999-4->UNK."),
    "2.06:.02": _m(NONE, "", "METHOD OF COLLECTION: us-core-ethnicity has no slot."),
    "2:7": _m(PATIENT, "Patient.communication", "LANGUAGE DATE/TIME multiple (subfile #2.07)."),
    "2.07:.01": _m(PATIENT, "Patient.communication.preferred", "Most recent LANGUAGE DATE/TIME entry is marked preferred."),
    "2.07:.02": _m(PATIENT, "Patient.communication.language",
                   "Stored as the LANGUAGE file #.85 name (see INPXF207^DGRPE); coded with its two-letter ISO 639-1 code (urn:ietf:bcp:47). DECLINED TO ANSWER is dropped."),
    "2:404.01": _m(PATIENT, "Patient.generalPractitioner", "Reference Practitioner (NEW PERSON file #200 IEN). Field is marked * (superseded by PCMM) in the DD."),
    "2:991.01": _m(PATIENT, "Patient.identifier[type=NI] (ICN)", "Used with ICN CHECKSUM when FULL ICN is empty."),
    "2:991.02": _m(PATIENT, "Patient.identifier[type=NI] (ICN checksum suffix)"),
    "2:991.1": _m(PATIENT, "Patient.identifier[type=NI] (ICN)", "Integration Control Number from the VA Master Patient Index; system is configurable."),
    "2:991.04": _m(PATIENT, "Patient.identifier[type=NI].use", "Y (locally assigned ICN) -> use=temp."),
    "2:991.03": _m(PATIENT, "Patient.managingOrganization", "Coordinating Master of Record; Reference Organization (INSTITUTION file #4 IEN)."),
    "2:991.08": _m(PARTIAL, "Patient.identifier[use=temp]", "Issuer of TEMPORARY ID NUMBER is not recorded; system configurable."),
    "2:991.09": _m(PARTIAL, "Patient.identifier[use=secondary]", "Issuing country/agency of FOREIGN ID NUMBER is not recorded."),
    "2:991.91": _m(PATIENT, "Patient.identifier[type=NI,use=old]", "FULL ICN HISTORY multiple (subfile #2.0991)."),
    "2.0991:.01": _m(PATIENT, "Patient.identifier[type=NI,use=old].value"),
    "2:992": _m(PATIENT, "Patient.identifier[type=NI,use=old]", "ICN HISTORY multiple (subfile #2.0992)."),
    "2.0992:.01": _m(PATIENT, "Patient.identifier[type=NI,use=old].value"),
    "2.0992:1": _m(PATIENT, "Patient.identifier[type=NI,use=old].value (checksum suffix)"),
    "2.0992:3": _m(PATIENT, "Patient.identifier[type=NI,use=old].period.end"),
    "2.0992:2": _m(OTHER, "Provenance", "CMOR at the time of the ICN change."),
    "2:994": _m(PATIENT, "Patient.multipleBirthBoolean"),
    "2:.3305": _m(PATIENT, "Patient.contact[relationship=C].address", "Y copies the primary next-of-kin address/phone into the emergency contact."),
}

EXPLICIT.update(_addr("Patient.address[use=home,type=postal]", {
    "line1": ".111", "line2": ".112", "line3": ".113", "city": ".114", "state": ".115", "zip": ".116",
    "zip4": ".1112", "county": ".117", "province": ".1171", "postal": ".1172", "country": ".1173"}))
EXPLICIT.update(_addr("Patient.address[use=home,type=physical]", {
    "line1": ".1151", "line2": ".1152", "line3": ".1153", "city": ".1154", "state": ".1155",
    "zip4": ".1156", "county": ".1157", "province": ".11571", "postal": ".11572", "country": ".11573"}))
EXPLICIT.update(_addr("Patient.address[use=temp]", {
    "line1": ".1211", "line2": ".1212", "line3": ".1213", "city": ".1214", "state": ".1215", "zip": ".1216",
    "zip4": ".12112", "county": ".12111", "province": ".1221", "postal": ".1222", "country": ".1223"}))
EXPLICIT.update(_addr("Patient.address[use=temp]", {
    "line1": ".1411", "line2": ".1412", "line3": ".1413", "city": ".1414", "state": ".1415", "zip": ".1416",
    "county": ".14111", "province": ".14114", "postal": ".14115", "country": ".14116"}, PARTIAL,
    "Confidential address: FHIR has no confidential address use; emitted only with include_confidential=True."))

EXPLICIT.update(_contact("Patient.contact[relationship=N]", {
    "name": ".211", "rel": ".212", "same": ".2125", "line1": ".213", "line2": ".214", "line3": ".215",
    "city": ".216", "state": ".217", "zip": ".218", "zip4": ".2207", "phone": ".219", "work": ".21011",
    "comp": "1.02"}, "Primary next of kin (v2-0131 N)."))
EXPLICIT.update(_contact("Patient.contact[relationship=N]", {
    "name": ".2191", "rel": ".2192", "same": ".21925", "line1": ".2193", "line2": ".2194", "line3": ".2195",
    "city": ".2196", "state": ".2197", "zip": ".2198", "zip4": ".2203", "phone": ".2199", "work": ".211011",
    "comp": "1.03"}, "Secondary next of kin (v2-0131 N)."))
EXPLICIT.update(_contact("Patient.contact[relationship=C]", {
    "name": ".331", "rel": ".332", "line1": ".333", "line2": ".334", "line3": ".335", "city": ".336",
    "state": ".337", "zip": ".338", "zip4": ".2201", "phone": ".339", "work": ".33011", "comp": "1.07"},
    "Primary emergency contact (v2-0131 C)."))
EXPLICIT.update(_contact("Patient.contact[relationship=C]", {
    "name": ".3311", "rel": ".3312", "line1": ".3313", "line2": ".3314", "line3": ".3315", "city": ".3316",
    "state": ".3317", "zip": ".3318", "zip4": ".2204", "phone": ".3319", "work": ".331011", "comp": "1.08"},
    "Secondary emergency contact (v2-0131 C)."))
EXPLICIT.update(_contact("Patient.contact[relationship.text=DESIGNEE]", {
    "name": ".341", "rel": ".342", "same": ".3405", "line1": ".343", "line2": ".344", "line3": ".345",
    "city": ".346", "state": ".347", "zip": ".348", "zip4": ".2202", "phone": ".349", "work": ".34011",
    "comp": "1.09"}, "Designee to receive personal effects; v2-0131 has no designee code, so relationship is text."))
EXPLICIT.update(_contact("Patient.contact[relationship=E]", {
    "org": ".3111", "line1": ".3113", "line2": ".3114", "line3": ".3115", "city": ".3116", "state": ".3117",
    "zip": ".3118", "zip4": ".2205", "work": ".3119"}, "Patient's employer (v2-0131 E)."))
EXPLICIT.update(_contact("Patient.contact[relationship=GUARD]", {
    "name": ".2912", "rel": ".2913", "line1": ".2914", "line2": ".2915", "city": ".2916", "state": ".2917",
    "zip": ".2918", "zip4": ".29013", "phone": ".2919", "orgref": ".2911"},
    "VA-appointed guardian (v3-RoleCode GUARD)."))
EXPLICIT.update(_contact("Patient.contact[relationship=GUARD]", {
    "name": ".2922", "rel": ".2923", "line1": ".2924", "line2": ".2925", "city": ".2926", "state": ".2927",
    "zip": ".2928", "zip4": ".290012", "phone": ".2929", "org": ".2921"},
    "Civil (court-appointed) guardian (v3-RoleCode GUARD)."))


def _group(nums: str, status: str, fhir: str, note: str) -> dict[str, Mapping]:
    return {f"2:{n}": _m(status, fhir, note) for n in nums.split()}


GROUPS: dict[str, Mapping] = {}
GROUPS.update(_group(".1 .101 .102 .103 .104 .1041 .105 .106 .107 .108 1000", OTHER, "Encounter",
                     "Current inpatient location, movement, provider, or disposition."))
GROUPS.update(_group("1010.15 1010.151 1010.152 1010.153 1010.154", OTHER, "Encounter",
                     "Summary of prior VA care (date/location)."))
GROUPS.update(_group(".109", OTHER, "Consent", "Facility directory opt-out."))
GROUPS.update(_group(
    ".096 .097 .098 .118 .119 .12 .122 .1158 .11581 .11582 .12113 .12114 .1311 .13111 .1312 .1313 .1314 "
    ".1317 .1321 .1322 .1323 .136 .137 .138 .139 .14112 .14113 .21012 .211012 .33012 .33112 .3412 .352 "
    ".354 .355 993", OTHER, "Provenance", "Who/when/where a value was entered or changed."))
GROUPS.update(_group(".181 401.3 401.4 1100.01 1100.02 1100.03 1100.04 1100.05 1100.09", OTHER, "Flag",
                     "Administrative alert on the patient record."))
GROUPS.update(_group(".2401 .2402 1.04 1.05 .3601", OTHER, "RelatedPerson",
                     "Parent or sponsor recorded as a name only; FHIR models these as RelatedPerson."))
GROUPS.update(_group(".07 .31115 .31116", OTHER, "Observation",
                     "Occupation/employment status (ODH / US Core occupation profiles)."))
GROUPS.update(_group("57.1 57.2", OTHER, "Observation", "Legacy vital sign (field marked *)."))
GROUPS.update(_group("57.4 .3721 .3731 .396 .398", OTHER, "Condition", "Diagnosis or condition list."))
GROUPS.update(_group(".397 .37", OTHER, "Procedure", "Procedure or treatment dates."))
GROUPS.update(_group("53", OTHER, "AllergyIntolerance", "Legacy allergy flag (field marked *)."))
GROUPS.update(_group(".3121 .3192 .381 25.01 25.02", OTHER, "Coverage", "Insurance / Medicaid / health benefit plan."))
GROUPS.update(_group("1900 1010.1511 1010.1512 1010.1513 1010.1514 1010.1515 1010.159 1010.161 1010.162 "
                     "1010.163 1010.164", OTHER, "Appointment", "Appointment or appointment request."))
GROUPS.update(_group("3", OTHER, "EpisodeOfCare", "Clinic enrollment."))
GROUPS.update(_group("404.02", OTHER, "CareTeam", "Primary care team (PCMM)."))
GROUPS.update(_group(".081 .083", NONE, "", "Duplicate-record workflow status (MPI/duplicate resolution)."))
GROUPS.update(_group(".091", NONE, "", "Free-text registration remark; Patient has no note/annotation element."))
GROUPS.update(_group(".14", NONE, "", "Current means test status (VA copay eligibility)."))
GROUPS.update(_group(".141", NONE, "", "Confidential address category (which mail types use it); Address has no such element."))
GROUPS.update(_group(".368 .369", NONE, "", "VA dental eligibility questions."))
GROUPS.update(_group(".363 .364", DERIVED, "", "Display IDs triggered from SSN; not exchanged."))

# Remaining fields, by ^DPT storage node: VA-specific data with no FHIR R4 / US Core element.
NONE_BY_NODE: dict[str, str] = {
    "0": "VA registration bookkeeping.",
    "SSN": "Pseudo-SSN reason / SSA verification status; no identifier sub-element for this.",
    ".11": "USPS CASS certification / bad-address flag; FHIR Address has no deliverability status.",
    ".115": "USPS CASS certification status.",
    ".121": "USPS CASS certification status.",
    ".13": "Email-on-file indicator.",
    ".14": "Means test status (VA copay eligibility).",
    ".141": "Confidential address category / CASS status.",
    ".15": "VA ineligible / missing-person status.",
    ".16": "VA ineligible / missing-person status.",
    "INE": "VA ineligible / missing-person TWX data.",
    ".17": "VA fee-basis hospital ID.",
    ".22": "Spouse's employer data; spouse is not a Patient.contact in VistA.",
    ".25": "Spouse's employer data; spouse is not a Patient.contact in VistA.",
    ".29": "VA incompetency rating.",
    ".291": "Civil incompetency rating.",
    ".3": "VA service-connected disability and monetary benefits.",
    ".31": "VA claim folder location.",
    ".311": "Federal agency employment flag.",
    ".32": "Military service episode data.",
    ".321": "Military exposure (Vietnam, Agent Orange, radiation, SHAD).",
    ".322": "Military conflict service (Gulf War, Lebanon, Grenada, Panama, Somalia, Yugoslavia).",
    ".3215": "OEF/OIF service.",
    ".3216": "Military service episode.",
    ".3217": "Camp Lejeune exposure.",
    ".32171": "Camp Lejeune exposure.",
    ".3291": "Military service component.",
    ".35": "Death-notification source/document metadata.",
    ".36": "VA eligibility code / disability retirement.",
    ".361": "VA eligibility verification.",
    ".362": "VA income/benefit amounts.",
    ".38": "Medicaid inquiry date.",
    ".385": "VA pension award / dental class.",
    ".39": "Catastrophically disabled determination.",
    ".399": "Catastrophically disabled history.",
    ".401": "Catastrophically disabled descriptors.",
    ".52": "POW / combat service.",
    ".53": "Purple Heart status.",
    ".54": "Medal of Honor status.",
    "PH": "Purple Heart history.",
    "NAME": "Name components for a value FHIR stores as a plain string.",
    "E": "VA patient eligibilities.",
    "ENR": "VA health care enrollment.",
    "DENT": "VA dental classification.",
    "NHC": "Community Nursing Home status.",
    "LR": "Internal pointer to LAB DATA file #63.",
    "LRT": "Internal pointer to REFERRAL PATIENT file #67.",
    "TYPE": "VA TYPE OF PATIENT (veteran, non-veteran, ...).",
    "MPI": "VA MPI subscription/CMOR scoring internals.",
    "MPICMOR": "VA MPI CMOR history.",
    "1010.15": "VA 1010EZ application data.",
    "VET": "Veteran status (Y/N).",
    "ARCH": "VistA archiving.",
    "INS": "Insurance-check run date.",
    "3000": "VA Transitional Services flag.",
    "ODS": "Operation Desert Shield data.",
    "537025": "Network Health Exchange site synonyms.",
    "1": "My HealtheVet socialization.",
    "2": "My HealtheVet registration/authentication status.",
    "2.1": "My HealtheVet declined text.",
    "2.2": "My HealtheVet declined text.",
    "2.3": "My HealtheVet declined text.",
    "3": "My HealtheVet actions.",
    "4": "My HealtheVet actions.",
}


def classify(field: dict) -> Mapping:
    key = f"{field['file']}:{field['number']}"
    if key in EXPLICIT:
        return EXPLICIT[key]
    if key in GROUPS:
        return GROUPS[key]
    if field["type_spec"].startswith("C") or field["storage"].strip() in ("", ";"):
        return _m(DERIVED, "", "Computed field (FileMan type C); recomputed from stored data.")
    node = field["node"]
    if field["file"] == "2" and node in NONE_BY_NODE:
        return _m(NONE, "", NONE_BY_NODE[node])
    raise KeyError(f"unclassified field {key} {field['name']} (node {node!r})")
