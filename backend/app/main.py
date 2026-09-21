"""FastAPI application for the centrifuge balance audit console."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .solver import SLOT_COUNT, ValidationError, solve, validate_input

API_VERSION = "1.0.0"

app = FastAPI(
    title="高速离心机全局配平审计台 API",
    version=API_VERSION,
    description="基于 Q(√2) 精确运算的八槽转子全局最优装载计算。",
)

# The web container serves the SPA and reverse-proxies /api to this service;
# CORS is kept open so the page can also call the API directly in dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "api", "version": API_VERSION, "slot_count": SLOT_COUNT}


@app.get("/api/meta")
def meta() -> Dict[str, Any]:
    return {
        "slot_count": SLOT_COUNT,
        "min_tubes": 2,
        "max_tubes": SLOT_COUNT,
        "field_ring": "Q(sqrt(2))",
        "objectives": [
            "最小化合力平方（Q(√2) 精确比较）",
            "在合力最优的方案中最少化移动样管数",
            "同优方案按槽位 0..7 上的标识序列取规范解，空槽排在所有标识之后",
        ],
        "relation_statuses": ["mandatory", "possible", "impossible"],
    }


@app.post("/api/solve")
async def solve_endpoint(request: Request) -> Dict[str, Any]:
    # Validate the raw body ourselves so every error has a uniform shape
    # {message, field} with Chinese explanations; pydantic never pre-empts us.
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"message": "请求体不是合法 JSON", "field": None})
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail={"message": "请求体必须是对象", "field": None})
    try:
        tubes = validate_input(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": exc.message, "field": exc.field})
    return solve(tubes)
