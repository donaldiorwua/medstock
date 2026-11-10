# API contract

These files are the agreement between the API (Engineer A) and the web app (Engineer B).
**Do not edit the JSON files by hand.** They are generated from the code.

| File | What it is |
|---|---|
| `openapi.json` | Every endpoint, request and response schema. Generate TypeScript types from this. |
| `enums.json` | Every status, role and reason code with its allowed values. |
| `errors.json` | Every error `code`, its HTTP status, its meaning, and an example error body. |
| `examples/<operationId>/<status>.json` | Hand-written request and response examples, checked by tests against the real schemas. They are also embedded in `openapi.json`, so a mock server (for example Prism) can run from that one file. |

## Everyday commands (run in `apps/api`)

```bash
python -m app.contract export   # regenerate the three JSON files after changing the API
python -m app.contract check    # what CI runs: fails if the committed files are out of date
```

## Changing the contract

1. Change the code (schemas, routes, enums or error codes).
2. Run `python -m app.contract export` and commit the regenerated files with the code change.
3. Add or update the example under `examples/` for any endpoint you touched.
4. Open a pull request. The other engineer must approve it (CODEOWNERS enforces this).

**Additive changes** (a new endpoint, a new optional response field, a new enum value, a new
error code) need nothing else. Bump the minor part of `CONTRACT_VERSION` in
`apps/api/app/contract/__init__.py`.

**Breaking changes** (removing or renaming a field, endpoint, enum value or error code, making a
field required, changing a type) must:

- carry the `breaking-contract` label on the pull request (otherwise CI fails),
- ship behind a new field or endpoint where possible (blueprint 10.4),
- bump the major part of `CONTRACT_VERSION`.

## Conventions

- Base path `/api/v1`, JSON, `snake_case`, UUID ids, UTC timestamps.
- Success: `{ "data": ... }`. Failure: `{ "error": { "code", "message", "details", "request_id" } }`.
- Operation IDs are the route function names; renaming a function is a contract change.
- Every response model is a named class (for example `HealthResponse`) so generated types are readable.
- Validation failures use the same error envelope, with `details[].path` matching the request body.

## Status of the endpoints

Every endpoint in `openapi.json` is real as far as the contract goes. Until its milestone is
built, calling it returns `501 NOT_IMPLEMENTED` in the standard error envelope, except
`GET /health`, which works now. Work from the examples until an endpoint goes live.

## Who may call what

Route descriptions state the intended roles (for example "Admin only"). They are enforced
when authentication and authorisation are built (A4 and A5). Treat them as the agreed
behaviour; tell Engineer A if one is wrong.

## Example files

- One file per operation and status: `examples/<operationId>/<status>.json`.
- Shape: `description`, `request` (`method`, `path`, optional `body`), `response` (`status`, `body`).
- Every operation needs at least one 2xx example. Add failure examples where they teach something.
- The 2xx request body is embedded as the operation's request example.

## The stock ledger and idempotency

- Every stock-changing POST needs an `Idempotency-Key` header (a UUID is ideal). Repeating the
  same key with the same body returns the original result with `Idempotent-Replay: true` and
  posts nothing twice. The same key with a different body returns `IDEMPOTENCY_KEY_CONFLICT`.
  Create a new key for each new user action, and reuse it only when retrying that same action.
- The ledger is append-only. Each row changes one balance (`bucket`: `available` or
  `quarantined`) by a signed, non-zero `quantity_delta`. Quarantine and release append two rows
  that share a `posting_id`. Mistakes are fixed with a reversal, never an edit.
- The API works out `qty_usable`, `qty_expired`, `alert_level`, `expiring_soon` and
  `allowed_actions`. Show them as given; do not recompute them in the browser.
- Quantities are whole numbers. `5` is accepted; `5.0`, `"5"` and `true` are rejected.

## Requests, shipments and discrepancies

- Every workflow record carries `version` and `allowed_actions`. Show a button only when its
  action is listed; send back the `version` you read. `VERSION_CONFLICT` means someone else
  changed the record: reload and retry. `INVALID_TRANSITION` means the action is not allowed
  in the record's current status.
- Request flow: draft -> submitted -> approved / partially_approved / rejected -> dispatched ->
  received (everything arrived) or discrepancy_open -> closed. A draft or submitted request can
  be cancelled. Review decides every line (`qty_approved` 0 rejects it) and moves no stock.
- Dispatch is all or nothing: the allocations per line must add up to `qty_approved`. Use
  `GET /requests/{id}/allocation-suggestion` for the first-expiry-first-out proposal.
- Receipt counts every shipment line. A shortfall opens one discrepancy per short line; the
  missing quantity stays counted as in transit until the discrepancy is resolved.
- Resolving a discrepancy is `written_off` (recorded as lost), `recovered_to_phc` (PHC stock
  increases) or `recovered_to_store` (store stock increases). The request closes when its last
  discrepancy is resolved.
- Actions with an `Idempotency-Key`: stock postings, reversal, submit, cancel, review,
  dispatch, receipt confirmation and discrepancy resolution. Drafts (create, edit) do not.

## CSV exports, audit and test-only endpoints

- `GET /exports/{resource}.csv` answers `text/csv`. Its example file has
  `"content_type": "text/csv"` and the file text as a string.
- `/test/reset` and `/test/seed` exist only when `APP_ENV` is `test` or `e2e`. They need no
  session and are marked `test-only`. Anywhere else they answer 404.
- `GET /audit` and `GET /admin/reconciliation` are for admins.
