"""Transform one VistA PATIENT (file #2) entry into a FHIR R4 Patient resource (as a dict)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .field_map import EXT, US_CORE
from .fileman import fm_date, name_from_components, parse_name, postal_code
from .lookups import Lookups
from .record import PatientRecord

V2_0203 = "http://terminology.hl7.org/CodeSystem/v2-0203"
V2_0131 = "http://terminology.hl7.org/CodeSystem/v2-0131"
V3_MARITAL = "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus"
V3_NULL = "http://terminology.hl7.org/CodeSystem/v3-NullFlavor"
V3_ROLE = "http://terminology.hl7.org/CodeSystem/v3-RoleCode"
V3_ACT_REASON = "http://terminology.hl7.org/CodeSystem/v3-ActReason"
CDC_RACE_ETH = "urn:oid:2.16.840.1.113883.6.238"
SNOMED = "http://snomed.info/sct"
BCP47 = "urn:ietf:bcp:47"
SSN_SYSTEM = "http://hl7.org/fhir/sid/us-ssn"

OMB_RACE = {"1002-5", "2028-9", "2054-5", "2076-8", "2106-3"}
OMB_ETHNICITY = {"2135-2", "2186-5"}
NULL_FLAVOR = {"0000-0": ("ASKU", "asked but unknown"), "9999-4": ("UNK", "unknown")}

# VistA MARITAL STATUS (file #11, piece 3) -> v3-MaritalStatus.
MARITAL = {
    "D": (V3_MARITAL, "D", "Divorced"),
    "M": (V3_MARITAL, "M", "Married"),
    "W": (V3_MARITAL, "W", "Widowed"),
    "S": (V3_MARITAL, "L", "Legally Separated"),
    "N": (V3_MARITAL, "S", "Never Married"),
    "U": (V3_NULL, "UNK", "unknown"),
}

# SELF IDENTIFIED GENDER (#.024) -> ONC 2015 gender identity value set (SNOMED CT + v3-NullFlavor).
GENDER_IDENTITY = {
    "M": (SNOMED, "446151000124109", "Identifies as male gender (finding)"),
    "F": (SNOMED, "446141000124107", "Identifies as female gender (finding)"),
    "TM": (SNOMED, "407377005", "Female-to-male transsexual (finding)"),
    "TF": (SNOMED, "407376001", "Male-to-female transsexual (finding)"),
    "O": (V3_NULL, "OTH", "other"),
    "N": (V3_NULL, "ASKU", "asked but unknown"),
}


@dataclass
class TransformConfig:
    """Identifier systems are site decisions; the defaults are placeholders to confirm
    with the receiving system before production use."""

    station: str = "500"
    id_template: str = "{dfn}"
    dfn_system_template: str = "urn:va:dfn:{station}"
    icn_system: str = "http://va.gov/mpi"
    claim_number_system: str = "urn:va:claim-number"
    temporary_id_system: str = "urn:va:mpi:temporary-id"
    foreign_id_system: str = "urn:va:mpi:foreign-id"
    medicaid_system: str = "urn:va:medicaid-number"
    military_id_system: str = "urn:va:military-service-number"
    include_confidential: bool = False
    tz: str | None = None
    us_core_profile: bool = True


def _coding(system: str, code: str, display: str | None = None) -> dict:
    c = {"system": system, "code": code}
    if display:
        c["display"] = display
    return c


def _period(start: str | None, end: str | None) -> dict | None:
    p = {k: v for k, v in (("start", start), ("end", end)) if v}
    return p or None


class _Builder:
    def __init__(self, rec: PatientRecord, lk: Lookups, cfg: TransformConfig):
        self.rec, self.lk, self.cfg = rec, lk, cfg

    def date(self, num: str) -> str | None:
        return fm_date(self.rec.get(num), tz=self.cfg.tz)

    # --- names ---------------------------------------------------------------
    def human_name(self, text: str, comp_ien: str) -> dict:
        zero = self.rec.components(comp_ien) if comp_ien else ""
        return name_from_components(zero, text) if zero else parse_name(text)

    def names(self) -> list[dict]:
        out = []
        official = self.rec.get(".01")
        comp = self.rec.get("1.01")
        if official:
            out.append({"use": "official", **self.human_name(official, comp)})
        preferred = self.rec.get(".2405")
        if preferred:
            out.append({"use": "usual", "text": preferred, "given": [preferred]})
        for _, alias in self.rec.multiple("1"):
            text, comp = alias.get(".01"), alias.get("100.03")
            if text:
                out.append({"use": "old", **self.human_name(text, comp)})
        return out

    # --- identifiers ---------------------------------------------------------
    def identifiers(self) -> list[dict]:
        cfg, rec, out = self.cfg, self.rec, []

        def add(value, system=None, code=None, display=None, use=None, text=None, period=None):
            if not value or any(i["value"] == value and i.get("system") == system for i in out):
                return
            ident: dict = {}
            if use:
                ident["use"] = use
            if code or text:
                ident["type"] = {}
                if code:
                    ident["type"]["coding"] = [_coding(V2_0203, code, display)]
                if text:
                    ident["type"]["text"] = text
            if system:
                ident["system"] = system
            ident["value"] = value
            if period:
                ident["period"] = period
            out.append(ident)

        add(rec.dfn, cfg.dfn_system_template.format(station=cfg.station), "MR", "Medical record number", "usual")
        full, icn, chk = rec.get("991.1"), rec.get("991.01"), rec.get("991.02")
        current_icn = full or (f"{icn}V{chk}" if icn and chk else icn)
        icn_use = "temp" if rec.get("991.04") == "Y" else "official"
        add(current_icn, cfg.icn_system, "NI", "National unique individual identifier", icn_use)
        ssn = rec.get(".09")
        if re.fullmatch(r"\d{9}", ssn):
            add(ssn, SSN_SYSTEM, "SS", "Social Security number", "official")
        add(rec.get(".383"), cfg.medicaid_system, "MA", "Patient Medicaid number", "secondary")
        add(rec.get(".313"), cfg.claim_number_system, use="secondary", text="VA claim number")
        for num in (".328", ".3294", ".3299"):
            add(rec.get(num), cfg.military_id_system, "MI", "Military ID number", "secondary")
        add(rec.get("991.08"), cfg.temporary_id_system, use="temp")
        add(rec.get("991.09"), cfg.foreign_id_system, use="secondary")
        for _, hist in rec.multiple("991.91"):
            add(hist.get(".01"), cfg.icn_system, "NI", "National unique individual identifier", "old")
        for _, hist in rec.multiple("992"):
            h_icn, h_chk = hist.get(".01"), hist.get("1")
            changed = fm_date(hist.get("3"), tz=cfg.tz)
            value = f"{h_icn}V{h_chk}" if h_icn and h_chk else h_icn
            if value != current_icn:
                add(value, cfg.icn_system, "NI", "National unique individual identifier", "old",
                    period=_period(None, changed))
        return out

    # --- addresses -----------------------------------------------------------
    def address(self, f: dict[str, str], use: str, type_: str | None = None) -> dict | None:
        rec, lk = self.rec, self.lk
        g = {part: rec.get(num) for part, num in f.items()}
        lines = [g[k] for k in ("line1", "line2", "line3") if g.get(k)]
        state_ien = g.get("state", "")
        state = lk.field("state", state_ien, 2) if state_ien else ""
        addr: dict = {"use": use}
        if type_:
            addr["type"] = type_
        if lines:
            addr["line"] = lines
        if g.get("city"):
            addr["city"] = g["city"]
        if g.get("county") and state_ien:
            county = lk.county(state_ien, g["county"])
            if county:
                addr["district"] = county
        if state or g.get("province"):
            addr["state"] = state or g["province"]
        pc = postal_code(g.get("zip", ""), g.get("zip4", "")) or g.get("postal")
        if pc:
            addr["postalCode"] = pc
        if g.get("country"):
            country = lk.field("country", g["country"], 1)
            if country:
                addr["country"] = country
        return addr if len(addr) > (2 if type_ else 1) else None

    HOME = {"line1": ".111", "line2": ".112", "line3": ".113", "city": ".114", "state": ".115",
            "zip": ".116", "zip4": ".1112", "county": ".117", "province": ".1171",
            "postal": ".1172", "country": ".1173"}
    RESIDENTIAL = {"line1": ".1151", "line2": ".1152", "line3": ".1153", "city": ".1154",
                   "state": ".1155", "zip4": ".1156", "county": ".1157", "province": ".11571",
                   "postal": ".11572", "country": ".11573"}
    TEMP = {"line1": ".1211", "line2": ".1212", "line3": ".1213", "city": ".1214", "state": ".1215",
            "zip": ".1216", "zip4": ".12112", "county": ".12111", "province": ".1221",
            "postal": ".1222", "country": ".1223"}
    CONFIDENTIAL = {"line1": ".1411", "line2": ".1412", "line3": ".1413", "city": ".1414",
                    "state": ".1415", "zip": ".1416", "county": ".14111", "province": ".14114",
                    "postal": ".14115", "country": ".14116"}

    def addresses_and_temp_telecom(self) -> tuple[list[dict], list[dict], dict | None]:
        rec, out, telecom = self.rec, [], []
        home = self.address(self.HOME, "home", "postal")
        if home:
            out.append(home)
        res = self.address(self.RESIDENTIAL, "home", "physical")
        if res:
            out.append(res)
        if rec.get(".12105") == "Y":
            period = _period(self.date(".1217"), self.date(".1218"))
            temp = self.address(self.TEMP, "temp")
            if temp:
                if period:
                    temp["period"] = period
                out.append(temp)
            phone = rec.get(".1219")
            if phone:
                cp = {"system": "phone", "value": phone, "use": "temp"}
                if period:
                    cp["period"] = period
                telecom.append(cp)
        if self.cfg.include_confidential and rec.get(".14105") == "Y":
            period = _period(self.date(".1417"), self.date(".1418"))
            conf = self.address(self.CONFIDENTIAL, "temp")
            if conf:
                if period:
                    conf["period"] = period
                out.append(conf)
            phone = rec.get(".1315")
            if phone:
                cp = {"system": "phone", "value": phone, "use": "temp"}
                if period:
                    cp["period"] = period
                telecom.append(cp)
        return out, telecom, home

    def telecom(self) -> list[dict]:
        out = []
        for num, system, use in ((".131", "phone", "home"), (".132", "phone", "work"),
                                 (".134", "phone", "mobile"), (".135", "pager", None),
                                 (".133", "email", None)):
            value = self.rec.get(num)
            if value:
                cp = {"system": system, "value": value}
                if use:
                    cp["use"] = use
                out.append(cp)
        return out

    # --- contacts ------------------------------------------------------------
    CONTACTS = (
        ("nok1", (V2_0131, "N", "Next-of-Kin"), None,
         {"name": ".211", "rel": ".212", "same": ".2125", "line1": ".213", "line2": ".214",
          "line3": ".215", "city": ".216", "state": ".217", "zip": ".218", "zip4": ".2207",
          "phone": ".219", "work": ".21011", "comp": "1.02"}),
        ("nok2", (V2_0131, "N", "Next-of-Kin"), None,
         {"name": ".2191", "rel": ".2192", "same": ".21925", "line1": ".2193", "line2": ".2194",
          "line3": ".2195", "city": ".2196", "state": ".2197", "zip": ".2198", "zip4": ".2203",
          "phone": ".2199", "work": ".211011", "comp": "1.03"}),
        ("ec1", (V2_0131, "C", "Emergency Contact"), None,
         {"name": ".331", "rel": ".332", "line1": ".333", "line2": ".334", "line3": ".335",
          "city": ".336", "state": ".337", "zip": ".338", "zip4": ".2201", "phone": ".339",
          "work": ".33011", "comp": "1.07"}),
        ("ec2", (V2_0131, "C", "Emergency Contact"), None,
         {"name": ".3311", "rel": ".3312", "line1": ".3313", "line2": ".3314", "line3": ".3315",
          "city": ".3316", "state": ".3317", "zip": ".3318", "zip4": ".2204", "phone": ".3319",
          "work": ".331011", "comp": "1.08"}),
        ("designee", None, "DESIGNEE",
         {"name": ".341", "rel": ".342", "same": ".3405", "line1": ".343", "line2": ".344",
          "line3": ".345", "city": ".346", "state": ".347", "zip": ".348", "zip4": ".2202",
          "phone": ".349", "work": ".34011", "comp": "1.09"}),
        ("employer", (V2_0131, "E", "Employer"), None,
         {"org": ".3111", "line1": ".3113", "line2": ".3114", "line3": ".3115", "city": ".3116",
          "state": ".3117", "zip": ".3118", "zip4": ".2205", "work": ".3119"}),
        ("guardian_va", (V3_ROLE, "GUARD", "guardian"), "VA GUARDIAN",
         {"name": ".2912", "rel": ".2913", "line1": ".2914", "line2": ".2915", "city": ".2916",
          "state": ".2917", "zip": ".2918", "zip4": ".29013", "phone": ".2919", "orgref": ".2911"}),
        ("guardian_civil", (V3_ROLE, "GUARD", "guardian"), "CIVIL GUARDIAN",
         {"name": ".2922", "rel": ".2923", "line1": ".2924", "line2": ".2925", "city": ".2926",
          "state": ".2927", "zip": ".2928", "zip4": ".290012", "phone": ".2929", "org": ".2921"}),
    )

    def contact(self, coding, label, f: dict[str, str], patient_home: dict | None) -> dict | None:
        rec = self.rec
        name = rec.get(f["name"]) if "name" in f else ""
        org = rec.get(f["org"]) if "org" in f else ""
        orgref = rec.get(f["orgref"]) if "orgref" in f else ""
        if not (name or org or orgref):
            return None
        c: dict = {}
        rel = [{"coding": [_coding(*coding)]}] if coding else []
        if label:
            if rel:
                rel[0]["text"] = label
            else:
                rel.append({"text": label})
        if "rel" in f and rec.get(f["rel"]):
            rel.append({"text": rec.get(f["rel"])})
        if rel:
            c["relationship"] = rel
        if name:
            c["name"] = self.human_name(name, rec.get(f["comp"]) if "comp" in f else "")
        telecom = []
        if "phone" in f and rec.get(f["phone"]):
            telecom.append({"system": "phone", "value": rec.get(f["phone"]), "use": "home"})
        if "work" in f and rec.get(f["work"]):
            telecom.append({"system": "phone", "value": rec.get(f["work"]), "use": "work"})
        if telecom:
            c["telecom"] = telecom
        if "same" in f and rec.get(f["same"]) == "Y" and patient_home:
            c["address"] = {k: v for k, v in patient_home.items() if k not in ("use", "type")}
        else:
            parts = {k: v for k, v in f.items() if k in ("line1", "line2", "line3", "city", "state", "zip", "zip4")}
            addr = self.address(parts, "home")
            if addr:
                addr.pop("use")
                c["address"] = addr
        if org:
            c["organization"] = {"display": org}
        elif orgref:
            c["organization"] = {"reference": f"Organization/{orgref}"}
        return c

    def contacts(self, patient_home: dict | None) -> list[dict]:
        out, by_key = [], {}
        ec_same_as_nok = self.rec.get(".3305") == "Y"
        for key, coding, label, f in self.CONTACTS:
            if key == "ec1" and ec_same_as_nok and "nok1" in by_key:
                by_key["nok1"]["relationship"].insert(1, {"coding": [_coding(V2_0131, "C", "Emergency Contact")]})
                continue
            c = self.contact(coding, label, f, patient_home)
            if c:
                by_key[key] = c
                out.append(c)
        return out

    # --- coded fields ---------------------------------------------------------
    def race_ethnicity(self, num: str, table: str, omb: set[str], url: str, legacy: str | None) -> dict | None:
        names, omb_codings, detailed = [], [], []
        for _, entry in self.rec.multiple(num):
            ien = entry.get(".01")
            zero = self.lk.zero(table, ien)
            if not zero:
                continue
            name, code = zero.split("^")[0], (zero.split("^") + ["", "", ""])[2]
            names.append(name)
            if code in omb:
                omb_codings.append(_coding(CDC_RACE_ETH, code, name.title()))
            elif code in NULL_FLAVOR:
                omb_codings.append(_coding(V3_NULL, *NULL_FLAVOR[code]))
            elif code:
                detailed.append(_coding(CDC_RACE_ETH, code, name.title()))
        if not names and legacy:
            ien = self.rec.get(legacy)
            name = self.lk.field(table, ien, 1) if ien else ""
            if name:
                names.append(name)
        if not names:
            return None
        ext = [{"url": "ombCategory", "valueCoding": c} for c in omb_codings]
        ext += [{"url": "detailed", "valueCoding": c} for c in detailed]
        ext.append({"url": "text", "valueString": ", ".join(names)})
        return {"url": url, "extension": ext}

    def extensions(self) -> list[dict]:
        rec, lk, out = self.rec, self.lk, []
        race = self.race_ethnicity("2", "race", OMB_RACE, f"{US_CORE}/us-core-race", ".06")
        if race:
            out.append(race)
        eth = self.race_ethnicity("6", "ethnicity", OMB_ETHNICITY, f"{US_CORE}/us-core-ethnicity", None)
        if eth:
            out.append(eth)
        gi = rec.get(".024")
        if gi in GENDER_IDENTITY:
            fd = rec.fdef("2", ".024")
            out.append({"url": f"{US_CORE}/us-core-genderIdentity", "valueCodeableConcept": {
                "coding": [_coding(*GENDER_IDENTITY[gi])], "text": fd["set_codes"].get(gi, gi)}})
        place = {}
        if rec.get(".092"):
            place["city"] = rec.get(".092")
        st = rec.get(".093")
        if st and lk.field("state", st, 2):
            place["state"] = lk.field("state", st, 2)
        elif rec.get(".0932"):
            place["state"] = rec.get(".0932")
        if rec.get(".0931") and lk.field("country", rec.get(".0931"), 1):
            place["country"] = lk.field("country", rec.get(".0931"), 1)
        if place:
            out.append({"url": f"{EXT}/patient-birthPlace", "valueAddress": place})
        maiden = rec.get(".2403")
        if maiden:
            out.append({"url": f"{EXT}/patient-mothersMaidenName", "valueString": maiden})
        rel = rec.get(".08")
        if rel and lk.field("religion", rel, 1):
            out.append({"url": f"{EXT}/patient-religion",
                        "valueCodeableConcept": {"text": lk.field("religion", rel, 1)}})
        return out

    def communication(self) -> list[dict]:
        entries = []
        for _, e in self.rec.multiple("7"):
            when, lang = e.get(".01"), e.get(".02")
            if lang and lang.upper() != "DECLINED TO ANSWER":
                entries.append((when, lang))
        if not entries:
            return []
        latest: dict[str, str] = {}
        for when, lang in entries:
            if lang not in latest or when > latest[lang]:
                latest[lang] = when
        preferred = max(latest, key=lambda k: latest[k])
        index = {v["zero"].split("^")[0]: v["zero"] for v in self.lk.tables["language"]["entries"].values()}
        out = []
        for lang in sorted(latest, key=lambda k: latest[k], reverse=True):
            cc: dict = {"text": lang}
            code = (index.get(lang.upper(), "").split("^") + ["", ""])[1]
            if code:
                cc["coding"] = [_coding(BCP47, code.lower(), lang.title())]
            item = {"language": cc}
            if lang == preferred:
                item["preferred"] = True
            out.append(item)
        return out

    def marital(self) -> dict | None:
        ien = self.rec.get(".05")
        if not ien:
            return None
        name, code = self.lk.field("marital_status", ien, 1), self.lk.field("marital_status", ien, 3)
        if code not in MARITAL:
            return {"text": name} if name else None
        return {"coding": [_coding(*MARITAL[code])], "text": name}


def patient_to_fhir(record: PatientRecord, lookups: Lookups | None = None,
                    config: TransformConfig | None = None) -> dict:
    """Build a FHIR R4 Patient (JSON-ready dict) from a ^DPT entry."""
    cfg = config or TransformConfig()
    b = _Builder(record, lookups or Lookups.load(), cfg)
    rec = record

    res: dict = {"resourceType": "Patient", "id": cfg.id_template.format(dfn=rec.dfn, station=cfg.station)}
    meta: dict = {}
    if cfg.us_core_profile:
        meta["profile"] = [f"{US_CORE}/us-core-patient"]
    if rec.get(".6") == "1":
        meta["security"] = [_coding(V3_ACT_REASON, "HTEST", "test health data")]
    if meta:
        res["meta"] = meta
    ext = b.extensions()
    if ext:
        res["extension"] = ext
    res["identifier"] = b.identifiers()
    names = b.names()
    if names:
        res["name"] = names
    addresses, temp_telecom, home = b.addresses_and_temp_telecom()
    telecom = b.telecom() + temp_telecom
    if telecom:
        res["telecom"] = telecom
    sex = rec.get(".02")
    gender = {"M": "male", "F": "female"}.get(sex)
    if gender or cfg.us_core_profile:
        res["gender"] = gender or "unknown"
    dob = b.date(".03")
    if dob:
        res["birthDate"] = dob
    dod = b.date(".351")
    if dod:
        res["deceasedDateTime"] = dod
    if addresses:
        res["address"] = addresses
    marital = b.marital()
    if marital:
        res["maritalStatus"] = marital
    mb = rec.get("994")
    if mb in ("Y", "N"):
        res["multipleBirthBoolean"] = mb == "Y"
    contacts = b.contacts(home)
    if contacts:
        res["contact"] = contacts
    comm = b.communication()
    if comm:
        res["communication"] = comm
    pcp = rec.get("404.01")
    if pcp:
        res["generalPractitioner"] = [{"reference": f"Practitioner/{pcp}"}]
    cmor = rec.get("991.03")
    if cmor:
        res["managingOrganization"] = {"reference": f"Organization/{cmor}"}
    merged = rec.get(".082")
    if merged:
        res["link"] = [{"other": {"reference": f"Patient/{merged}"}, "type": "replaced-by"}]
    return res
