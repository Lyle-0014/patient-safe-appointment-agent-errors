"""Typed appointment workflow with patient-safe failure notifications."""

from __future__ import annotations

from typing import Callable, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from appointment_failure_client import InfraiClient, InfraiError


class AppointmentRequest(BaseModel):
    workflow_id: str = Field(min_length=8, max_length=64)
    clinic_id: str = Field(min_length=2, max_length=64)
    requested_slot: str = Field(min_length=10, max_length=40)


class AppointmentResult(BaseModel):
    workflow_id: str
    status: Literal["confirmed", "needs_review"]
    patient_message: str


def run_appointment(
    request: AppointmentRequest,
    reserve_slot: Callable[[str, str], bool],
    errors: InfraiClient,
) -> AppointmentResult:
    try:
        confirmed = reserve_slot(request.clinic_id, request.requested_slot)
    except Exception as exc:
        # Never send patient or slot data to error tracking.
        safe_exception = f"{type(exc).__name__}: reservation step raised"
        errors.capture_appointment_failure(
            workflow_id=request.workflow_id,
            step="reserve-slot",
            exception=safe_exception,
        )
        return AppointmentResult(
            workflow_id=request.workflow_id,
            status="needs_review",
            patient_message=(
                "Your appointment request is under review. "
                "The clinic will confirm the time separately."
            ),
        )

    if confirmed:
        return AppointmentResult(
            workflow_id=request.workflow_id,
            status="confirmed",
            patient_message="Your appointment time is confirmed.",
        )
    return AppointmentResult(
        workflow_id=request.workflow_id,
        status="needs_review",
        patient_message="The clinic will contact you to confirm another time.",
    )


service = FastAPI(title="Appointment Safety Service")


def reserve_slot(clinic_id: str, requested_slot: str) -> bool:
    """Executable example boundary; replace with the clinic scheduler."""
    return bool(clinic_id and requested_slot)


@service.post("/appointments", response_model=AppointmentResult)
def create_appointment(request: AppointmentRequest) -> AppointmentResult:
    try:
        return run_appointment(request, reserve_slot, InfraiClient())
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.code) from exc
