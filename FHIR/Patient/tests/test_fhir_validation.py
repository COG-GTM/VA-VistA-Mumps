"""Structural validation against FHIR R4-family models (fhir.resources R4B Patient).

R4B made no changes to Patient relative to R4 4.0.1. Profile-level (US Core)
validation uses the HL7 validator; see README.
"""

import pytest

from conftest import run

patient_model = pytest.importorskip("fhir.resources.R4B.patient")


@pytest.mark.parametrize("dfn", ["7187", "7188"])
@pytest.mark.parametrize("confidential", [True, False])
def test_output_parses_as_fhir_patient(dfn, confidential):
    res, _ = run(dfn, include_confidential=confidential)
    model = patient_model.Patient.parse_obj(res)
    assert model.id == dfn
