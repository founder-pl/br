"""B+R relief: statutory deduction rate and base per expense.

Taxpayer without Centrum Badawczo-Rozwojowe status (art. 26e PIT / art. 18d CIT):
salaries of people doing B+R work (employment and civil-law contracts) are
deducted at 200%, the other qualifying costs at 100%. Contractors invoicing on
B2B are not personnel costs.

The base is the tax cost: for a VAT payer a purchase invoice counts net of VAT;
salary records keep their gross wage (``gross_amount``), because their
``net_amount`` is take-home pay, not the cost.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

PERSONNEL_CATEGORIES = frozenset({"personnel_employment", "personnel_civil"})
PERSONNEL_RATE = 2.0
OTHER_RATE = 1.0


def statutory_rate(category: Any) -> float:
    """Minimum statutory rate for a B+R category (taxpayer without CBR status)."""
    return PERSONNEL_RATE if category in PERSONNEL_CATEGORIES else OTHER_RATE


def vat_payer() -> bool:
    """Whether purchase invoices are booked net of VAT (BR_VAT_PAYER, default: yes)."""
    return os.environ.get("BR_VAT_PAYER", "1").strip().lower() not in {"0", "false", "no", "nie"}


def deduction_rate(expense: Mapping[str, Any]) -> float:
    """Stored rate, never below the statutory rate of the expense category."""
    try:
        stored = float(expense.get("br_deduction_rate") or 0)
    except (TypeError, ValueError):
        stored = 0.0
    return max(stored, statutory_rate(expense.get("br_category")))


def deduction_base(expense: Mapping[str, Any], is_vat_payer: bool | None = None) -> float:
    """Tax cost the rate applies to: net for a VAT payer's invoices, gross wage for salaries."""
    gross = float(expense.get("gross_amount") or 0)
    if expense.get("br_category") in PERSONNEL_CATEGORIES:
        return gross
    payer = vat_payer() if is_vat_payer is None else is_vat_payer
    net = expense.get("net_amount")
    if payer and net not in (None, ""):
        return float(net)
    return gross


def deduction_amount(expense: Mapping[str, Any], is_vat_payer: bool | None = None) -> float:
    """B+R deduction for one qualified expense."""
    return deduction_base(expense, is_vat_payer) * deduction_rate(expense)
