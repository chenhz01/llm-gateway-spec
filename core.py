#!/usr/bin/env python3
"""llm-gateway-spec: a minimal unified LLM gateway contract plus an
in-process conformance test suite.

Defines the request shape, success envelope, error envelope and status-code
table, and validates any handler — a plain Python callable taking a request
dict and returning (status, body) — against 14 conformance cases. No network;
handlers run in-process. Pure standard library.
"""
import argparse
import importlib.util
import json
import sys

ERROR_CODES = {
    "invalid_request": 400,
    "model_not_found": 404,
    "rate_limited": 429,
    "upstream_timeout": 504,
    "internal_error": 500,
}


# ---------------- validators ----------------

def validate_request(req):
    """Return a list of request errors (empty = valid)."""
    if not isinstance(req, dict):
        return ["request must be a JSON object"]
    errs = []
    model = req.get("model")
    if not isinstance(model, str) or not model:
        errs.append("model must be a non-empty string")
    inp = req.get("input")
    if not (isinstance(inp, str) or
            (isinstance(inp, list) and all(isinstance(x, str) for x in inp))):
        errs.append("input must be a string or list of strings")
    elif inp == "" or inp == []:
        errs.append("input must not be empty")
    mot = req.get("max_output_tokens")
    if mot is not None and (isinstance(mot, bool) or
                            not isinstance(mot, int) or mot < 1):
        errs.append("max_output_tokens must be a positive integer")
    if "stream" in req and not isinstance(req["stream"], bool):
        errs.append("stream must be a boolean")
    return errs


def validate_success(body):
    """Return a list of success-envelope errors (empty = valid)."""
    if not isinstance(body, dict):
        return ["success body must be an object"]
    errs = []
    rid = body.get("id")
    if not isinstance(rid, str) or not rid.startswith("resp_"):
        errs.append("id must be a string with prefix 'resp_'")
    if not isinstance(body.get("model"), str) or not body.get("model"):
        errs.append("model must be a non-empty string")
    out = body.get("output")
    if not (isinstance(out, list) and out and all(
            isinstance(o, dict) and o.get("role") == "assistant"
            and isinstance(o.get("content"), str) for o in out)):
        errs.append("output must be a non-empty list of "
                    "{role:'assistant', content:str}")
    usage = body.get("usage")
    if not isinstance(usage, dict):
        errs.append("usage must be an object")
    else:
        for k in ("input_tokens", "output_tokens"):
            v = usage.get(k)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                errs.append("usage.%s must be a non-negative integer" % k)
    created = body.get("created")
    if isinstance(created, bool) or not isinstance(created, int):
        errs.append("created must be an integer timestamp")
    return errs


def validate_error(body, status):
    """Return a list of error-envelope errors (empty = valid)."""
    if not isinstance(body, dict):
        return ["error body must be an object"]
    err = body.get("error")
    if not isinstance(err, dict):
        return ["error envelope missing"]
    errs = []
    code = err.get("code")
    if code not in ERROR_CODES:
        errs.append("unknown error code %r" % (code,))
    elif ERROR_CODES[code] != status:
        errs.append("status %d does not match code %r (expected %d)"
                    % (status, code, ERROR_CODES[code]))
    if not isinstance(err.get("message"), str) or not err.get("message"):
        errs.append("error.message must be a non-empty string")
    return errs


# ---------------- reference handler ----------------

KNOWN_MODELS = ("gpt-mini", "gpt-large")


def reference_handler(req):
    errs = validate_request(req)
    if errs:
        return 400, {"error": {"code": "invalid_request",
                               "message": "; ".join(errs),
                               "type": "invalid_request_error"}}
    if req["model"] not in KNOWN_MODELS:
        return 404, {"error": {"code": "model_not_found",
                               "message": "unknown model %r" % req["model"],
                               "type": "invalid_request_error"}}
    mot = req.get("max_output_tokens", 64)
    text = "ok:" + (req["input"] if isinstance(req["input"], str)
                    else " ".join(req["input"]))
    text = text[:mot]
    body = {"id": "resp_%08x" % reference_handler.counter,
            "model": req["model"],
            "output": [{"role": "assistant", "content": text}],
            "usage": {"input_tokens": len(str(req["input"])),
                      "output_tokens": len(text)},
            "created": 1728600000}
    reference_handler.counter += 1
    return 200, body


reference_handler.counter = 0


# ---------------- conformance suite ----------------

def conformance_suite(handler):
    """Run all conformance cases against handler(req) -> (status, body)."""
    results = []

    def add(name, passed, detail=""):
        results.append({"case": name, "passed": bool(passed),
                        "detail": str(detail)})

    st, body = handler({"model": "gpt-mini", "input": "hi"})
    errs = [] if st == 200 else ["status %s" % st]
    if st == 200:
        errs = validate_success(body)
    add("C01_minimal_request", not errs, errs)

    st, body = handler({"input": "hi"})
    errs = validate_error(body, st) if st != 200 else ["should be 400"]
    add("C02_missing_model_rejected", st == 400 and not errs, errs)

    st, body = handler({"model": "gpt-mini", "input": ""})
    errs = validate_error(body, st) if st != 200 else ["empty input must be rejected"]
    add("C03_empty_input_rejected", st == 400 and not errs, errs)

    st, body = handler({"model": "no-such-model", "input": "hi"})
    errs = validate_error(body, st) if st != 404 else validate_error(body, st)
    add("C04_unknown_model_404", st == 404 and not errs, errs)

    st, body = handler({"model": "gpt-mini", "input": "hi",
                        "max_output_tokens": 0})
    errs = validate_error(body, st) if st != 200 else ["mot=0 must be rejected"]
    add("C05_max_output_tokens_zero_rejected", st == 400 and not errs, errs)

    st, body = handler({"model": "gpt-mini", "input": "hi",
                        "max_output_tokens": -5})
    errs = validate_error(body, st) if st != 200 else ["negative mot must be rejected"]
    add("C06_max_output_tokens_negative_rejected", st == 400 and not errs, errs)

    st, body = handler({"model": "gpt-mini", "input": "hi",
                        "max_output_tokens": 8})
    detail = "ok"
    ok = st == 200 and not validate_success(body)
    if ok and body["usage"]["output_tokens"] > 8:
        ok, detail = False, "output_tokens %d exceeds max 8" % body["usage"]["output_tokens"]
    add("C07_output_respects_max", ok, detail)

    _s1, b1 = handler({"model": "gpt-mini", "input": "a"})
    _s2, b2 = handler({"model": "gpt-mini", "input": "b"})
    add("C08_id_uniqueness", b1.get("id") != b2.get("id"),
        "ids: %r vs %r" % (b1.get("id"), b2.get("id")))

    st, body = handler({"model": "gpt-mini", "input": "hi",
                        "unknown_future_field": {"x": 1}})
    add("C09_unknown_field_tolerated", st == 200 and not validate_success(body),
        "status %s" % st)

    st, body = handler({"model": "gpt-mini", "input": ["a", "b"]})
    add("C10_list_input_ok", st == 200 and not validate_success(body),
        "status %s" % st)

    st, body = handler({"model": "gpt-mini", "input": "hi", "stream": False})
    add("C11_stream_false_ok", st == 200 and not validate_success(body),
        "status %s" % st)

    st, body = handler({"model": "", "input": "hi"})
    errs = validate_error(body, st) if st != 200 else ["empty model must be rejected"]
    add("C12_empty_model_rejected", st == 400 and not errs, errs)

    st, body = handler({"model": "gpt-mini", "input": "hello world"})
    ok = (st == 200 and not validate_success(body)
          and body["usage"]["input_tokens"] > 0)
    add("C13_input_tokens_positive_for_text", ok, "usage: %r"
        % (body.get("usage") if isinstance(body, dict) else body))

    st, body = handler({"model": "gpt-mini", "input": "hi"})
    ok = (st == 200 and not validate_success(body)
          and isinstance(body["output"][0].get("content"), str)
          and body["output"][0]["content"] != "")
    add("C14_content_nonempty_string", ok, "content: %r"
        % (body.get("output") if isinstance(body, dict) else body))

    return results


# ---------------- CLI ----------------

def _load_handler(module_path, func_name):
    spec = importlib.util.spec_from_file_location("user_gateway_mod",
                                                  module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, func_name)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="llm-gateway-spec",
        description="Run the LLM gateway conformance suite (in-process, "
                    "no network).")
    sub = parser.add_subparsers(dest="cmd")
    p_demo = sub.add_parser("demo", help="run suite on the reference handler")
    p_check = sub.add_parser("conformance", help="run suite on your handler")
    p_check.add_argument("--module", required=True, help="path to .py file")
    p_check.add_argument("--func", default="handle",
                         help="handler function name (default: handle)")
    args = parser.parse_args(argv)

    if args.cmd == "conformance":
        try:
            handler = _load_handler(args.module, args.func)
        except Exception as e:  # noqa: BLE001
            print("error: cannot load handler module: %s" % e, file=sys.stderr)
            return 2
    else:
        handler = reference_handler
    results = conformance_suite(handler)
    print(json.dumps(results, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
