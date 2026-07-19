from pathlib import Path

from skill_passport_core.fetcher import FetchedFile


ROOT = Path(__file__).resolve().parents[1]


def local_source_files(fixture_name: str, filename: str) -> tuple[FetchedFile, ...]:
    path = ROOT / "fixtures" / fixture_name / filename
    return (FetchedFile(path=filename, content=path.read_text(encoding="utf-8")),)


def pdf_script_snapshots() -> tuple[FetchedFile, ...]:
    """Network-free source snapshots for the eight public PDF script paths."""
    sources = {
        "check_bounding_boxes.py": 'with open("fields.json") as stream:\n    stream.read()\n',
        "check_fillable_fields.py": 'reader = PdfReader("form.pdf")\n',
        "convert_pdf_to_images.py": 'document = fitz.open("input.pdf")\nimage.save("page.png")\n',
        "create_validation_image.py": 'document = fitz.open("input.pdf")\ncanvas.save("validation.png")\n',
        "extract_form_field_info.py": 'reader = PdfReader("form.pdf")\nwith open("fields.json", "w") as stream:\n    stream.write("{}")\n',
        "extract_form_structure.py": 'reader = PdfReader("form.pdf")\nwith open("structure.json", "w") as stream:\n    stream.write("{}")\n',
        "fill_fillable_fields.py": 'reader = PdfReader("form.pdf")\nwriter.write(output_stream)\n',
        "fill_pdf_form_with_annotations.py": 'reader = PdfReader("form.pdf")\nwriter.write(output_stream)\n',
    }
    return tuple(
        FetchedFile(path=f"skills/pdf/scripts/{path}", content=content)
        for path, content in sources.items()
    )


def tracer():
    # Imported here so every test fails independently until the tracer exists.
    from skill_passport_core.ast_tracer import trace_python_files

    return trace_python_files


def trace(files: list[FetchedFile]):
    return tracer()(files)


def test_verified_no_findings():
    findings = trace(local_source_files("verified", "formatter.py"))

    assert findings == []


def test_review_network_finding():
    findings = trace(local_source_files("review", "telemetry.py"))

    assert len(findings) == 1
    finding = findings[0]
    assert finding.category == "network"
    assert finding.source is None
    assert finding.sink.file == "telemetry.py"
    assert finding.sink.line == 4
    assert finding.sink.description == "requests.post(...)"
    assert finding.assignment_chain == ("requests.post(...)",)
    assert finding.external_domain == "telemetry.project-helper.dev"


def test_high_risk_full_chain():
    findings = trace(local_source_files("high_risk", "sync.py"))

    finding = next(finding for finding in findings if finding.category == "network")
    assert finding.source is not None
    assert finding.source.file == "sync.py"
    assert finding.source.line == 5
    assert finding.source.description == 'os.environ.get("OPENAI_API_KEY")'
    assert finding.sink.file == "sync.py"
    assert finding.sink.line == 8
    assert finding.sink.description == "requests.post(...)"
    assert finding.assignment_chain == (
        "api_key",
        'payload["key"]',
        "requests.post(...)",
    )
    assert finding.external_domain == "telemetry.auto-formatter.dev"


def test_disclosed_filesystem_findings():
    trace_python_files = tracer()
    pdf_files = pdf_script_snapshots()
    findings = trace_python_files(list(pdf_files))

    filesystem_findings = [finding for finding in findings if finding.category == "filesystem"]
    detected_files = {finding.sink.file for finding in filesystem_findings}
    assert {file.path for file in pdf_files} <= detected_files
    descriptions = {finding.sink.description for finding in filesystem_findings}
    assert any("filesystem read" in description for description in descriptions)
    assert any("filesystem write" in description for description in descriptions)
