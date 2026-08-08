"""
Pre-trade compliance checks (BRD 5.1.2: "Run pre-trade compliance checks by
clicking a button" / 6.1 step 4).

This is a stand-in rules engine — a real deployment would replace
`StubComplianceEngine` with calls to an actual compliance/risk system, but
should keep the same `check()` interface so order-management logic doesn't
need to change.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Toy restricted list for demo purposes — a real system would source this
# from a compliance data feed, not a hardcoded constant.
RESTRICTED_SYMBOLS = {"XYZ", "BADCO"}
MAX_ORDER_QUANTITY = 100_000


@dataclass
class ComplianceResult:
    passed: bool
    notes: str


class ComplianceEngine(ABC):
    @abstractmethod
    def check(self, *, symbol: str, side: str, quantity: float) -> ComplianceResult:
        ...


class StubComplianceEngine(ComplianceEngine):
    def check(self, *, symbol: str, side: str, quantity: float) -> ComplianceResult:
        if symbol.upper() in RESTRICTED_SYMBOLS:
            return ComplianceResult(passed=False, notes=f"{symbol} is on the restricted list")
        if quantity > MAX_ORDER_QUANTITY:
            return ComplianceResult(
                passed=False,
                notes=f"Quantity {quantity} exceeds max order size of {MAX_ORDER_QUANTITY}",
            )
        return ComplianceResult(passed=True, notes="Passed restricted-list and size checks")


def get_compliance_engine() -> ComplianceEngine:
    return StubComplianceEngine()
