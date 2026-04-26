from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationPlan:
    allocated: dict[str, int]
    missing: dict[str, int]


@dataclass(frozen=True)
class PlannedOrder:
    allocation: AllocationPlan
    receipt: dict[str, float]
