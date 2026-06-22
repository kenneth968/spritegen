from __future__ import annotations

import json
from urllib.error import HTTPError, URLError


def provider_request_error(provider: str, action: str, exc: BaseException) -> str:
    if isinstance(exc, HTTPError):
        return _http_error_message(provider, action, exc)
    if isinstance(exc, URLError):
        return f"{provider} {action} failed before receiving a response: {exc.reason}"
    if isinstance(exc, TimeoutError):
        return f"{provider} {action} timed out. Try again or switch provider/model."
    return f"{provider} {action} failed: {exc}"


def _http_error_message(provider: str, action: str, exc: HTTPError) -> str:
    status = f"HTTP {exc.code}"
    if exc.reason:
        status = f"{status} {exc.reason}"
    detail = _http_error_detail(exc)
    retry = _retry_after_text(exc)
    if exc.code == 429:
        return (
            f"{provider} {action} hit a rate limit or quota limit ({status})."
            f"{retry} Switch provider/model, wait and retry, or use Mock/Pollinations "
            f"for no-key local tests.{detail}"
        )
    if exc.code in {401, 403}:
        return (
            f"{provider} {action} was rejected by the provider ({status}). "
            f"Check the API key, account access, and selected model.{detail}"
        )
    return f"{provider} {action} failed ({status}).{detail}"


def _retry_after_text(exc: HTTPError) -> str:
    retry_after = exc.headers.get("Retry-After") if exc.headers else ""
    if retry_after.isdecimal():
        return f" Retry after {retry_after} seconds."
    if retry_after:
        return f" Retry after {retry_after}."
    return ""


def _http_error_detail(exc: HTTPError) -> str:
    body = _http_error_body(exc)
    if not body:
        return ""
    message = _json_error_message(body)
    if message:
        return f" Provider detail: {message}"
    return f" Provider detail: {body[:300]}"


def _http_error_body(exc: HTTPError) -> str:
    try:
        data = exc.read()
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace").strip()


def _json_error_message(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
    if isinstance(error, str):
        return error
    message = payload.get("message")
    if isinstance(message, str):
        return message
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    return ""
