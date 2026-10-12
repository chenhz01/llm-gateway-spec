#!/usr/bin/env python3
"""Self-tests for llm-gateway-spec. Run: python self_test.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def expect(cond, msg="assertion failed"):
    if not cond:
        raise AssertionError(msg)


def ok_request(**over):
    req = {"model": "gpt-mini", "input": "hi"}
    req.update(over)
    return req


def call(req):
    return core.reference_handler(req)


# ---------- functional: validate_request ----------

@case
def t_req_valid():
    expect(core.validate_request(ok_request()) == [], "should be valid")


@case
def t_req_missing_model():
    expect(core.validate_request({"input": "x"}) != [], "missing model")


@case
def t_req_empty_model():
    expect(core.validate_request(ok_request(model="")) != [], "empty model")


@case
def t_req_non_string_model():
    expect(core.validate_request(ok_request(model=7)) != [], "int model")


@case
def t_req_input_int_rejected():
    expect(core.validate_request(ok_request(input=5)) != [], "int input")


@case
def t_req_input_list_of_str_ok():
    expect(core.validate_request(ok_request(input=["a", "b"])) == [],
           "list input ok")


@case
def t_req_input_list_with_int_rejected():
    expect(core.validate_request(ok_request(input=["a", 1])) != [],
           "mixed list rejected")


@case
def t_req_mot_zero_rejected():
    expect(core.validate_request(ok_request(max_output_tokens=0)) != [],
           "mot=0")


@case
def t_req_mot_negative_rejected():
    expect(core.validate_request(ok_request(max_output_tokens=-1)) != [],
           "mot=-1")


@case
def t_req_mot_bool_rejected():
    expect(core.validate_request(ok_request(max_output_tokens=True)) != [],
           "bool mot")


@case
def t_req_mot_string_rejected():
    expect(core.validate_request(ok_request(max_output_tokens="8")) != [],
           "str mot")


@case
def t_req_stream_non_bool_rejected():
    expect(core.validate_request(ok_request(stream="yes")) != [], "stream")


@case
def t_req_non_dict_rejected():
    expect(core.validate_request(["not", "a", "dict"]) != [], "non-dict")


@case
def t_req_unknown_field_tolerated():
    expect(core.validate_request(ok_request(future="x")) == [],
           "unknown fields ignored")


# ---------- functional: validate_success ----------

def ok_body(**over):
    body = {"id": "resp_00000001", "model": "gpt-mini",
            "output": [{"role": "assistant", "content": "ok"}],
            "usage": {"input_tokens": 2, "output_tokens": 3},
            "created": 1728600000}
    body.update(over)
    return body


@case
def t_success_valid():
    expect(core.validate_success(ok_body()) == [], "should be valid")


@case
def t_success_bad_id_prefix():
    expect(core.validate_success(ok_body(id="cmp_1")) != [], "prefix")


@case
def t_success_missing_id():
    b = ok_body()
    del b["id"]
    expect(core.validate_success(b) != [], "missing id")


@case
def t_success_empty_output():
    expect(core.validate_success(ok_body(output=[])) != [], "empty output")


@case
def t_success_wrong_role():
    expect(core.validate_success(
        ok_body(output=[{"role": "system", "content": "x"}])) != [], "role")


@case
def t_success_content_not_string():
    expect(core.validate_success(
        ok_body(output=[{"role": "assistant", "content": 5}])) != [], "content")


@case
def t_success_usage_missing():
    expect(core.validate_success(ok_body(usage=None)) != [], "usage")


@case
def t_success_usage_negative():
    expect(core.validate_success(
        ok_body(usage={"input_tokens": -1, "output_tokens": 0})) != [],
        "negative")


@case
def t_success_usage_bool():
    expect(core.validate_success(
        ok_body(usage={"input_tokens": True, "output_tokens": 0})) != [],
        "bool tokens")


@case
def t_success_usage_float():
    expect(core.validate_success(
        ok_body(usage={"input_tokens": 1.5, "output_tokens": 0})) != [],
        "float tokens")


@case
def t_success_created_string():
    expect(core.validate_success(ok_body(created="yesterday")) != [], "created")


@case
def t_success_non_dict():
    expect(core.validate_success("ok") != [], "non-dict body")


# ---------- functional: validate_error ----------

def ok_error(code="invalid_request", status=400, **over):
    err = {"error": {"code": code, "message": "bad request",
                     "type": "invalid_request_error"}}
    err.update(over)
    return err


@case
def t_error_valid():
    expect(core.validate_error(ok_error(), 400) == [], "should be valid")


@case
def t_error_unknown_code():
    expect(core.validate_error(ok_error(code="boom"), 400) != [], "code")


@case
def t_error_status_mismatch():
    expect(core.validate_error(ok_error(code="rate_limited"), 400) != [],
           "status/code mismatch")


@case
def t_error_missing_message():
    e = ok_error()
    del e["error"]["message"]
    expect(core.validate_error(e, 400) != [], "message")


@case
def t_error_envelope_missing():
    expect(core.validate_error({"oops": 1}, 400) != [], "envelope")


@case
def t_error_codes_table():
    expect(core.ERROR_CODES["invalid_request"] == 400
           and core.ERROR_CODES["model_not_found"] == 404
           and core.ERROR_CODES["rate_limited"] == 429
           and core.ERROR_CODES["upstream_timeout"] == 504
           and core.ERROR_CODES["internal_error"] == 500, "status table")


# ---------- functional: reference handler + suite ----------

@case
def t_ref_minimal_ok():
    st, body = call(ok_request())
    expect(st == 200 and not core.validate_success(body), "st=%s" % st)


@case
def t_ref_unknown_model_404():
    st, body = call(ok_request(model="ghost"))
    expect(st == 404 and not core.validate_error(body, st), "st=%s" % st)


@case
def t_ref_bad_request_400():
    st, body = call({"input": "x"})
    expect(st == 400 and not core.validate_error(body, st), "st=%s" % st)


@case
def t_ref_ids_unique():
    _s, b1 = call(ok_request(input="a"))
    _s, b2 = call(ok_request(input="b"))
    expect(b1["id"] != b2["id"], "ids must differ")


@case
def t_ref_respects_max():
    st, body = call(ok_request(input="a" * 100, max_output_tokens=8))
    expect(body["usage"]["output_tokens"] <= 8, "max not respected")


@case
def t_suite_all_pass_on_reference():
    core.reference_handler.counter = 0
    res = core.conformance_suite(core.reference_handler)
    expect(len(res) == 14, "case count: %d" % len(res))
    failed = [r for r in res if not r["passed"]]
    expect(not failed, "failures: %r" % failed)


@case
def t_suite_shape():
    res = core.conformance_suite(lambda r: (200, ok_body()))
    expect(all(set(r) == {"case", "passed", "detail"} for r in res), "shape")


@case
def t_suite_catches_missing_error_envelope():
    def bad(req):
        return 200, ok_body()
    res = core.conformance_suite(bad)
    expect(not res[1]["passed"], "C02 must fail without error envelope")


@case
def t_suite_catches_wrong_404_status():
    def bad(req):
        if req.get("model") not in core.KNOWN_MODELS:
            return 500, {"error": {"code": "internal_error",
                                   "message": "x", "type": "t"}}
        return 200, ok_body()
    res = core.conformance_suite(bad)
    expect(not res[3]["passed"], "C04 must catch wrong status")


@case
def t_suite_catches_usage_inflation():
    def bad(req):
        st, body = core.reference_handler(req)
        if st == 200:
            body["usage"]["output_tokens"] = 10 ** 9
        return st, body
    res = core.conformance_suite(bad)
    expect(not res[6]["passed"], "C07 must catch usage inflation")


@case
def t_suite_catches_duplicate_ids():
    def bad(req):
        st, body = core.reference_handler(req)
        if st == 200:
            body["id"] = "resp_fixed"
        return st, body
    res = core.conformance_suite(bad)
    expect(not res[7]["passed"], "C08 must catch duplicate ids")


@case
def t_suite_catches_zero_input_tokens():
    def bad(req):
        st, body = core.reference_handler(req)
        if st == 200:
            body["usage"]["input_tokens"] = 0
        return st, body
    res = core.conformance_suite(bad)
    expect(not res[12]["passed"], "C13 must catch zero input tokens")


# ---------- CLI ----------

@case
def t_cli_demo_exit_zero():
    core.reference_handler.counter = 0
    expect(core.main(["demo"]) == 0, "reference must pass")


@case
def t_cli_module_load_failure_exit_two():
    expect(core.main(["conformance", "--module", "Z:/no.py"]) == 2, "exit 2")


@case
def t_cli_missing_func_exit_two():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "gw.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write("x = 1\n")
    expect(core.main(["conformance", "--module", p]) == 2, "exit 2")


@case
def t_cli_user_handler_passes():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "gw.py")
    src = ("import sys, os\n"
           "sys.path.insert(0, os.getcwd())\n"
           "from core import reference_handler as handle\n")
    with open(p, "w", encoding="utf-8") as f:
        f.write(src)
    cwd = os.getcwd()
    os.chdir(d)
    try:
        core.reference_handler.counter = 0
        rc = core.main(["conformance", "--module", p])
    finally:
        os.chdir(cwd)
    expect(rc == 0, "user handler (reference alias) should pass, rc=%s" % rc)


@case
def t_unicode_input_ok():
    st, body = call(ok_request(input="你好 ünïcode ✓"))
    expect(st == 200 and not core.validate_success(body), "unicode failed")


@case
def t_huge_input_ok():
    st, body = call(ok_request(input="x" * 200000))
    expect(st == 200, "huge input failed")


@case
def t_results_json_serializable():
    res = core.conformance_suite(core.reference_handler)
    s = json.dumps(res, ensure_ascii=True, sort_keys=True)
    expect("case" in s, "serialization failed")


def run():
    ok = 0
    for i, fn in enumerate(CASES, 1):
        try:
            fn()
            ok += 1
        except Exception as e:
            print("FAIL %02d %s: %s: %s" % (i, fn.__name__,
                                            type(e).__name__, e))
    total = len(CASES)
    print("SUMMARY: %s %d/%d" % ("PASS" if ok == total else "FAIL", ok, total))
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(run())
