import os

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PROXY_X_API_KEY = os.getenv("PROXY_X_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com").rstrip("/")
if OPENAI_BASE_URL.endswith("/v1"):
    OPENAI_BASE_URL = OPENAI_BASE_URL[:-3]

if not OPENAI_API_KEY or not PROXY_X_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY or PROXY_X_API_KEY")

app = FastAPI()

_CLIENT = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None))


@app.on_event("shutdown")
async def _shutdown_client() -> None:
    await _CLIENT.aclose()


def _is_allowed_path(path: str) -> bool:
    normalized = path.lstrip("/")
    exact = {"chat/completions", "completions", "embeddings"}
    prefixes = {"responses", "images", "audio"}

    if normalized in exact:
        return True

    for prefix in prefixes:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True

    return False


def _build_upstream_headers(request: Request) -> dict[str, str]:
    excluded = {
        "authorization",
        "connection",
        "content-length",
        "host",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "x-api-key",
    }

    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        if key.lower() in excluded:
            continue
        headers[key] = value

    headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"
    return headers


def _filter_response_headers(headers: httpx.Headers, streaming: bool) -> dict[str, str]:
    hop_by_hop = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }

    filtered: dict[str, str] = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if key_lower in hop_by_hop:
            continue
        if streaming and key_lower == "content-length":
            continue
        filtered[key] = value

    return filtered


@app.api_route(
    "/v1/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy(path: str, request: Request) -> Response:
    if not _is_allowed_path(path):
        raise HTTPException(status_code=404, detail="Not found")

    client_key = request.headers.get("x-api-key")
    if not client_key or client_key != PROXY_X_API_KEY:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    url = f"{OPENAI_BASE_URL}/v1/{path}"
    headers = _build_upstream_headers(request)

    upstream_request = _CLIENT.build_request(
        request.method,
        url,
        headers=headers,
        params=request.query_params,
        content=request.stream(),
    )

    upstream_response = await _CLIENT.send(upstream_request, stream=True)
    content_type = upstream_response.headers.get("content-type", "")
    is_streaming = content_type.startswith("text/event-stream")

    if is_streaming:
        response_headers = _filter_response_headers(upstream_response.headers, streaming=True)
        return StreamingResponse(
            upstream_response.aiter_raw(),
            status_code=upstream_response.status_code,
            headers=response_headers,
            background=BackgroundTask(upstream_response.aclose),
        )

    body = await upstream_response.aread()
    response_headers = _filter_response_headers(upstream_response.headers, streaming=False)
    await upstream_response.aclose()
    return Response(
        content=body,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )
