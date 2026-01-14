"""
Tax Templates - Tax-related document templates (IP Box, B+R)
"""
from typing import List
from .base import DocumentTemplate, DocumentCategory, TimeScope, TemplateDataRequirement


def get_tax_templates() -> List[DocumentTemplate]:
    """Return all tax-related templates"""
    return [
        DocumentTemplate(
            id="nexus_calculation",
            name="Obliczenie Wskaźnika Nexus",
            description="Kalkulacja wskaźnika Nexus dla potrzeb IP Box",
            category=DocumentCategory.TAX,
            time_scope=TimeScope.YEARLY,
            data_requirements=[
                TemplateDataRequirement(source_name="project_info", required_params=["project_id"], description="Informacje o projekcie"),
                TemplateDataRequirement(source_name="nexus_calculation", required_params=["project_id"], optional_params=["year"], description="Dane do obliczenia Nexus"),
                TemplateDataRequirement(source_name="revenues", required_params=["project_id"], optional_params=["year"], description="Przychody z IP")
            ],
            template_content=NEXUS_CALCULATION_TEMPLATE,
            llm_prompt="Wykonaj obliczenie wskaźnika Nexus dla IP Box na podstawie dostarczonych danych."
        ),
        DocumentTemplate(
            id="br_annual_summary",
            name="Roczne Podsumowanie B+R",
            description="Kompleksowe roczne zestawienie działalności B+R dla celów podatkowych",
            category=DocumentCategory.REPORT,
            time_scope=TimeScope.YEARLY,
            data_requirements=[
                TemplateDataRequirement(source_name="project_info", required_params=["project_id"], description="Informacje o projekcie"),
                TemplateDataRequirement(source_name="expenses_by_category", required_params=["project_id", "year"], description="Wydatki według kategorii"),
                TemplateDataRequirement(source_name="timesheet_monthly_breakdown", required_params=["project_id", "year"], description="Godziny pracy miesięcznie"),
                TemplateDataRequirement(source_name="revenues", required_params=["project_id", "year"], description="Przychody"),
                TemplateDataRequirement(source_name="nexus_calculation", required_params=["project_id", "year"], description="Wskaźnik Nexus")
            ],
            template_content=BR_ANNUAL_SUMMARY_TEMPLATE,
            llm_prompt="Wygeneruj kompleksowe roczne podsumowanie działalności B+R."
        ),
        DocumentTemplate(
            id="ip_box_procedure",
            name="Procedura Wewnętrzna IP Box",
            description="Dokument opisujący wewnętrzne procedury stosowania preferencji IP Box",
            category=DocumentCategory.TAX,
            time_scope=TimeScope.PROJECT,
            data_requirements=[
                TemplateDataRequirement(source_name="project_info", required_params=["project_id"], description="Informacje o projekcie")
            ],
            template_content=IP_BOX_PROCEDURE_TEMPLATE,
            llm_prompt="Wygeneruj procedurę wewnętrzną IP Box dostosowaną do specyfiki projektu."
        ),
        DocumentTemplate(
            id="tax_interpretation_request",
            name="Wniosek o Interpretację Indywidualną",
            description="Wzór wniosku do KIS o interpretację przepisów B+R/IP Box",
            category=DocumentCategory.TAX,
            time_scope=TimeScope.PROJECT,
            data_requirements=[
                TemplateDataRequirement(source_name="project_info", required_params=["project_id"], description="Informacje o projekcie"),
                TemplateDataRequirement(source_name="expenses_by_category", required_params=["project_id"], description="Struktura kosztów")
            ],
            template_content=TAX_INTERPRETATION_REQUEST_TEMPLATE,
            llm_prompt="Wygeneruj wniosek o interpretację indywidualną dla ulgi B+R / IP Box."
        )
    ]


NEXUS_CALCULATION_TEMPLATE = """# OBLICZENIE WSKAŹNIKA NEXUS - IP BOX

**Projekt:** {{project.name}}{% if project.code %} ({{project.code}}){% endif %}

**Rok podatkowy:** {{year}}

## 1. Składniki wzoru Nexus

| Symbol | Opis | Kwota (PLN) |
|--------|------|-------------|
| **a** | Koszty B+R poniesione bezpośrednio | {{nexus.a_direct|format_currency}} |
| **b** | Koszty nabycia B+R od podmiotów niepowiązanych | {{nexus.b_unrelated|format_currency}} |
| **c** | Koszty nabycia B+R od podmiotów powiązanych | {{nexus.c_related|format_currency}} |
| **d** | Koszty zakupu gotowego IP | {{nexus.d_ip|format_currency}} |

## 2. Obliczenie wskaźnika

```
Nexus = ((a + b) × 1,3) / (a + b + c + d)

Nexus = (({{nexus.a_direct}} + {{nexus.b_unrelated}}) × 1,3) / ({{nexus.a_direct}} + {{nexus.b_unrelated}} + {{nexus.c_related}} + {{nexus.d_ip}})

Nexus = {{nexus.nexus|round(4)}}
```

{% if nexus.nexus >= 1 %}
**Uwaga:** Wskaźnik Nexus nie może przekroczyć 1, więc przyjmujemy wartość **1,0**.
{% endif %}

## 3. Zastosowanie do dochodu

| Pozycja | Wartość |
|---------|---------|
| Przychody z IP | {{total_revenue|format_currency}} |
| Koszty uzyskania | {{total_costs|format_currency}} |
| Dochód z IP | {{ip_income|format_currency}} |
| Wskaźnik Nexus | {{nexus.nexus|round(4)}} |
| **Dochód kwalifikowany** | **{{qualified_income|format_currency}}** |
| Stawka IP Box | 5% |
| **Podatek IP Box** | **{{ip_tax|format_currency}}** |

---

Obliczenie wykonano: {{generated_date}}
"""


BR_ANNUAL_SUMMARY_TEMPLATE = """# ROCZNE PODSUMOWANIE DZIAŁALNOŚCI B+R

## Informacje ogólne

| Pole | Wartość |
|------|---------|
| **Projekt** | {{project.name}} |
| **Kod** | BR-{{year}}-{{(project.id|string)[:8] if project.id else '00000000'}} |
| **Rok podatkowy** | {{year}} |
| **Data sporządzenia** | {{generated_date}} |

---

## 1. Koszty kwalifikowane B+R

### 1.1 Zestawienie według kategorii

| Kategoria | Liczba | Kwota brutto | Kwalifikowane |
|-----------|--------|--------------|---------------|
{% for cat in expenses_by_category %}{% if cat.category %}
| {{cat.category}} | {{cat.count}} | {{cat.total_gross|format_currency}} | {{cat.qualified_amount|format_currency}} |
{% endif %}{% endfor %}
{% if not expenses_by_category %}| *(Brak wydatków)* | 0 | 0,00 zł | 0,00 zł |
{% endif %}| **RAZEM** | | **{{total_expenses|format_currency}}** | **{{total_qualified|format_currency}}** |

### 1.2 Ulga B+R (100% kosztów kwalifikowanych)

**Kwota ulgi do odliczenia: {{total_qualified|format_currency}}**

---

## 2. Ewidencja czasu pracy

### 2.1 Zestawienie

| Pracownik | Łączne godziny B+R |
|-----------|-------------------|
{% for entry in timesheet %}
| {{entry.worker_name}} | {{entry.total_hours}} h |
{% endfor %}
{% if not timesheet %}
| *(Brak danych)* | 0 h |
{% endif %}
| **RAZEM** | **{{total_hours}} h** |

---

## 3. Przychody z IP (IP Box)

| Data | Opis | Kwota | Kwalif. IP Box |
|------|------|-------|----------------|
{% for rev in revenues %}{% if rev.invoice_date and rev.gross_amount %}
| {{rev.invoice_date|format_date}} | {{rev.description or rev.invoice_number or 'N/A'}} | {{rev.gross_amount|format_currency}} | {% if rev.ip_qualified %}✓{% else %}✗{% endif %} |
{% endif %}{% endfor %}
{% if not revenues or total_revenue == 0 %}| - | Brak przychodów w tym okresie | 0,00 zł | - |
{% endif %}| **RAZEM** | | **{{total_revenue|format_currency}}** | |

---

## 4. Wskaźnik Nexus

| Składnik | Wartość |
|----------|---------|
| a (bezpośrednie) | {{nexus.a_direct|format_currency}} |
| b (niepowiązane) | {{nexus.b_unrelated|format_currency}} |
| c (powiązane) | {{nexus.c_related|format_currency}} |
| d (zakup IP) | {{nexus.d_ip|format_currency}} |
| **Nexus** | **{{nexus.nexus|round(4)}}** |

---

## 5. Podsumowanie podatkowe

| Ulga/Preferencja | Wartość |
|------------------|---------|
| Ulga B+R (100%) | {{total_qualified|format_currency}} |
| Dochód kwalifikowany IP Box | {{qualified_income|format_currency}} |
| Oszczędność podatkowa IP Box | {{ip_box_savings|format_currency}} |

---

*Dokument wygenerowany automatycznie. Wymaga weryfikacji przez doradcę podatkowego.*
"""


IP_BOX_PROCEDURE_TEMPLATE = """# PROCEDURA WEWNĘTRZNA - STOSOWANIE IP BOX

**Podmiot:** _____________________

**NIP:** _____________________

**Data wdrożenia:** {{generated_date}}

---

## 1. CEL PROCEDURY

Niniejsza procedura określa zasady identyfikacji, ewidencji i rozliczania kwalifikowanych praw własności intelektualnej (IP) dla potrzeb zastosowania preferencyjnej stawki podatku 5% (IP Box).

---

## 2. IDENTYFIKACJA KWALIFIKOWANEGO IP

### 2.1 Rodzaje kwalifikowanego IP

- [ ] Patenty
- [ ] Prawa ochronne na wzory użytkowe
- [ ] Prawa z rejestracji wzorów przemysłowych
- [x] Autorskie prawa do programów komputerowych
- [ ] Know-how

### 2.2 Projekty objęte procedurą

| Projekt | Kod | Rodzaj IP | Status |
|---------|-----|-----------|--------|
| {{project.name}} | {{project.code}} | Program komputerowy | W realizacji |

---

## 3. PROWADZENIE EWIDENCJI IP BOX

### 3.1 Zakres ewidencji

1. **Przychody z IP:** Sprzedaż licencji, opłaty licencyjne, przychody z usług wykorzystujących IP
2. **Koszty bezpośrednie:** Wynagrodzenia pracowników B+R, materiały i surowce, usługi zewnętrzne
3. **Koszty pośrednie (dla Nexus):** Koszty od podmiotów powiązanych, koszty zakupu gotowego IP

### 3.2 Terminy aktualizacji

| Czynność | Termin |
|----------|--------|
| Rejestracja przychodów | Na bieżąco |
| Rejestracja kosztów | Do 5. dnia następnego miesiąca |
| Podsumowanie miesięczne | Do 10. dnia następnego miesiąca |
| Obliczenie Nexus | Rocznie, do 31 stycznia |

---

## 4. OBLICZANIE WSKAŹNIKA NEXUS

```
Nexus = ((a + b) × 1,3) / (a + b + c + d)
```

Gdzie: a = koszty B+R bezpośrednie, b = od niepowiązanych, c = od powiązanych, d = zakup IP

---

## 5. PRZECHOWYWANIE DOKUMENTACJI

Minimum 5 lat od końca roku, w którym złożono zeznanie.

---

**Zatwierdzam:**

_____________________
(podpis, data)
"""


TAX_INTERPRETATION_REQUEST_TEMPLATE = """# WNIOSEK O WYDANIE INTERPRETACJI INDYWIDUALNEJ

**Do:** Dyrektor Krajowej Informacji Skarbowej

**Wnioskodawca:**
- Nazwa: _____________________
- NIP: _____________________
- Adres: _____________________

---

## 1. OPIS STANU FAKTYCZNEGO

Wnioskodawca prowadzi działalność badawczo-rozwojową w ramach projektu:

**{{project.name}}**

{{project.description or 'Projekt obejmuje prace badawczo-rozwojowe.'}}

---

## 2. PYTANIA

1. Czy opisana działalność stanowi działalność badawczo-rozwojową w rozumieniu art. 4a pkt 26-28 ustawy o CIT / art. 5a pkt 38-40 ustawy o PIT?

2. Czy poniesione koszty mogą być uznane za koszty kwalifikowane do ulgi B+R zgodnie z art. 18d ustawy o CIT / art. 26e ustawy o PIT?

3. Czy wytworzone prawa autorskie do programu komputerowego stanowią kwalifikowane IP w rozumieniu art. 24d ustawy o CIT / art. 30ca ustawy o PIT?

---

## 3. STANOWISKO WNIOSKODAWCY

W ocenie Wnioskodawcy, przedstawiona działalność spełnia definicję działalności badawczo-rozwojowej...

---

## 4. ZAŁĄCZNIKI

1. Dokumentacja techniczna projektu
2. Zestawienie kosztów według kategorii
3. Ewidencja czasu pracy

---

_____________________
(podpis wnioskodawcy)

Data: {{generated_date}}
"""
