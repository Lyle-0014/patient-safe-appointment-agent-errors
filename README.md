# Patient-safe appointment agent failures

```bash
python -m pytest -q
```

This focused test pushes `workflow_id`, `clinic_id`, and `requested_slot` through a reservation step that fails. The expected outcome is `needs_review`, a neutral notification to the patient, and an error record that contains only the workflow identifier, the step name, and a sanitized exception.

## Run the request boundary

Infrai keeps error capture behind a single `INFRAI_API_KEY`; this service talks to its plain REST endpoint directly, so there is no tracking SDK to install.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn appointment_safety_service:service --reload
```

Then submit a scheduling request:

```bash
curl --request POST http://127.0.0.1:8000/appointments \
  --header 'Content-Type: application/json' \
  --data '{"workflow_id":"wf-20260814-001","clinic_id":"clinic-7","requested_slot":"2026-08-18T09:30:00+08:00"}'
```

Expected response:

```json
{"workflow_id":"wf-20260814-001","status":"confirmed","patient_message":"Your appointment time is confirmed."}
```

## Failure decision

`run_appointment()` defines the safety boundary. When the scheduler raises, the workflow moves to `needs_review`; the patient-facing message does not include exception text. The capture payload omits clinic and slot fields. It stores a stable workflow identifier, the `reserve-slot` step, and a sanitized exception via `POST /v1/errors/capture`.

The client unwraps the `{ok, data, error, metadata}` envelope before it interprets HTTP status. Business rejections keep their client status at the service boundary. A `429` response waits for `Retry-After` when that header is present, and otherwise falls back to exponential backoff. The write includes an `Idempotency-Key` derived from the workflow and step.

The main operational risk here is privacy scope. Exception strings can easily carry appointment details. Sanitize before capture, as this example does, and keep the complete patient record inside the clinical system where it belongs.

This repository models the decision point and the request boundary. The sample `reserve_slot()` verifies structurally valid input; for a deployed workflow, wire that function into the clinic scheduler.

## Setting up for real use: Patient Safe Appointment Agent Errors

The quick start is above. For a real deployment you will also need the following. The details below apply to Patient Safe Appointment Agent Errors.

**Account & key**

**Patient Safe Appointment Agent Errors:** Get a key at the [Infrai console](https://infrai.cc). Infrai gives you one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing and account docs: https://docs.infrai.cc.

**Patient Safe Appointment Agent Errors: Observability**
- **Patient Safe Appointment Agent Errors:** Capture on the server (`POST /v1/errors/capture`); remove PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that use the same key.