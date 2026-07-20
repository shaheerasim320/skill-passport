"""SSE analysis endpoint backed entirely by the shared core pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from queue import Queue
from threading import Thread
from typing import Any, Iterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from skill_passport_core.fetcher import FetchError, RepositoryNotFoundError
from skill_passport_core.reasoner import ReasonerError, analyze_repository, answer_follow_up


app = FastAPI(
    title="Skill Passport API",
    version="0.1.3",
    description=(
        "Analyze a public GitHub skill repository without executing its code. "
        "Use **POST /analyze** below, click **Try it out**, replace the example "
        "URL, then click **Execute**. The response is a Server-Sent Events (SSE) "
        "stream: progress events arrive first, followed by a profile and either a "
        "verdict or an error."
    ),
    openapi_tags=[
        {
            "name": "analysis",
            "description": "Read-only public GitHub repository analysis.",
        }
    ],
)


class AnalysisRequest(BaseModel):
    github_url: str = Field(
        ...,
        description="Public GitHub repository URL or github.com/owner/repository.",
        examples=["github.com/shaheerasim320/auto-formatter"],
    )


class FollowUpRequest(BaseModel):
    thread_id: str = Field(..., description="Codex thread ID returned in the final verdict.")
    question: str = Field(..., min_length=1, description="Question grounded in the completed analysis.")


@app.post(
    "/analyze",
    response_class=StreamingResponse,
    tags=["analysis"],
    summary="Analyze a public GitHub skill repository",
    description=(
        "Streams status, behavior profile, and verdict events. This endpoint never "
        "executes repository code or an installation command."
    ),
    response_description="A text/event-stream sequence ending in a verdict or error event.",
    responses={
        200: {
            "description": "SSE analysis stream.",
            "content": {
                "text/event-stream": {
                    "example": (
                        'event: progress\\n'
                        'data: {"type":"progress","stage":"fetching"}\\n\\n'
                        'event: verdict\\n'
                        'data: {"type":"verdict","verdict":{"trust_level":"HIGH RISK"}}\\n\\n'
                    )
                }
            },
        }
    },
)
def analyze(request: AnalysisRequest) -> StreamingResponse:
    """Stream one stateless repository analysis as Server-Sent Events."""
    return StreamingResponse(
        _analysis_stream(request.github_url),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post(
    "/follow-up",
    tags=["analysis"],
    summary="Ask a grounded question about a completed analysis",
    description="Resumes the existing Codex reasoning thread. It does not re-fetch or re-analyze the repository.",
)
def follow_up(request: FollowUpRequest) -> dict[str, str]:
    """Return one grounded answer for the supplied analysis thread."""
    try:
        return {"answer": answer_follow_up(request.question, request.thread_id)}
    except (ReasonerError, ValueError, OSError) as error:
        # FastAPI returns a concise user-facing error rather than a traceback.
        raise HTTPException(status_code=400, detail=str(error)) from error


def _analysis_stream(github_url: str) -> Iterator[str]:
    events: Queue[tuple[str, dict[str, Any]] | None] = Queue()
    last_stage = "fetching"

    def stage_callback(stage: str, data: dict[str, Any]) -> None:
        nonlocal last_stage
        last_stage = stage
        events.put(
            (
                "progress",
                {
                    "type": "progress",
                    "stage": stage,
                    "status": _stage_status(stage),
                    "data": _json_ready(data),
                },
            )
        )
        if stage == "profiling":
            events.put(
                (
                    "profile",
                    {
                        "type": "profile",
                        "behavior_profile": _json_ready(data["behavior_profile"]),
                    },
                )
            )

    def run_analysis() -> None:
        try:
            verdict = analyze_repository(github_url, stage_callback=stage_callback)
            events.put(("verdict", {"type": "verdict", "verdict": verdict.to_dict()}))
        except RepositoryNotFoundError:
            events.put(
                (
                    "error",
                    {
                        "type": "error",
                        "code": "repository_not_found",
                        "message": "Repository not found or not publicly accessible.",
                    },
                )
            )
        except FetchError as error:
            message = str(error)
            is_rate_limited = "rate limit" in message.lower() or "HTTP 429" in message
            events.put(
                (
                    "error",
                    {
                        "type": "error",
                        "code": "github_rate_limited" if is_rate_limited else "analysis_failed",
                        "stage": last_stage,
                        "message": message,
                    },
                )
            )
        except (ReasonerError, OSError) as error:
            events.put(
                (
                    "error",
                    {
                        "type": "error",
                        "code": "reasoning_unavailable" if last_stage == "reasoning" else "analysis_failed",
                        "stage": last_stage,
                        "message": str(error),
                    },
                )
            )
        except ValueError as error:
            events.put(("error", {"type": "error", "code": "analysis_failed", "stage": last_stage, "message": str(error)}))
        except Exception:
            events.put(
                (
                    "error",
                    {
                        "type": "error",
                        "code": "analysis_failed",
                        "stage": last_stage,
                        "message": "Analysis failed unexpectedly.",
                    },
                )
            )
        finally:
            events.put(None)

    Thread(target=run_analysis, daemon=True).start()
    while True:
        item = events.get()
        if item is None:
            return
        event, payload = item
        yield _sse(event, payload)


def _stage_status(stage: str) -> str:
    return {
        "fetching": "Fetching repository claims and source files.",
        "parsing": "Parsing repository claims and source files.",
        "tracing": "Tracing deterministic data flows.",
        "profiling": "Building the Behavior Profile.",
        "classifying": "Comparing observed behavior with claims.",
        "reasoning": "Reasoning through the local Codex CLI.",
    }[stage]


def _json_ready(value: Any) -> Any:
    if is_dataclass(value):
        return _json_ready(asdict(value))
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
