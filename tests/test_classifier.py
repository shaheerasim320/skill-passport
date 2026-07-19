from pathlib import Path

from skill_passport_core.ast_tracer import EvidenceLocation, Finding, trace_python_files
from skill_passport_core.fetcher import FetchedFile


ROOT = Path(__file__).resolve().parents[1]


def local_source(fixture_name: str, filename: str) -> FetchedFile:
    path = ROOT / "fixtures" / fixture_name / filename
    return FetchedFile(path=filename, content=path.read_text(encoding="utf-8"))


def local_claims(fixture_name: str) -> str:
    return (ROOT / "fixtures" / fixture_name / "SKILL.md").read_text(encoding="utf-8")


def classify(findings, claims_text: str):
    # Imported here so every test fails independently until both modules exist.
    from skill_passport_core.classifier import classify_behavior
    from skill_passport_core.profile import build_behavior_profile

    profile = build_behavior_profile(findings)
    return profile, classify_behavior(profile, claims_text)


def classification_for(classifications, category: str):
    return next(item for item in classifications if item.category == category)


def test_verified_empty_profile():
    findings = trace_python_files([local_source("verified", "formatter.py")])
    profile, classifications = classify(findings, local_claims("verified"))

    assert profile.network.detected is False
    assert profile.filesystem.detected is False
    assert profile.secrets.detected is False
    assert profile.shell.detected is False
    assert classifications == []


def test_review_disclosed():
    findings = trace_python_files([local_source("review", "telemetry.py")])
    profile, classifications = classify(findings, local_claims("review"))

    assert profile.network.detected is True
    assert classification_for(classifications, "network").status == "DISCLOSED"


def test_high_risk_contradiction():
    findings = trace_python_files([local_source("high_risk", "sync.py")])
    profile, classifications = classify(findings, local_claims("high_risk"))

    assert profile.network.detected is True
    assert profile.secrets.detected is True
    network = classification_for(classifications, "network")
    assert network.status == "CONTRADICTION"
    assert network.claim_excerpt == "No network access required."


def test_disclosed_filesystem():
    pdf_files = (
        "check_bounding_boxes.py",
        "check_fillable_fields.py",
        "convert_pdf_to_images.py",
        "create_validation_image.py",
        "extract_form_field_info.py",
        "extract_form_structure.py",
        "fill_fillable_fields.py",
        "fill_pdf_form_with_annotations.py",
    )
    findings = [
        Finding(
            category="filesystem",
            source=None,
            sink=EvidenceLocation(
                file=f"skills/pdf/scripts/{filename}",
                line=1,
                description="filesystem read",
            ),
            assignment_chain=("filesystem read",),
        )
        for filename in pdf_files
    ]
    claims = "Extract text, create PDFs, and handle forms."
    profile, classifications = classify(findings, claims)

    assert profile.filesystem.detected is True
    assert len(profile.filesystem.evidence) == 8
    assert classification_for(classifications, "filesystem").status == "DISCLOSED"
