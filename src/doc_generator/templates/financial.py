"""
Financial Templates - Financial document templates
"""
from typing import List
from .base import DocumentTemplate, DocumentCategory, TimeScope, TemplateDataRequirement


def get_financial_templates() -> List[DocumentTemplate]:
    """Return all financial templates"""
    return [
        DocumentTemplate(
            id="timesheet_monthly",
            name="Miesięczny Rejestr Czasu Pracy B+R",
            description="Zestawienie godzin pracy zespołu w projekcie B+R za dany miesiąc",
            category=DocumentCategory.TIMESHEET,
            time_scope=TimeScope.MONTHLY,
            data_requirements=[
                TemplateDataRequirement(
                    source_name="project_info",
                    required_params=["project_id"],
                    description="Informacje o projekcie"
                ),
                TemplateDataRequirement(
                    source_name="timesheet_summary",
                    required_params=["project_id", "year", "month"],
                    description="Dane z ewidencji czasu pracy"
                )
            ],
            template_content=TIMESHEET_MONTHLY_TEMPLATE,
            llm_prompt="""Wygeneruj miesięczny rejestr czasu pracy dla projektu B+R.
Podsumuj godziny każdego pracownika i opisz wykonane zadania.
Oblicz statystyki zbiorcze."""
        ),
        DocumentTemplate(
            id="expense_registry",
            name="Ewidencja Wydatków B+R",
            description="Szczegółowy rejestr wydatków kwalifikowanych do ulgi B+R",
            category=DocumentCategory.FINANCIAL,
            time_scope=TimeScope.MONTHLY,
            data_requirements=[
                TemplateDataRequirement(
                    source_name="project_info",
                    required_params=["project_id"],
                    description="Informacje o projekcie"
                ),
                TemplateDataRequirement(
                    source_name="expenses_summary",
                    required_params=["project_id"],
                    optional_params=["year", "month"],
                    description="Lista wydatków"
                )
            ],
            template_content=EXPENSE_REGISTRY_TEMPLATE,
            llm_prompt="""Wygeneruj ewidencję wydatków B+R na podstawie dostarczonych danych.
Dla każdego wydatku podaj uzasadnienie kwalifikacji do B+R.
Podsumuj według kategorii i oblicz procent kwalifikowanych."""
        )
    ]


TIMESHEET_MONTHLY_TEMPLATE = """# REJESTR CZASU PRACY - PROJEKT B+R

**Projekt:** {{project.name}} ({{project.code or 'BR-' + year|string}})

**Okres:** {{month_name}} {{year}}

## Zestawienie godzin pracy

| Pracownik | Godziny B+R | Dni roboczych |
|-----------|-------------|---------------|
{% for entry in timesheet %}
| {{entry.worker_name}} | {{entry.total_hours}} h | {{entry.days_worked or '-'}} |
{% endfor %}
{% if not timesheet %}
| *(Brak wpisów)* | 0 h | - |
{% endif %}

---

**PODSUMOWANIE:**

| Metryka | Wartość |
|---------|---------|
| Łączna liczba godzin B+R | **{{total_hours}} h** |
| Liczba pracowników | **{{worker_count}}** |
| Średnia godzin/pracownika | **{{avg_hours}} h** |

---

Zatwierdzenie kierownika projektu: _________________________

Data: {{generated_date}}
"""


EXPENSE_REGISTRY_TEMPLATE = """# EWIDENCJA WYDATKÓW B+R

**Projekt:** {{project.name}} ({{project.code or 'BR-' + year|string}})

**Okres:** {% if month %}{{month_name}} {% endif %}{{year}}

## Lista wydatków

| Nr | Data | Dostawca | Nr faktury | Kwota brutto | Kwalif. B+R | Dokument |
|----|------|----------|------------|--------------|-------------|----------|
{% for exp in expenses %}
{% if exp.invoice_date %}
| {{loop.index}} | {{exp.invoice_date|format_date}} | {{exp.vendor_name or 'N/A'}} | {{exp.invoice_number or 'N/A'}} | {{exp.gross_amount|format_currency}} | {% if exp.br_qualified %}✓{% else %}✗{% endif %} | {% if exp.document_id %}[{{exp.document_filename or 'Dokument'}}](/api/documents/{{exp.document_id}}/file){% else %}Brak{% endif %} |
{% endif %}
{% endfor %}
{% if not expenses %}
| - | - | - | - | - | - | - |
{% endif %}

---

## PODSUMOWANIE

| Metryka | Wartość |
|---------|---------|
| Liczba wydatków | {{expenses|length}} |
| Suma brutto | {{total_gross|format_currency}} |
| Suma netto | {{total_net|format_currency}} |
| Kwalifikowane B+R | {{total_qualified|format_currency}} |

---

Sporządził: _________________________

Data: {{generated_date}}
"""
