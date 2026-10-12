# llm-gateway-spec

A minimal, dependency-free contract for LLM gateway APIs — one request
shape, one success envelope, one error envelope, a five-code status table —
plus a 14-case conformance suite you can point at any in-process handler
callable. If your facade passes, any client written against this spec works
unchanged. Confidence: high for the contract and suite; the contract itself
is opinionated by design.

as of 2026-10-11

## Problem

Every LLM gateway reinvents its own request/response dialect, so every
client is a snowflake and every provider swap rewrites error handling.
OpenAI-compatible specs exist but are large and SDK-bound; teams that need
a small internal facade lack a checkable contract, so drift is discovered
by broken clients in production. What is needed is a tiny spec plus a test
suite that fails loudly when a handler drifts.

## How it works

- **Request**: `{model: str, input: str|[str], max_output_tokens?: int>=1,
  stream?: bool}`; unknown fields tolerated for forward compatibility.
- **Success envelope**: `{id: "resp_*", model, output: [{role:"assistant",
  content: str}], usage: {input_tokens, output_tokens} (non-negative
  ints), created: int}`.
- **Error envelope**: `{error: {code, message, type}}` where code is one of
  `invalid_request`/`model_not_found`/`rate_limited`/`upstream_timeout`/
  `internal_error`, each pinned to 400/404/429/504/500 respectively.
- **Conformance suite**: 14 cases (C01–C14) covering minimal success,
  each rejection path, status/code agreement, max-token respect, id
  uniqueness, and unknown-field tolerance. Handlers are plain callables
  `handler(request) -> (status, body)` — no sockets involved.
- Exit codes: `0` all cases pass, `1` failures, `2` module load error.

## Quickstart

```bash
python core.py demo                                        # reference (~1 s)
python core.py conformance --module my_gateway.py --func handle  (~1 s)
python self_test.py                                        # ~55 cases (~3 s)
```

## Why not X

| Alternative | Stars (as of 2026-10-11) | How this differs |
| --- | --- | --- |
| [shubham-kumr/project_carbon](https://github.com/shubham-kumr/project_carbon) | 1 | Defines a carbon-aware model *routing* interface; this repo defines the base request/response/error contract any router would sit on, with an executable conformance suite. |
| [brzdev2/system-canvas](https://github.com/brzdev2/system-canvas) | 0 | A general framework for app structure/routing/interfaces; this repo is a narrow, fully test-specified LLM facade contract with zero framework lock-in. |

Only two low-star anchors surfaced in the precheck for this domain as of
2026-10-11; descriptions paraphrased, not copied.

## Minimal Fallback

No suite runner? Paste the `ERROR_CODES` table and the two envelope schemas
into your API README and add one CI assertion per row: call your handler
with a bad request and assert `status == 400` and `body.error.code ==
"invalid_request"`. That is C02 with a screwdriver.

## Design Trade-offs

- Opinionated envelopes over per-provider passthrough: clients get one
  dialect, at the cost of a mapping layer per upstream provider.
- Error-code table pinned to HTTP statuses: predictable, but coarse — rate
  limit *reasons* live in `message`, not new codes.
- In-process handler callables over live HTTP in the suite: fast and
  deterministic; transport behavior (timeouts, TLS) is out of scope.

## Limits & Second-order Effects

- Streaming is declared (`stream: bool`) but chunked-SSE semantics are not
  specified; passing C11 says nothing about your SSE framing.
- Token accounting is validated for *shape*, not truth — usage numbers can
  still be wrong in ways this suite cannot see.
- Second-order effect: a shared error vocabulary makes clients lazy about
  per-provider quirks; when they finally need them, the mapping layer
  surfaces in the client, not the gateway.

## FAQ

**Is this OpenAI-compatible?**
It is shaped in that spirit (familiar field names) but smaller and with its
own error-code table; it is not a drop-in replacement.

**When NOT to use this?**
When you need tool-calling, multimodal inputs, or streaming semantics in
the contract today — this spec deliberately excludes them.

**How do I test a real HTTP gateway?**
Write a 10-line adapter whose `handle(req)` performs the HTTP call and
returns `(status, parsed_json)`; the suite runs unchanged.

## Core Assumptions

- [A1] Text-in / text-out covers the target workloads; multimodality is
  out of scope.
- [A2] Ids are generated per response and unique within a process.
- [A3] Usage numbers are non-negative integers, not floats or strings.

Confidence: contract + suite high; fit for your workload — read "When NOT
to use" first. All claims as of 2026-10-11.

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 55 purpose-built AI-engineering tools across neglected niches.

Related tools: [system-prompt-audit](https://github.com/chenhz01/system-prompt-audit) · [rag-chunk-bench](https://github.com/chenhz01/rag-chunk-bench) · [agent-audit-trail](https://github.com/chenhz01/agent-audit-trail)
