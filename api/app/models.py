"""请求模型与批次校验（2-8 管、标识唯一、质量正整数、当前槽位互异）。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLOT_MIN = 0
SLOT_MAX = 7


class TubeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=32, description="样管标识，批次内唯一")
    mass: int = Field(gt=0, description="质量，正整数")
    current_slot: int = Field(ge=SLOT_MIN, le=SLOT_MAX, description="当前槽位 0-7")
    allowed_slots: list[int] = Field(default_factory=list, description="允许槽位子集")

    @field_validator("allowed_slots")
    @classmethod
    def _slots_in_range(cls, v: list[int]) -> list[int]:
        for s in v:
            if not (SLOT_MIN <= s <= SLOT_MAX):
                raise ValueError(f"允许槽位 {s} 超出 0-7 范围")
        return v


class BalanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tubes: list[TubeIn] = Field(min_length=2, max_length=8)

    @model_validator(mode="after")
    def _check_batch(self) -> "BalanceRequest":
        ids = [t.id for t in self.tubes]
        if len(set(ids)) != len(ids):
            raise ValueError("样管标识必须唯一")
        slots = [t.current_slot for t in self.tubes]
        if len(set(slots)) != len(slots):
            raise ValueError("各样管的当前槽位必须互不相同")
        return self
