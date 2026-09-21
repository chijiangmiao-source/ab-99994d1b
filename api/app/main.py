"""FastAPI 入口：健康检查、元信息、配平计算。"""

from __future__ import annotations

import math

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import BalanceRequest
from .solver import (
    SLOT_COUNT,
    Tube,
    conflict_witness,
    format_resultant,
    solve,
)

app = FastAPI(
    title="Centrifuge Balance Audit API",
    version="1.0.0",
    description="八槽离心机转子全局配平审计：Q(√2) 精确比较合力平方，"
                "先最小化合力、再最少移动样管，同优取规范解并给出"
                "必然/可选/不可能管槽关系；不可行时返回霍尔冲突见证。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/meta")
def meta() -> dict:
    return {
        "slot_count": SLOT_COUNT,
        "min_tubes": 2,
        "max_tubes": 8,
        "objectives": [
            "minimize |F|² exactly in Q(√2)",
            "minimize moved tubes",
            "canonical slot-id sequence (empty sorts after any id)",
        ],
    }


def _approx(p: int, q: int, scale: int):
    """仅供展示的近似值；比较逻辑从不使用浮点。过大时返回 None。"""
    try:
        return (p + q * math.sqrt(2.0)) / scale
    except OverflowError:
        return None


@app.post("/api/v1/balance")
def balance(req: BalanceRequest) -> dict:
    tubes = [
        Tube(t.id, t.mass, t.current_slot, tuple(sorted(set(t.allowed_slots))))
        for t in req.tubes
    ]
    n = len(tubes)

    witness = conflict_witness(tubes)
    if witness is not None:
        tset, union = witness
        return {
            "status": "infeasible",
            "witness": {
                "tubes": sorted(tubes[i].tid for i in tset),
                "allowed_union": union,
                "tube_count": len(tset),
                "slot_count": len(union),
                "explanation": (
                    f"{len(tset)} 支样管的允许槽位并集只有 {len(union)} 个，"
                    "霍尔条件不满足，无可行装载"
                ),
            },
        }

    res = solve(tubes)
    assert res is not None, "匹配判定可行但枚举无解，内部不一致"

    owner: dict[int, str] = {}
    for i, s in enumerate(res.assignment):
        owner[s] = tubes[i].tid

    assignment = [
        {
            "tube": tubes[i].tid,
            "mass": tubes[i].mass,
            "slot": res.assignment[i],
            "current_slot": tubes[i].current_slot,
            "moved": res.assignment[i] != tubes[i].current_slot,
        }
        for i in range(n)
    ]
    slots = [
        {"slot": s, "tube": owner.get(s)}
        for s in range(SLOT_COUNT)
    ]
    relations = [
        {
            "tube": tubes[i].tid,
            "slot": s,
            "allowed": s in tubes[i].allowed,
            "status": res.relations[i][s],
        }
        for i in range(n)
        for s in range(SLOT_COUNT)
    ]

    ax, bx, ay, by = res.force2
    return {
        "status": "optimal",
        "objectives": {
            "resultant_squared": {
                "p": res.p,
                "q": res.q,
                "scale": res.scale,
                "exact": format_resultant(res.p, res.q, res.scale),
                "approx": _approx(res.p, res.q, res.scale),
            },
            "moves": res.moves,
            "optimal_count": res.optimal_count,
        },
        "force": {
            "x": {"a": ax, "b": bx, "scale": 2},
            "y": {"a": ay, "b": by, "scale": 2},
        },
        "assignment": assignment,
        "slots": slots,
        "relations": relations,
    }
