from appointment_safety_service import AppointmentRequest, run_appointment


class RecordingErrors:
    def __init__(self) -> None:
        self.captured: dict[str, str] | None = None

    def capture_appointment_failure(self, **payload: str) -> dict[str, str]:
        self.captured = payload
        return {"event_id": "evt-test"}


def test_failure_routes_to_review_without_patient_details() -> None:
    errors = RecordingErrors()
    request = AppointmentRequest(
        workflow_id="wf-20260814-001",
        clinic_id="cardiology-private",
        requested_slot="2026-08-18T09:30:00+08:00",
    )

    def failed_reservation(clinic_id: str, requested_slot: str) -> bool:
        raise ConnectionError(f"scheduler rejected {clinic_id} at {requested_slot}")

    result = run_appointment(request, failed_reservation, errors)  # type: ignore[arg-type]

    assert result.status == "needs_review"
    assert result.patient_message == (
        "Your appointment request is under review. "
        "The clinic will confirm the time separately."
    )
    assert errors.captured == {
        "workflow_id": "wf-20260814-001",
        "step": "reserve-slot",
        "exception": "ConnectionError: reservation step raised",
    }
    assert "cardiology-private" not in str(errors.captured)
    assert "2026-08-18" not in str(errors.captured)
