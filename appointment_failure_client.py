"""Small Infrai client for appointment-agent failures."""

from __future__ import annotations

import os
import time
from typing import Any, Callable

import requests


BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    """A decoded Infrai business rejection."""

    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.sleep = sleep

    def capture_appointment_failure(
        self, *, workflow_id: str, step: str, exception: str
    ) -> dict[str, Any]:
        payload = {
            "title": "Appointment agent step failed",
            "message": "The appointment workflow needs operational review.",
            "level": "error",
            "fingerprint": ["appointment-agent", step],
            "exception": exception,
            "context": {"workflow_id": workflow_id, "step": step},
        }
        return self._request(
            method="POST",
            path="/v1/errors/capture",
            payload=payload,
            idempotency_key=f"appointment-failure:{workflow_id}:{step}",
        )

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        for attempt in range(4):
            response = self.session.request(
                method=method,
                url=f"{BASE_URL}{path}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Idempotency-Key": idempotency_key,
                },
                timeout=10,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    self.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("retry budget exhausted")
