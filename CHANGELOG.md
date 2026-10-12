# Changelog — llm-gateway-spec

All notable changes. Format based on Keep a Changelog; versioning: SemVer.

## [0.1.1] - 2026-10-12

### Added
- MIT LICENSE file (was missing from the release candidate).

### Fixed
- Empty-input gap in `validate_request`: `{"input": ""}` (and empty list form) previously passed validation, so the reference handler returned 200 where the C03 conformance case requires 400. Empty input is now rejected as `input must not be empty`. This single fix cleared three suite failures (C03, and the two tests that run the full suite on the reference handler).

### Verified
- Full release audit: `python self_test.py` → `SUMMARY: PASS 51/51` (51 cases across functional, exception/CLI, and extreme-edge tiers; includes the 14-case conformance suite passing on the reference handler).

## [0.1.0] - 2026-10-11

### Added
- Unified LLM gateway contract: request shape (model/input/max_output_tokens/stream), success envelope (id/model/output/usage/created), error envelope (code/message/type), and status-code table (200/400/404).
- `validate_request` / `validate_success` / `validate_error` pure functions shared by handlers and the test suite.
- 14-case in-process conformance suite runnable against any `(request dict) -> (status, body)` handler: minimal request, missing model, empty input, unknown model, mot=0, streaming flag, envelope shape, error codes, and more.
- Reference handler implementing the full contract; `demo` command runs the suite on it.
- CLI: `conformance --module F --handler NAME` loads your handler module and runs the suite; exit 0 all-pass / 1 failures / 2 load error.
- Self-test suite: 51 cases across functional, exception/CLI, and extreme-edge tiers.
