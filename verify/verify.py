#!/usr/bin/env python3
"""一次性验收服务：对真实运行中的 API（直连）与 Web 反向代理（全链路）
执行接口验收，全部通过以退出码 0 结束，否则退出码 1。

期望值由本脚本内置的独立精确枚举（Q(√2) 整数运算）重新计算，
不与被测服务共享任何代码。
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from functools import cmp_to_key
from itertools import permutations

API = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
WEB = os.environ.get("WEB_BASE", "http://127.0.0.1:8080").rstrip("/")
WAIT_SECONDS = float(os.environ.get("VERIFY_WAIT", "120"))

# 2*(cos, sin) 的 (ax, bx, ay, by)：2cos = ax + bx·√2，2sin = ay + by·√2
SLOT_VEC2 = (
    (2, 0, 0, 0), (0, 1, 0, 1), (0, 0, 2, 0), (0, -1, 0, 1),
    (-2, 0, 0, 0), (0, -1, 0, -1), (0, 0, -2, 0), (0, 1, 0, -1),
)

FAILURES = []
CHECKS = 0


def check(name, cond, detail=""):
    global CHECKS
    CHECKS += 1
    if cond:
        print(f"  PASS {name}")
    else:
        FAILURES.append(name)
        print(f"  FAIL {name}" + (f" :: {detail}" if detail else ""))


# ---------------- 独立精确参照实现 ----------------

def cmp_pq(p1, q1, p2, q2):
    dp, dq = p1 - p2, q1 - q2
    if dp == 0:
        return (dq > 0) - (dq < 0)
    if dq == 0:
        return (dp > 0) - (dp < 0)
    if (dp > 0) == (dq > 0):
        return 1 if dp > 0 else -1
    lhs, rhs = dp * dp, 2 * dq * dq
    if lhs == rhs:
        return 0
    if dp > 0:
        return 1 if lhs > rhs else -1
    return 1 if lhs < rhs else -1


def _entry_cmp(a, b):
    c = cmp_pq(a[0][0], a[0][1], b[0][0], b[0][1])
    return c if c else a[1] - b[1]


_ENTRY_KEY = cmp_to_key(_entry_cmp)


def reference_solve(tubes):
    """返回 ((P,Q), moves, canonical_assign, relations, optimal_count) 或 None。"""
    n = len(tubes)
    entries = []
    for perm in permutations(range(8), n):
        if any(perm[i] not in tubes[i]["allowed_slots"] for i in range(n)):
            continue
        ax = bx = ay = by = 0
        for i, s in enumerate(perm):
            va, vb, vc, vd = SLOT_VEC2[s]
            m = tubes[i]["mass"]
            ax += m * va
            bx += m * vb
            ay += m * vc
            by += m * vd
        p = ax * ax + 2 * bx * bx + ay * ay + 2 * by * by
        q = 2 * (ax * bx + ay * by)
        moves = sum(perm[i] != tubes[i]["current_slot"] for i in range(n))
        entries.append(((p, q), moves, perm))
    if not entries:
        return None

    best = min(entries, key=_ENTRY_KEY)
    bpq, bmoves = best[0], best[1]
    optimal = [e for e in entries
               if cmp_pq(e[0][0], e[0][1], bpq[0], bpq[1]) == 0 and e[1] == bmoves]

    def seq_key(perm):
        owner = [None] * 8
        for i, s in enumerate(perm):
            owner[s] = tubes[i]["id"]
        return tuple((0, t) if t is not None else (1, "") for t in owner)

    canonical = min((e[2] for e in optimal), key=seq_key)
    total = len(optimal)
    relations = {}
    for i in range(n):
        for s in range(8):
            cnt = sum(1 for e in optimal if e[2][i] == s)
            relations[(tubes[i]["id"], s)] = (
                "necessary" if cnt == total else "optional" if cnt else "impossible"
            )
    return bpq, bmoves, canonical, relations, total


# ---------------- HTTP 工具 ----------------

def http(method, url, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            return resp.status, body, parse_json(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return e.code, body, parse_json(body)
    except OSError as e:
        return None, str(e), None


def parse_json(body):
    try:
        return json.loads(body)
    except Exception:
        return None


def wait_ready():
    deadline = time.time() + WAIT_SECONDS
    targets = {"api": f"{API}/healthz", "web": f"{WEB}/healthz"}
    ready = set()
    while time.time() < deadline and ready != set(targets):
        for name, url in targets.items():
            if name in ready:
                continue
            try:
                with urllib.request.urlopen(url, timeout=3) as resp:
                    if resp.status == 200:
                        ready.add(name)
            except OSError:
                pass
        if ready != set(targets):
            time.sleep(1)
    return ready == set(targets)


# ---------------- 验收用例 ----------------

def check_optimal_case(name, base, tubes):
    print(f"[case] {name} (via {base})")
    status, _, body = http("POST", f"{base}/api/v1/balance", {"tubes": tubes})
    check("HTTP 200 且 status=optimal",
          status == 200 and isinstance(body, dict) and body.get("status") == "optimal",
          f"status={status} body={str(body)[:200]}")
    if not (status == 200 and isinstance(body, dict) and body.get("status") == "optimal"):
        return

    ref = reference_solve(tubes)
    (p, q), moves, canonical, relations, total = ref

    rs = body["objectives"]["resultant_squared"]
    check("合力平方精确值 (P,Q,scale)",
          rs["p"] == p and rs["q"] == q and rs["scale"] == 4,
          f"期望 P={p} Q={q}，实得 {rs}")
    check("最少移动数", body["objectives"]["moves"] == moves,
          f"期望 {moves}，实得 {body['objectives']['moves']}")
    check("同优方案数", body["objectives"]["optimal_count"] == total,
          f"期望 {total}，实得 {body['objectives']['optimal_count']}")

    got = {a["tube"]: a["slot"] for a in body["assignment"]}
    want = {tubes[i]["id"]: canonical[i] for i in range(len(tubes))}
    check("规范解槽位分配", got == want, f"期望 {want}，实得 {got}")

    got_rel = {(r["tube"], r["slot"]): r["status"] for r in body["relations"]}
    bad = {k: (relations[k], got_rel.get(k)) for k in relations
           if got_rel.get(k) != relations[k]}
    check("必然/可选/不可能关系标注", not bad, f"不一致: {bad}")

    # 自洽性：返回的分配本身可行，且其精确合力与报告一致
    seen = set()
    feasible = True
    ax = bx = ay = by = 0
    for a in body["assignment"]:
        t = next(t for t in tubes if t["id"] == a["tube"])
        if a["slot"] in seen or a["slot"] not in t["allowed_slots"]:
            feasible = False
        seen.add(a["slot"])
        va, vb, vc, vd = SLOT_VEC2[a["slot"]]
        ax += t["mass"] * va
        bx += t["mass"] * vb
        ay += t["mass"] * vc
        by += t["mass"] * vd
    check("返回分配可行（允许槽且不复用）", feasible)
    check("返回分配复算的 (P,Q) 与报告一致",
          ax * ax + 2 * bx * bx + ay * ay + 2 * by * by == p
          and 2 * (ax * bx + ay * by) == q)
    fx = body["force"]["x"]
    fy = body["force"]["y"]
    check("力分量系数自洽",
          (fx["a"], fx["b"], fy["a"], fy["b"]) == (ax, bx, ay, by),
          f"期望 {(ax, bx, ay, by)}，实得 {(fx, fy)}")
    slot_map = {s["slot"]: s["tube"] for s in body["slots"]}
    check("槽位图与分配一致",
          all(slot_map[s] == t for t, s in got.items())
          and all(slot_map[s] is None for s in range(8) if s not in got.values()))


def check_infeasible_case(name, base, tubes):
    print(f"[case] {name} (via {base})")
    status, _, body = http("POST", f"{base}/api/v1/balance", {"tubes": tubes})
    check("HTTP 200 且 status=infeasible",
          status == 200 and isinstance(body, dict) and body.get("status") == "infeasible",
          f"status={status} body={str(body)[:200]}")
    if not (status == 200 and isinstance(body, dict) and body.get("status") == "infeasible"):
        return
    w = body.get("witness", {})
    tset = set(w.get("tubes", []))
    union = set(w.get("allowed_union", []))
    ids = {t["id"] for t in tubes}
    check("见证样管属于输入且非空", 0 < len(tset) <= len(ids) and tset <= ids,
          f"witness={w}")
    actual_union = set()
    for t in tubes:
        if t["id"] in tset:
            actual_union |= set(t["allowed_slots"])
    check("见证并集等于这些样管允许槽的真实并集", union == actual_union,
          f"期望 {sorted(actual_union)}，实得 {sorted(union)}")
    check("霍尔冲突成立：|并集| < |样管集|", len(union) < len(tset),
          f"|union|={len(union)} |tubes|={len(tset)}")
    check("见证计数一致",
          w.get("tube_count") == len(tset) and w.get("slot_count") == len(union))
    check("参照实现确认无可行装载", reference_solve(tubes) is None)


def check_validation(name, base, payload):
    print(f"[case] {name}")
    status, _, body = http("POST", f"{base}/api/v1/balance", payload)
    check("非法输入返回 422", status == 422, f"status={status} body={str(body)[:160]}")
    check("错误响应含 detail", isinstance(body, dict) and "detail" in body)


def main():
    print(f"API_BASE={API}  WEB_BASE={WEB}")
    if not wait_ready():
        print("FAIL: 服务在限定时间内未就绪")
        return 1

    print("[case] 健康检查")
    s, _, b = http("GET", f"{API}/healthz")
    check("API /healthz", s == 200 and isinstance(b, dict) and b.get("status") == "ok")
    s, _, _ = http("GET", f"{WEB}/healthz")
    check("Web /healthz", s == 200)
    s, raw, _ = http("GET", f"{WEB}/")
    check("Web 前端页面可访问", s == 200 and "root" in raw)
    s, _, b = http("GET", f"{API}/api/v1/meta")
    check("元信息：8 槽、2-8 管",
          s == 200 and b.get("slot_count") == 8
          and b.get("min_tubes") == 2 and b.get("max_tubes") == 8)

    # 1) 经 Web 反向代理的全链路最优解
    check_optimal_case("四管基础配平（全链路）", WEB, [
        {"id": "A", "mass": 12, "current_slot": 0, "allowed_slots": [0, 1, 4, 5]},
        {"id": "B", "mass": 12, "current_slot": 4, "allowed_slots": [0, 4]},
        {"id": "C", "mass": 7, "current_slot": 2, "allowed_slots": [2, 3, 6, 7]},
        {"id": "D", "mass": 7, "current_slot": 6, "allowed_slots": [2, 6]},
    ])

    # 2) 同优规范解：两种放法合力、移动数完全相同
    check_optimal_case("同优规范解与可选关系", API, [
        {"id": "Y", "mass": 5, "current_slot": 0, "allowed_slots": [2, 6]},
        {"id": "Z", "mass": 5, "current_slot": 1, "allowed_slots": [2, 6]},
    ])

    # 3) 八管填满转子
    check_optimal_case("八管满转子", API, [
        {"id": f"T{i}", "mass": 3 + (i % 3), "current_slot": i,
         "allowed_slots": list(range(8))}
        for i in range(8)
    ])

    # 4) Pell 近邻：float64 无法区分的合力比较（精确性验收）
    check_optimal_case("Pell 近邻精确性（浮点必错）", API, [
        {"id": "D", "mass": 500000, "current_slot": 4, "allowed_slots": [0, 4]},
        {"id": "R1", "mass": 27304197, "current_slot": 1, "allowed_slots": [1]},
        {"id": "R2", "mass": 27304196, "current_slot": 7, "allowed_slots": [7]},
        {"id": "R3", "mass": 38613965, "current_slot": 5, "allowed_slots": [4]},
        {"id": "R4", "mass": 3, "current_slot": 2, "allowed_slots": [2]},
    ])

    # 5) 大质量随机形态（精确交叉验证）
    check_optimal_case("大质量多管", API, [
        {"id": "M1", "mass": 1000003, "current_slot": 0, "allowed_slots": [0, 1, 3, 4]},
        {"id": "M2", "mass": 999983, "current_slot": 2, "allowed_slots": [2, 5, 6]},
        {"id": "M3", "mass": 1000009, "current_slot": 4, "allowed_slots": [0, 4, 7]},
        {"id": "M4", "mass": 999991, "current_slot": 6, "allowed_slots": [1, 2, 6]},
    ])

    # 6) 不可行：3 管竞争 2 槽
    check_infeasible_case("霍尔冲突：3 管 2 槽", WEB, [
        {"id": "A", "mass": 4, "current_slot": 0, "allowed_slots": [1, 2]},
        {"id": "B", "mass": 4, "current_slot": 3, "allowed_slots": [1, 2]},
        {"id": "C", "mass": 4, "current_slot": 4, "allowed_slots": [1, 2]},
    ])

    # 7) 不可行：空允许集
    check_infeasible_case("霍尔冲突：空允许槽", API, [
        {"id": "A", "mass": 4, "current_slot": 0, "allowed_slots": []},
        {"id": "B", "mass": 4, "current_slot": 1, "allowed_slots": [1, 2]},
    ])

    # 8) 输入校验
    check_validation("少于一管", API, {"tubes": [
        {"id": "A", "mass": 1, "current_slot": 0, "allowed_slots": [0]}]})
    check_validation("超过八管", API, {"tubes": [
        {"id": f"T{i}", "mass": 1, "current_slot": i % 8 if i < 8 else 0,
         "allowed_slots": [0]} for i in range(9)]})
    check_validation("标识重复", API, {"tubes": [
        {"id": "A", "mass": 1, "current_slot": 0, "allowed_slots": [0]},
        {"id": "A", "mass": 1, "current_slot": 1, "allowed_slots": [1]}]})
    check_validation("当前槽位冲突", API, {"tubes": [
        {"id": "A", "mass": 1, "current_slot": 0, "allowed_slots": [0]},
        {"id": "B", "mass": 1, "current_slot": 0, "allowed_slots": [1]}]})
    check_validation("质量非正", API, {"tubes": [
        {"id": "A", "mass": 0, "current_slot": 0, "allowed_slots": [0]},
        {"id": "B", "mass": 1, "current_slot": 1, "allowed_slots": [1]}]})
    check_validation("槽位越界", API, {"tubes": [
        {"id": "A", "mass": 1, "current_slot": 8, "allowed_slots": [0]},
        {"id": "B", "mass": 1, "current_slot": 1, "allowed_slots": [1]}]})
    check_validation("允许槽越界", API, {"tubes": [
        {"id": "A", "mass": 1, "current_slot": 0, "allowed_slots": [-1]},
        {"id": "B", "mass": 1, "current_slot": 1, "allowed_slots": [1]}]})

    print(f"\n{'=' * 50}")
    if FAILURES:
        print(f"验收失败：{len(FAILURES)}/{CHECKS} 项未通过 -> {FAILURES}")
        return 1
    print(f"验收通过：{CHECKS} 项全部成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())
