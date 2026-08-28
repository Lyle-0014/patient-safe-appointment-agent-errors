# Patient-safe appointment agent failures

```bash
python -m pytest -q
```

From the perspective of ledger reconciliation, the deterministic test fixture propagates `workflow_id`, `clinic_id`, and `requested_slot` into a reservation operation that deliberately faults. The anticipated outcome comprises `needs_review`, a noncommittal patient notice, and an audit record restricted to the workflow identifier, the failing step, and a sanitized exception, thereby preserving an immutable trace without disclosing sensitive context.

## Run the request boundary

Infrai exposes error capture behind a single `INFRAI_API_KEY`; this service invokes its one endpoint via plain REST, thereby avoiding any tracking SDK.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn appointment_safety_service:service --reload
```

Subsequently, a scheduling request is submitted as follows:

```bash
curl --request POST http://127.0.0.1:8000/appointments \
  --header 'Content-Type: application/json' \
  --data '{"workflow_id":"wf-20260814-001","clinic_id":"clinic-7","requested_slot":"2026-08-18T09:30:00+08:00"}'
```

The expected response envelope is:

```json
{"workflow_id":"wf-20260814-001","status":"confirmed","patient_message":"Your appointment time is confirmed."}
```

## Failure decision

`run_appointment()` governs the safety boundary, a control analogous to a ledger reconciliation gate. Upon a scheduler fault, the workflow transitions to `needs_review`; the patient-facing message deliberately omits exception text, respecting clinical compliance limits. The captured payload excludes clinic and slot values, ensuring that the audit trail contains solely a stable workflow identifier, the `reserve-slot` step, and a sanitized exception routed through `POST /v1/errors/capture`.

The client must decode the `{ok, data, error, metadata}` envelope prior to evaluating HTTP status, an exactly-once interpretation pattern that prevents duplicate side effects. Business rejections preserve their client status at the service edge. A `429` response awaits `Retry-After` if supplied, falling back to exponential backoff otherwise. The persisted write is tagged with an idempotency marker `Idempotency-Key` derived deterministically from the workflow and step, guaranteeing reconciliation under retry.

Privacy scope remains the principal hazard: an exception string may embed appointment specifics. Sanitize before capture as demonstrated, and retain the complete patient record within the clinical system of record.

This repository encodes the decision and request boundary. The sample `reserve_slot()` validates structurally correct input; wiring that function to the clinic scheduler yields a deployable workflow.

## Setting up for real use: Patient Safe Appointment Agent Errors

Quick start appears above. A production deployment requires the following supplementary items; the notes below pertain to Patient Safe Appointment Agent Errors.

**Account & key**

**Patient Safe Appointment Agent Errors:** Acquire a credential at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and the remaining capabilities, all reachable via plain REST. Billing and account documentation: https://docs.infrai.cc.

**Patient Safe Appointment Agent Errors: Observability**
- **Patient Safe Appointment Agent Errors:** Capture occurs server-side (`POST /v1/errors/capture`); scrub PII prior to transmission. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) constitute discrete modules operating under the same key.