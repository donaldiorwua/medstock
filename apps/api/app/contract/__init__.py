"""The API contract: generated artifacts in docs/contract/ and the tools that guard them.

CONTRACT_VERSION is the version written into openapi.json (info.version). It is separate from
the application version so ordinary releases do not change the contract file.
Bump it by hand: patch for documentation-only changes, minor for additive changes,
major for breaking changes (which also need the `breaking-contract` label and approval).
"""

CONTRACT_VERSION = "0.1.0"
