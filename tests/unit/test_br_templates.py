"""Generated B+R documentation uses the statutory rate and the tax-cost base."""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]


def _load(name, path, package):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = package
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def templates():
    # Avoid src.api.services/__init__ (service settings create /app/uploads).
    for name, path in (("brsvc", "src/api/services"), ("brsvc.doc_generator", "src/api/services/doc_generator")):
        package = types.ModuleType(name)
        package.__path__ = [str(ROOT / path)]
        sys.modules[name] = package
    _load("brsvc.br_deduction", ROOT / "src/api/services/br_deduction.py", "brsvc")
    _load("brsvc.doc_generator.prompts", ROOT / "src/api/services/doc_generator/prompts.py", "brsvc.doc_generator")
    return _load("brsvc.doc_generator.templates", ROOT / "src/api/services/doc_generator/templates.py", "brsvc.doc_generator")


SALARY = {"br_category": "personnel_employment", "br_deduction_rate": 1.0, "gross_amount": 10000, "net_amount": 7200, "currency": "PLN"}
INVOICE = {"br_category": "materials", "br_deduction_rate": 1.0, "gross_amount": 1230, "net_amount": 1000, "vat_amount": 230, "currency": "PLN"}


def test_salary_prompt_uses_200_percent_of_gross_wage(templates):
    prompt = templates.build_expense_prompt(SALARY, {"name": "P"}, None)
    assert "200%" in prompt and "20000.00" in prompt


def test_invoice_prompt_uses_net_amount_for_a_vat_payer(templates, monkeypatch):
    monkeypatch.setenv("BR_VAT_PAYER", "1")
    prompt = templates.build_expense_prompt(INVOICE, {"name": "P"}, None)
    assert "100%" in prompt and "1000.00" in prompt and "1230.00 ×" not in prompt
