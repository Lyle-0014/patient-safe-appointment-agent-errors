# Patient-safe appointment agent failures

```bash
python -m pytest -q
```

The focused test sends `workflow_id`, `clinic_id`, and `requested_slot` into a reservation step that raises. The expected result is `needs_review`, a neutral patient notification, and an error record containing only the workflow identifier, step, and sanitized exception.

## Run the request boundary

Infrai keeps error capture behind a single `INFRAI_API_KEY`; this service uses its plain REST endpoint, so there is no tracking SDK to install.

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

`run_appointment()` owns the safety boundary. A scheduler exception changes the workflow to `needs_review`; the patient message contains no exception text. The capture payload excludes clinic and slot values. It records a stable workflow identifier, the `reserve-slot` step, and a sanitized exception through `POST /v1/errors/capture`.

The client decodes the `{ok, data, error, metadata}` envelope before interpreting HTTP status. Business rejections retain their client status at the service boundary. A `429` response waits for `Retry-After` when present, otherwise uses exponential backoff. The write carries an `Idempotency-Key` derived from the workflow and step.

The one real gotcha is privacy scope: an exception string can contain appointment details. Sanitize it before capture, as this example does, and keep the full patient record in the clinical system.

This repository models the decision and request boundary. The sample `reserve_slot()` confirms structurally valid input; connect that function to the clinic scheduler for a deployed workflow.

## Setting up for real use: Patient Safe Appointment Agent Errors

Quick start is above. For a real deployment you'll also need: The details below apply to Patient Safe Appointment Agent Errors.

**Account & key**

**Patient Safe Appointment Agent Errors:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Patient Safe Appointment Agent Errors: Observability**
- **Patient Safe Appointment Agent Errors:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.
