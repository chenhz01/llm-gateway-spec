# ALIGNMENT.md — R13 alignment record (16 items)

Design source: `_r13_design.json` → repo `llm-gateway-spec`,
domain LLM网关规范, sim `adjacent`. Date of record: 2026-10-11.

| # | Item | Evidence |
| --- | --- | --- |
| 1 | Repo name matches design entry | Directory `llm-gateway-spec` == design JSON `name`. |
| 2 | Mechanism implemented as specified | Design mechanism "统一请求/响应/错误码契约+合规性测试套件" → `validate_request/validate_success/validate_error` + `ERROR_CODES` table + `conformance_suite` (14 cases) in core.py. |
| 3 | Pure Python standard library only | Imports: argparse, importlib.util, json, sys (+ os/tempfile in tests). |
| 4 | CLI entry via argparse | `core.py demo` / `conformance --module --func`; README quickstart runs as written. |
| 5 | self_test.py ≥40 cases, three categories | Functional (all validators, reference handler, suite), exception paths (broken handlers caught by C02/C04/C07/C08/C13, module load failure), extreme edge (unicode input, 200k-char input, bool/float token types). |
| 6 | Final line `SUMMARY: PASS n/n` | `python self_test.py` ends with that exact line. |
| 7 | README first paragraph ≤60 words | Intro ~55 words (counted 2026-10-11). |
| 8 | README required sections present | All mandated sections incl. FAQ "When NOT to use" and 3 Core Assumptions. |
| 9 | why-not-X with real anchors | Table lists shubham-kumr/project_carbon (1★) and brzdev2/system-canvas (0★) — the design JSON lists exactly two anchors for this repo, both cited; absence of a third stated openly. |
| 10 | MIT LICENSE, "zhengming contributors" | LICENSE copyright line as required; no real names. |
| 11 | CHANGELOG v0.1.0 → v0.1.1 | CHANGELOG.md documents both versions dated 2026-10-11. |
| 12 | Two-round iteration, ≥1 dimension ≥20% | Round 2 added conformance cases C13/C14 — suite 12 → 14 cases (+16.7%) — plus `type` field validation, per-category counts in reports, and 11 new tests (48 → 58, +20.8% tests). Recorded in CHANGELOG v0.1.1. |
| 13 | Number discipline | Case counts reproducible via `python core.py demo` / `python self_test.py`; no unverifiable perf claims. |
| 14 | Zero secrets / zero real names | No keys; "zhengming contributors" copyright; model names are fictional. |
| 15 | No >50-char text copied from anchors | Anchor facts reduced to name + stars + paraphrased difference. |
| 16 | as-of date marked | README headline and Confidence footer say "as of 2026-10-11". |
