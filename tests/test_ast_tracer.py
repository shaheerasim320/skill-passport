from functools import lru_cache

from skill_passport_core.fetcher import FetchedFile, GitHubRepositoryFetcher


FIXTURE_URLS = {
    "verified": "https://github.com/shaheerasim320/text-formatter",
    "review": "https://github.com/shaheerasim320/project-helper",
    "high_risk": "https://github.com/shaheerasim320/auto-formatter",
    "disclosed_filesystem": "https://github.com/anthropics/skills/tree/main/skills/pdf/scripts",
}


@lru_cache
def published_source_files(fixture_name: str) -> tuple[FetchedFile, ...]:
    return GitHubRepositoryFetcher(timeout_seconds=60).fetch(
        FIXTURE_URLS[fixture_name]
    ).source_files


def tracer():
    # Imported here so every test fails independently until the tracer exists.
    from skill_passport_core.ast_tracer import trace_python_files

    return trace_python_files


def trace(files: list[FetchedFile]):
    return tracer()(files)


def test_verified_no_findings():
    findings = trace(list(published_source_files("verified")))

    assert findings == []


def test_review_network_finding():
    findings = trace(list(published_source_files("review")))

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
    findings = trace(list(published_source_files("high_risk")))

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
    pdf_files = published_source_files("disclosed_filesystem")
    findings = trace_python_files(list(pdf_files))

    filesystem_findings = [finding for finding in findings if finding.category == "filesystem"]
    detected_files = {finding.sink.file for finding in filesystem_findings}
    assert {file.path for file in pdf_files} <= detected_files
    descriptions = {finding.sink.description for finding in filesystem_findings}
    assert any("filesystem read" in description for description in descriptions)
    assert any("filesystem write" in description for description in descriptions)
