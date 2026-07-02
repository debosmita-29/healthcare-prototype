from app.governance.guardrails import HealthcareGuardrails
from app.models.schemas import BriefingSection


def test_input_guardrail_blocks_personal_medical_advice():
    decision = HealthcareGuardrails().validate_input("Should I stop taking my medication?")
    assert not decision.approved
    assert decision.required_revisions


def test_supervisor_requires_safety_language():
    decision = HealthcareGuardrails().supervise_output(
        executive_summary="A strategy briefing grounded in evidence.",
        sections=[
            BriefingSection(
                title="Emerging Treatments",
                bullets=["Pipeline assets should be classified as investigational."],
                evidence_ids=["ev_1"],
            )
        ],
        selected_evidence_ids=["ev_1"],
    )
    assert not decision.approved
    assert any("non-personalized" in item for item in decision.required_revisions)

