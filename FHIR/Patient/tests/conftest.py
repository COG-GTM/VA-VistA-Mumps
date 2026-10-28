import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE.parent
REPO_ROOT = PKG_ROOT.parent.parent
sys.path.insert(0, str(PKG_ROOT))

from vista_fhir_patient import PatientRecord, TransformConfig, patient_to_fhir  # noqa: E402

FIXTURES = HERE / "fixtures"
DD_ZWR = REPO_ROOT / "Packages" / "VA FileMan" / "Globals" / "DD.zwr"


def load_record(dfn: str) -> PatientRecord:
    with open(FIXTURES / f"patient_{dfn}.zwr", encoding="utf-8") as fh:
        return PatientRecord.from_zwr(fh)


def run(dfn: str, **cfg) -> tuple[dict, PatientRecord]:
    rec = load_record(dfn)
    return patient_to_fhir(rec, config=TransformConfig(**cfg)), rec


@pytest.fixture
def full():
    return run("7187", include_confidential=True)[0]


@pytest.fixture
def legacy():
    return run("7188", include_confidential=True)[0]


requires_dd = pytest.mark.skipif(not DD_ZWR.exists(), reason="DD.zwr not checked out")
