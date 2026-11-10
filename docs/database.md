# Database schema

17 tables, created by migrations `0002` to `0006` in `apps/api/migrations/versions/`.
Models are in `apps/api/app/models/`. Models hold columns and constraints only; business
rules live in services.

## Conventions

- Primary keys are UUIDs. Exceptions: `user_facility_roles`, `stock_thresholds` and
  `stock_balances` use composite keys.
- Every constraint has an explicit, predictable name (`ck_`, `uq_`, `fk_`, `ix_`, `pk_` prefixes).
- Timestamps are timezone-aware UTC, set by the application. Dates (`expiry_date`,
  `occurred_on`) are plain dates compared in the facility's time zone.
- Enums are `VARCHAR` plus a named `CHECK`, never native enums. Migrations write the values out
  and do not import `app/core/enums.py`; adding an enum value needs a new migration.
- Codes and emails are stored lower case (a `CHECK` enforces it).
- Nothing is deleted and there is no `ON DELETE CASCADE`. Users, facilities and items are
  deactivated. The ledger and audit tables are append-only (by code and tests; see Limits).

## Tables

| Table | What it holds | Rules enforced by the database |
|---|---|---|
| `users` | Accounts | lower-case unique email; failed logins >= 0 |
| `facilities` | Central store and PHCs | lower-case unique code; type is one of two values |
| `user_facility_roles` | A user's role at a facility | one role per user and facility; role is a known value |
| `sessions` | Server-side sessions (token hash only) | unique token hash |
| `items` | The item catalogue | lower-case unique code |
| `batches` | Batches with expiry | unique batch number per item, case-insensitive |
| `stock_thresholds` | Reorder and critical levels | reorder >= critical >= 0 |
| `stock_balances` | On hand per facility and batch | available >= 0, quarantined >= 0 |
| `stock_movements` | The ledger | delta is never 0; balance_after >= 0; adjustment needs a reason; opening needs signed_off_by; reversal rows (and only they) point at a target; a row is reversed at most once; one opening per facility and batch |
| `resupply_requests` | Requests | requester is not the supplier; version >= 1 |
| `resupply_request_lines` | Request lines | one line per item; approved <= requested |
| `shipments` | What the store sent | one shipment per request; from is not to |
| `shipment_lines` | Per request line and batch | quantity >= 1; unique per shipment, line and batch |
| `receipt_lines` | What the PHC counted | received <= dispatched (composite foreign key keeps a copy of the dispatched quantity honest) |
| `discrepancies` | Shortfalls found at receipt | one per receipt line; open and resolved states are consistent |
| `audit_records` | Who did what and when | (indexes only) |
| `idempotency_keys` | Outcomes of retried actions | unique per user and key; response fields set together |

## Limits

- Append-only is not enforced by triggers. Reconciliation (`GET /admin/reconciliation`) and the
  tests catch violations. Consider revoking UPDATE and DELETE on the ledger and audit tables
  for the application's database role in milestone A15.
- Rules that span tables (a `phc_officer` only at a PHC, a batch belonging to the right item)
  are enforced by services, not by the database.
- Re-recording opening stock for a batch after reversing it is blocked; use an adjustment.
- `sessions` and `idempotency_keys` grow and need a purge job (A15).
