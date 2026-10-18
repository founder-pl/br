"""Statutory B+R rates and base (regression: everything was 100% of the VAT-gross amount)."""
import importlib.util
from pathlib import Path

import pytest

# Load the dependency-free module directly; importing src.api.services runs service settings (/app/uploads).
_spec = importlib.util.spec_from_file_location(
    "br_deduction", Path(__file__).resolve().parents[2] / "src" / "api" / "services" / "br_deduction.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
deduction_amount, deduction_base = _mod.deduction_amount, _mod.deduction_base
deduction_rate, statutory_rate = _mod.deduction_rate, _mod.statutory_rate

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("category,rate", [
    ("personnel_employment", 2.0), ("personnel_civil", 2.0),
    ("materials", 1.0), ("equipment", 1.0), ("expertise", 1.0), (None, 1.0),
])
def test_statutory_rate_by_category(category, rate):
    assert statutory_rate(category) == rate


def test_default_stored_rate_cannot_undercount_salaries():
    salary = {"br_category": "personnel_employment", "br_deduction_rate": 1.0, "gross_amount": 10000, "net_amount": 7200}
    assert deduction_rate(salary) == 2.0
    assert deduction_base(salary) == 10000  # gross wage is the cost, net is take-home pay
    assert deduction_amount(salary) == 20000


def test_vat_payer_invoice_counts_net_of_vat():
    invoice = {"br_category": "materials", "br_deduction_rate": 1.0, "gross_amount": 1230, "net_amount": 1000}
    assert deduction_amount(invoice, is_vat_payer=True) == 1000
    assert deduction_amount(invoice, is_vat_payer=False) == 1230


def test_explicit_higher_rate_is_kept():
    expense = {"br_category": "materials", "br_deduction_rate": 1.5, "gross_amount": 100, "net_amount": 100}
    assert deduction_rate(expense) == 1.5


def test_missing_net_falls_back_to_gross():
    assert deduction_base({"br_category": "materials", "gross_amount": 50}, is_vat_payer=True) == 50
