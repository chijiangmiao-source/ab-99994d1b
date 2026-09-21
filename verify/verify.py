"""End-to-end acceptance for the centrifuge audit console.

Runs as a one-shot Compose service. Every check hits real HTTP endpoints
(through the nginx web tier where stated) — nothing is imported in-process.

Exit code 0 means the whole stack passed acceptance; non-zero means failure.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("API_BASE", "http://api:8000")
WEB = os.environ.get("WEB_BASE", "http://web:80")

failures: list[str] = []
checks_run = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global checks_run
    checks_run += 1
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(f"{name}: {detail}")


def request(method: str, url: str, body=None, timeout: int = 10, expect_status: int | None = None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        status = e.code
    parsed = None
    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        pass
    if expect_status is not None:
        check(f"HTTP {method} {url} status {expect_status}", status == expect_status,
              f"got {status}: {raw[:200]}")
    return status, parsed, raw


def wait_for(url: str, label: str, attempts: int = 30, delay: float = 1.0) -> bool:
    for i in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    print(f"[ready] {label} after {i + 1} attempt(s)")
                    return True
        except Exception:
            pass
        time.sleep(delay)
    return False


# A load whose optimum force^2 is the genuinely irrational number 8-4√2:
# masses 3,5,2 initially at slots 0,1,4. Optimum force (4|F|^2) is 32-16√2,
# i.e. |F|^2 = 8-4√2 — a value a float comparison could only approximate.
TRIPLE = {
    "tubes": [
        {"label": "A", "mass": 3, "current_slot": 0, "allowed_slots": list(range(8))},
        {"label": "B", "mass": 5, "current_slot": 1, "allowed_slots": list(range(8))},
        {"label": "C", "mass": 2, "current_slot": 4, "allowed_slots": list(range(8))},
    ]
}

EQUAL_PAIR = {
    "tubes": [
        {"label": "A", "mass": 10, "current_slot": 0, "allowed_slots": list(range(8))},
        {"label": "B", "mass": 10, "current_slot": 2, "allowed_slots": list(range(8))},
    ]
}

INFEASIBLE = {
    "tubes": [
        {"label": "X", "mass": 1, "current_slot": 0, "allowed_slots": [0, 1]},
        {"label": "Y", "mass": 1, "current_slot": 1, "allowed_slots": [0, 1]},
        {"label": "Z", "mass": 1, "current_slot": 2, "allowed_slots": [0]},
    ]
}

INVALID = {
    "tubes": [
        {"label": "A", "mass": -2, "current_slot": 0, "allowed_slots": [0]},
        {"label": "B", "mass": 1, "current_slot": 0, "allowed_slots": [1]},
    ]
}


def main() -> int:
    print("== waiting for services ==")
    if not wait_for(f"{API}/health", "api"):
        print("FATAL: api never became ready")
        return 2
    if not wait_for(f"{WEB}/web-health", "web"):
        print("FATAL: web never became ready")
        return 2
    check("api reachable", True)
    check("web reachable", True)

    print("== health & meta ==")
    st, health, _ = request("GET", f"{API}/health", expect_status=200)
    check("api health payload", health and health.get("status") == "ok", str(health))
    st, meta, _ = request("GET", f"{API}/api/meta", expect_status=200)
    check("meta advertises Q(sqrt(2))", meta and meta.get("field_ring") == "Q(sqrt(2))", str(meta))
    check("meta slot count 8", meta and meta.get("slot_count") == 8)

    print("== web tier serves SPA and proxies API ==")
    st, _, html = request("GET", f"{WEB}/", expect_status=200)
    check("SPA html served by nginx", 'id="root"' in html, html[:200])
    st, via_web, _ = request("POST", f"{WEB}/api/solve", body=EQUAL_PAIR, expect_status=200)
    check("API reachable through nginx proxy", via_web and via_web.get("feasible") is True)

    print("== exact Q(sqrt(2)) optimum (8-4√2) ==")
    st, r, _ = request("POST", f"{API}/api/solve", body=TRIPLE, expect_status=200)
    check("triple feasible", r and r.get("feasible") is True, str(r)[:200])
    fs = r and r["objective"]["force_squared"]
    check("force^2 exact string is 8-4√2", fs and fs.get("exact") == "8-4√2", str(fs))
    q4 = r["objective"]["force_squared_quadrupled"]
    check("4*force^2 pair is a=32,b=-16",
          q4.get("a") == 32 and q4.get("b") == -16, str(q4))
    check("force^2 fractions are 8/1 and -4/1",
          fs and fs["a_num"] == 8 and fs["a_den"] == 1
          and fs["b_num"] == -4 and fs["b_den"] == 1, str(fs))
    check("not exactly balanced", r and r["objective"]["balanced_exactly"] is False)
    check("minimum moves is 1", r and r["objective"]["moves"] == 1,
          str(r and r["objective"]["moves"]))
    # Exact positivity: (a + b√2)/4 with a=8,b=-4 must be positive but tiny-ish;
    # recompute symbolically: 8 - 4√2 > 0  <=> 2 > √2.
    a, b = fs["a_num"], fs["b_num"]
    positive = a * a > 2 * b * b and a > 0
    check("exact sign positive (a^2 > 2b^2, a>0)", positive, f"a={a}, b={b}")

    print("== tie handling: equal pair, two optimal loadings ==")
    st, r2, _ = request("POST", f"{API}/api/solve", body=EQUAL_PAIR, expect_status=200)
    check("balanced with force 0", r2 and r2["objective"]["force_squared"]["exact"] == "0")
    check("exactly balanced flag", r2 and r2["objective"]["balanced_exactly"] is True)
    check("exactly 2 optimal solutions", r2 and r2["optimal_solution_count"] == 2,
          str(r2 and r2["optimal_solution_count"]))
    rel = r2["relations"]
    check("relations cover both tubes and 8 slots",
          all(len(rel[t]) == 8 for t in ("A", "B")), str(rel))
    statuses = {(t, row["slot"]): row["status"] for t in ("A", "B") for row in rel[t]}
    check("A possible at 0 and 6 only (stay opposite B moved, or move to 6)",
          [statuses[("A", s)] for s in range(8)] ==
          ["possible", "impossible", "impossible", "impossible",
           "impossible", "impossible", "possible", "impossible"], str(statuses))
    check("B possible at 2 and 4 only",
          [statuses[("B", s)] for s in range(8)] ==
          ["impossible", "impossible", "possible", "impossible",
           "possible", "impossible", "impossible", "impossible"], str(statuses))
    # no mandatory cell in this tie
    check("no mandatory cell in this tie",
          all(cell["status"] != "mandatory" for t in ("A", "B") for cell in rel[t]))
    placement = {(p["tube"]): p["slot"] for p in r2["placement"]}
    check("canonical solution is A=0 (empty sorts after labels too)",
          placement == {"A": 0, "B": 4}, str(placement))
    check("canonical key length 8 with empties after labels",
          len(r2["canonical_key"]) == 8 and r2["canonical_key"][0] == [0, "A"]
          and r2["canonical_key"][4] == [0, "B"] and r2["canonical_key"][1] == [1, ""]
          and r2["canonical_key"][6] == [1, ""],
          str(r2["canonical_key"]))

    print("== mandatory relation exists when forced ==")
    forced = {
        "tubes": [
            {"label": "A", "mass": 4, "current_slot": 0, "allowed_slots": [0, 4]},
            {"label": "B", "mass": 4, "current_slot": 4, "allowed_slots": [0, 4]},
        ]
    }
    st, r3, _ = request("POST", f"{API}/api/solve", body=forced, expect_status=200)
    st3 = {(t, row["slot"]): row["status"] for t, rows in r3["relations"].items() for row in rows}
    check("A mandatory at 0", st3[("A", 0)] == "mandatory" and st3[("A", 4)] == "impossible")
    check("B mandatory at 4", st3[("B", 4)] == "mandatory" and st3[("B", 0)] == "impossible")
    check("zero moves when current layout optimal", r3["objective"]["moves"] == 0)

    print("== infeasible: Hall conflict witness ==")
    st, r4, _ = request("POST", f"{API}/api/solve", body=INFEASIBLE, expect_status=200)
    check("infeasible reported", r4 and r4.get("feasible") is False)
    w = r4 and r4.get("conflict_witness")
    check("witness names all 3 tubes", w and set(w["tubes"]) == {"X", "Y", "Z"}, str(w))
    check("witness union is slots [0,1]", w and w["allowed_union"] == [0, 1], str(w))
    check("witness genuinely smaller", w and w["tube_count"] > w["union_size"], str(w))

    print("== validation errors keep uniform shape ==")
    st, r5, _ = request("POST", f"{API}/api/solve", body=INVALID, expect_status=422)
    check("422 carries chinese message + field",
          r5 and isinstance(r5.get("detail"), dict) and "message" in r5["detail"]
          and "field" in r5["detail"], str(r5))
    st, r6, _ = request("POST", f"{API}/api/solve",
                        body={"tubes": [{"label": "S", "mass": 1, "current_slot": 0,
                                         "allowed_slots": [0]}]}, expect_status=422)
    check("single tube rejected (need 2..8)", r6 and "detail" in r6)

    print(f"\n== summary: {checks_run - len(failures)}/{checks_run} checks passed ==")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
