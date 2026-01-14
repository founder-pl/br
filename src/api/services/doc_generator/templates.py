"""
Template Generation for B+R Documentation.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List

from .prompts import CATEGORY_NAMES, CATEGORY_NAMES_WITH_RATES, MONTH_NAMES_PL


def build_expense_prompt(
    expense: Dict[str, Any],
    project: Dict[str, Any],
    document: Optional[Dict[str, Any]]
) -> str:
    """Build prompt for expense documentation generation."""
    
    br_category = expense.get('br_category') or 'other'
    deduction_rate = expense.get('br_deduction_rate', 1.0)
    deduction_amount = float(expense.get('gross_amount', 0)) * deduction_rate
    
    prompt = f"""Wygeneruj dokumentację B+R dla poniższego wydatku:

DANE PROJEKTU:
- Nazwa projektu: {project.get('name', 'Projekt B+R')}
- Rok podatkowy: {project.get('fiscal_year', datetime.now().year)}
- Firma: {project.get('company_name', 'Firma')}

DANE WYDATKU:
- Nr faktury: {expense.get('invoice_number', 'N/A')}
- Data faktury: {expense.get('invoice_date', 'N/A')}
- Dostawca: {expense.get('vendor_name', 'N/A')}
- NIP dostawcy: {expense.get('vendor_nip', 'N/A')}
- Kwota brutto: {expense.get('gross_amount', 0)} {expense.get('currency', 'PLN')}
- Kwota netto: {expense.get('net_amount', 0)} {expense.get('currency', 'PLN')}
- VAT: {expense.get('vat_amount', 0)} {expense.get('currency', 'PLN')}

KLASYFIKACJA B+R:
- Kategoria: {CATEGORY_NAMES_WITH_RATES.get(br_category, br_category)}
- Kwalifikowany: {'Tak' if expense.get('br_qualified') else 'Nie'}
- Stawka odliczenia: {int(deduction_rate * 100)}%
- Kwota odliczenia: {deduction_amount:.2f} PLN
- Uzasadnienie: {expense.get('br_qualification_reason', 'Brak')}

{f"OPIS Z DOKUMENTU: {document.get('ocr_text', '')[:500]}..." if document and document.get('ocr_text') else ''}

Wygeneruj profesjonalną dokumentację B+R w formacie Markdown zawierającą:
1. Nagłówek z numerem dokumentu i datą
2. Identyfikację wydatku
3. Związek z działalnością B+R projektu
4. Uzasadnienie kategorii kosztów
5. Kalkulację odliczenia
6. Podsumowanie

Format: Markdown z nagłówkami H1, H2, H3"""

    return prompt


def generate_expense_template(
    expense: Dict[str, Any],
    project: Dict[str, Any],
    document: Optional[Dict[str, Any]]
) -> str:
    """Generate documentation from template (fallback)."""
    
    br_category = expense.get('br_category') or 'other'
    deduction_rate = expense.get('br_deduction_rate', 1.0)
    gross = float(expense.get('gross_amount', 0))
    net = float(expense.get('net_amount', 0))
    vat = float(expense.get('vat_amount', 0))
    deduction_amount = gross * deduction_rate
    
    doc_date = datetime.now().strftime('%Y-%m-%d')
    invoice_date = expense.get('invoice_date') or 'N/A'
    iteration_num = hash(expense.get('id', '')) % 1000 + 1
    
    # OCR/Document info section
    ocr_section = ""
    if document:
        ocr_text = document.get('ocr_text', '')[:500] if document.get('ocr_text') else ''
        ocr_confidence = document.get('ocr_confidence', 0) * 100 if document.get('ocr_confidence') else 0
        ocr_section = f"""
## 6. Dane źródłowe dokumentu

### Wyniki przetwarzania OCR

| Parametr | Wartość |
|----------|---------|
| Nazwa pliku | {document.get('filename', 'N/A')} |
| Typ dokumentu | {document.get('document_type', 'N/A')} |
| Status OCR | {document.get('ocr_status', 'N/A')} |
| Pewność OCR | {ocr_confidence:.1f}% |

### Fragment rozpoznanego tekstu

```
{ocr_text}
```
"""
    
    return f"""# Dokumentacja Wydatku B+R - Iteracja #{iteration_num}

**Nr dokumentu:** BR-{expense.get('id', 'N/A')[:8]}
**Data sporządzenia:** {doc_date}
**Wersja:** 1.0

---

## 1. Identyfikacja wydatku

| Parametr | Wartość |
|----------|---------|
| Nr faktury | {expense.get('invoice_number', 'N/A')} |
| Data faktury | {invoice_date} |
| Dostawca | {expense.get('vendor_name', 'N/A')} |
| NIP dostawcy | {expense.get('vendor_nip', 'N/A')} |
| Kwota brutto | {gross:.2f} {expense.get('currency', 'PLN')} |
| Kwota netto | {net:.2f} {expense.get('currency', 'PLN')} |
| VAT | {vat:.2f} {expense.get('currency', 'PLN')} |

## 2. Powiązanie z projektem B+R

**Projekt:** {project.get('name', 'Projekt B+R')}
**Rok podatkowy:** {project.get('fiscal_year', datetime.now().year)}

Niniejszy wydatek stanowi iterację #{iteration_num} w ramach projektu badawczo-rozwojowego
i dokumentuje postęp prac nad innowacyjnymi rozwiązaniami.

## 3. Opis prac badawczo-rozwojowych

### Cel iteracji

W ramach tej iteracji projektu przeprowadzono prace związane z:
- Testowaniem nowych rozwiązań technologicznych
- Weryfikacją hipotez badawczych
- Dokumentacją wyników eksperymentów

### Metodologia

Prace prowadzono zgodnie z metodyką badawczo-rozwojową obejmującą:
1. Planowanie eksperymentu
2. Realizację testów
3. Analiza wyników
4. Dokumentacja wniosków

### Wyniki i wnioski

Iteracja #{iteration_num} przyniosła następujące rezultaty:
- Zweryfikowano założenia techniczne
- Udokumentowano nowe doświadczenia
- Zidentyfikowano obszary do dalszych prac

## 4. Klasyfikacja kosztów B+R

**Kategoria:** {CATEGORY_NAMES.get(br_category, br_category)}

### Uzasadnienie klasyfikacji

{expense.get('br_qualification_reason') or 'Wydatek został zakwalifikowany jako koszt kwalifikowany w ramach działalności badawczo-rozwojowej na podstawie związku z realizowanym projektem B+R.'}

## 5. Kalkulacja odliczenia

| Element | Wartość | Obliczenie |
|---------|---------|------------|
| Kwota brutto | {gross:.2f} PLN | - |
| Kwota netto | {net:.2f} PLN | - |
| VAT ({((vat/net)*100) if net > 0 else 23:.0f}%) | {vat:.2f} PLN | {net:.2f} × {((vat/net)*100) if net > 0 else 23:.0f}% |
| Kwota kwalifikowana | {gross:.2f} PLN | kwota brutto |
| Stawka odliczenia | {int(deduction_rate * 100)}% | art. 18d CIT |
| **Odliczenie B+R** | **{deduction_amount:.2f} PLN** | {gross:.2f} × {int(deduction_rate * 100)}% |
{ocr_section}
## 7. Podsumowanie

Wydatek stanowi część iteracji #{iteration_num} projektu B+R i kwalifikuje się do odliczenia
zgodnie z art. 18d ustawy o CIT. Dokumentacja potwierdza związek wydatku z działalnością
badawczo-rozwojową oraz prawidłowość kalkulacji.

**Całkowita kwota do odliczenia: {deduction_amount:.2f} PLN**

---

*Dokumentacja wygenerowana automatycznie przez System B+R*
*Data: {doc_date} | Iteracja: #{iteration_num}*
"""


def generate_summary_template(
    project: Dict[str, Any],
    expenses: list,
    by_category: Dict,
    total_gross: float,
    total_br: float,
    total_deduction: float,
    timesheet_data: Optional[Dict[str, Any]] = None,
    contractors: Optional[List[Dict[str, Any]]] = None,
    revenues: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Generate comprehensive B+R project summary template."""
    
    doc_date = datetime.now().strftime('%Y-%m-%d')
    fiscal_year = project.get('fiscal_year', datetime.now().year)
    
    # Build category table
    category_rows = ""
    for cat, data in by_category.items():
        cat_name = CATEGORY_NAMES.get(cat, cat)
        category_rows += f"| {cat_name} | {data['count']} | {data['amount']:.2f} PLN | {data['deduction']:.2f} PLN |\n"
    
    # Build detailed expense descriptions
    expense_details = build_expense_details(expenses)
    
    # Build timesheet section with monthly breakdown
    timesheet_section = build_timesheet_section(timesheet_data)
    
    # Build contractors section
    contractors_section = build_contractors_section(contractors)
    
    # Build revenues section (monetization)
    revenues_section, total_revenue = build_revenues_section(revenues, total_gross)
    
    return f"""# Dokumentacja Projektu B+R: {project.get('name', 'Projekt B+R')}

**Kod projektu:** BR-{fiscal_year}-{str(project.get('id', '000'))[:8]}
**Rok podatkowy:** {fiscal_year}
**Data sporządzenia:** {doc_date}
**Firma:** Tomasz Sapletta
**NIP:** 5881918662

---

## Streszczenie Wykonawcze

Niniejsza dokumentacja przedstawia kompleksowe podsumowanie projektu badawczo-rozwojowego 
realizowanego w roku podatkowym {fiscal_year}. Projekt spełnia kryteria działalności B+R 
określone w art. 4a pkt 26-28 ustawy o CIT: systematyczność, twórczość i innowacyjność.

| Parametr | Wartość |
|----------|---------|
| Całkowite koszty projektu | {total_gross:.2f} PLN |
| Koszty kwalifikowane B+R | {total_br:.2f} PLN |
| Kwota odliczenia podatkowego | {total_deduction:.2f} PLN |
| Przychody z komercjalizacji | {total_revenue:.2f} PLN |

---

## 1. Opis projektu

### 1.1 Cel projektu

{project.get('description', 'Brak opisu projektu.')}

### 1.2 Innowacyjność rozwiązania

Projekt charakteryzuje się następującymi elementami innowacyjności:
- Rozwój nowych technologii i metod
- Testowanie prototypowych rozwiązań
- Dokumentacja doświadczeń i wniosków z eksperymentów

### 1.3 Zakres prac B+R

Prace badawczo-rozwojowe obejmowały:
- Badania stosowane i prace rozwojowe
- Tworzenie prototypów i modeli doświadczalnych
- Testowanie i walidacja rozwiązań

## 2. Metodologia badawcza

### 2.1 Systematyczność

Projekt realizowany zgodnie z przyjętym harmonogramem i metodyką, z regularnymi 
przeglądami postępów i dokumentacją wyników każdej iteracji.

### 2.2 Twórczość

Prace projektowe miały charakter twórczy - oparte na oryginalnych koncepcjach 
i kreatywnym podejściu do rozwiązywania problemów technologicznych.

### 2.3 Element niepewności

W projekcie występował element niepewności co do osiągnięcia zakładanych rezultatów,
co jest cechą charakterystyczną działalności badawczo-rozwojowej.

## 3. Podsumowanie kosztów

### 3.1 Zestawienie ogólne

| Parametr | Wartość |
|----------|---------|
| Liczba wszystkich wydatków | {len(expenses)} |
| Liczba wydatków kwalifikowanych B+R | {len([e for e in expenses if e.get('br_qualified')])} |
| Suma wszystkich wydatków | {total_gross:.2f} PLN |
| Suma wydatków kwalifikowanych | {total_br:.2f} PLN |
| **Całkowita kwota odliczenia B+R** | **{total_deduction:.2f} PLN** |

### 3.2 Podział według kategorii kosztów kwalifikowanych

| Kategoria | Liczba | Kwota | Odliczenie |
|-----------|--------|-------|------------|
{category_rows}| **RAZEM** | **{sum(d['count'] for d in by_category.values()) if by_category else 0}** | **{total_br:.2f} PLN** | **{total_deduction:.2f} PLN** |

## 4. Podstawa prawna

Dokumentacja sporządzona zgodnie z wymogami:
- Art. 18d ustawy z dnia 15 lutego 1992 r. o podatku dochodowym od osób prawnych
- Art. 26e ustawy z dnia 26 lipca 1991 r. o podatku dochodowym od osób fizycznych

### Stawki odliczenia kosztów kwalifikowanych:

| Kategoria | Stawka | Podstawa prawna |
|-----------|--------|-----------------|
| Wynagrodzenia (umowa o pracę) | 200% | art. 18d ust. 2 pkt 1 |
| Umowy cywilnoprawne | 200% | art. 18d ust. 2 pkt 1a |
| Materiały i surowce | 100% | art. 18d ust. 2 pkt 2 |
| Ekspertyzy i usługi | 100% | art. 18d ust. 2 pkt 3 |
| Amortyzacja | 100% | art. 18d ust. 3 |

## 5. Szczegółowa dokumentacja wydatków

Każdy wydatek stanowi odrębną iterację w projekcie B+R, dokumentując postęp prac:

{expense_details}
{timesheet_section}{contractors_section}{revenues_section}
## 10. Oświadczenie

Oświadczam, że:
1. Wydatki ujęte w dokumentacji zostały faktycznie poniesione w roku podatkowym {fiscal_year}
2. Wydatki są bezpośrednio związane z prowadzoną działalnością badawczo-rozwojową
3. Dokumentacja odzwierciedla rzeczywisty przebieg prac B+R
4. Projekt spełnia kryteria systematyczności, twórczości i innowacyjności

---

*Dokumentacja wygenerowana automatycznie przez System B+R*
*Data: {doc_date}*
*Wersja dokumentu: 1.0*
"""


def build_expense_details(expenses: list, company_nip: str = "5881918662") -> str:
    """Build detailed expense descriptions with justifications."""
    
    def clean_nip(nip):
        if not nip: return ''
        return ''.join(c for c in str(nip) if c.isdigit())
    
    cost_expenses = [
        e for e in expenses 
        if clean_nip(e.get('vendor_nip')) != clean_nip(company_nip)
    ]
    
    if not cost_expenses:
        return "Brak wydatków kosztowych do udokumentowania.\n"
    
    details = ""
    for i, e in enumerate(cost_expenses, 1):
        iteration = hash(e.get('id', '')) % 1000 + 1
        inv_date = e.get('invoice_date', 'N/A')
        inv_num = e.get('invoice_number', 'N/A')
        vendor = e.get('vendor_name', 'Nieznany dostawca')
        vendor_nip = e.get('vendor_nip', 'N/A')
        gross = float(e.get('gross_amount', 0))
        net = float(e.get('net_amount', 0))
        vat = float(e.get('vat_amount', 0))
        currency = e.get('currency', 'PLN')
        br_cat = e.get('br_category', 'other')
        br_qualified = e.get('br_qualified', False)
        br_reason = e.get('br_qualification_reason', '')
        deduction_rate = float(e.get('br_deduction_rate', 1.0))
        
        status_icon = "✅" if br_qualified else "⏳"
        cat_name = CATEGORY_NAMES.get(br_cat, br_cat)
        
        details += f"""
### Iteracja #{iteration} - Wydatek {i}

| Parametr | Wartość |
|----------|---------|
| Nr faktury | {inv_num} |
| Data | {inv_date} |
| Dostawca | {vendor} |
| NIP dostawcy | {vendor_nip} |
| Kwota netto | {net:.2f} {currency} |
| VAT | {vat:.2f} {currency} |
| Kwota brutto | {gross:.2f} {currency} |
| Kategoria B+R | {cat_name} |
| Status kwalifikacji | {status_icon} {'Kwalifikowany' if br_qualified else 'Oczekuje na klasyfikację'} |
| Stawka odliczenia | {int(deduction_rate * 100)}% |
| Kwota odliczenia | {gross * deduction_rate if br_qualified else 0:.2f} PLN |
| Dokument źródłowy | {format_doc_link(e)} |

**Uzasadnienie kwalifikacji B+R:**

{br_reason if br_reason else 'Wydatek związany z realizacją prac badawczo-rozwojowych w ramach projektu. Stanowi koszt niezbędny do przeprowadzenia eksperymentów i testów prototypowych rozwiązań.'}

**Powiązanie z działalnością B+R:**

Wydatek dokumentuje iterację #{iteration} projektu B+R, w ramach której:
- Przeprowadzono testy i eksperymenty technologiczne
- Zweryfikowano hipotezy badawcze
- Udokumentowano wyniki i wnioski

---
"""
    return details


def build_timesheet_section(timesheet_data: Optional[Dict[str, Any]]) -> str:
    """Build timesheet section with monthly breakdown."""
    if not timesheet_data or timesheet_data.get('total_hours', 0) <= 0:
        return ""
    
    section = f"""
## 7. Ewidencja czasu pracy

| Parametr | Wartość |
|----------|---------|
| Łączna liczba godzin | {timesheet_data.get('total_hours', 0)} h |

### 7.1 Podział godzin według pracowników:

| Pracownik | Godziny |
|-----------|---------|
"""
    for w in timesheet_data.get('by_worker', []):
        section += f"| {w['worker_name']} | {w['total_hours']} h |\n"
    
    # Monthly breakdown
    monthly_data = timesheet_data.get('by_month', [])
    if monthly_data:
        section += "\n### 7.2 Rozbicie miesięczne godzin:\n\n"
        
        workers = list(set(w['worker_name'] for w in timesheet_data.get('by_worker', [])))
        
        section += "| Miesiąc |"
        for worker in workers:
            section += f" {worker[:15]} |"
        section += " **Razem** |\n"
        
        section += "|---------|" + "".join(["--------|" for _ in workers]) + "--------|\n"
        
        months_dict = {}
        for entry in monthly_data:
            month_key = (entry.get('year'), entry.get('month'))
            if month_key not in months_dict:
                months_dict[month_key] = {}
            months_dict[month_key][entry.get('worker_name', '')] = entry.get('hours', 0)
        
        for (year, month), worker_hours in sorted(months_dict.items()):
            month_name = f"{MONTH_NAMES_PL.get(month, month)} {year}"
            total = sum(worker_hours.values())
            section += f"| {month_name} |"
            for worker in workers:
                h = worker_hours.get(worker, 0)
                section += f" {h} h |" if h else " - |"
            section += f" **{total} h** |\n"
    
    return section


def build_contractors_section(contractors: Optional[List[Dict[str, Any]]]) -> str:
    """Build contractors section."""
    if not contractors or len(contractors) == 0:
        return ""
    
    section = """
## 8. Kooperanci i dostawcy (faktury kosztowe)

| Nazwa | NIP | Kwota | Liczba faktur |
|-------|-----|-------|---------------|
"""
    for c in contractors:
        section += f"| {c.get('vendor_name', '-')} | {c.get('vendor_nip', '-')} | {c.get('total_amount', 0):.2f} PLN | {c.get('invoice_count', 0)} |\n"
    
    return section


def build_revenues_section(revenues: Optional[List[Dict[str, Any]]], total_gross: float) -> tuple:
    """Build revenues section (monetization)."""
    if not revenues or len(revenues) == 0:
        return "", 0
    
    total_revenue = sum(float(r.get('gross_amount', 0)) for r in revenues)
    section = f"""
## 9. Monetyzacja projektu B+R (faktury przychodowe)

Poniższa sekcja dokumentuje przychody z komercjalizacji wyników projektu B+R.

| Data | Nr faktury | Klient | Kwota | Opis | Dokument |
|------|------------|--------|-------|------|----------|
"""
    for r in revenues:
        ip_desc = r.get('ip_description') or 'Usługi B+R'
        client = r.get('client_name') or r.get('client_nip') or 'N/A'
        doc_link = format_doc_link(r)
        section += f"| {r.get('invoice_date', 'N/A')} | {r.get('invoice_number', 'N/A')} | {client} | {float(r.get('gross_amount', 0)):.2f} PLN | {ip_desc[:30]} | {doc_link} |\n"
    
    section += f"""
**Łączne przychody z projektu B+R:** {total_revenue:.2f} PLN

### Analiza rentowności projektu

| Wskaźnik | Wartość |
|----------|---------|
| Koszty projektu | {total_gross:.2f} PLN |
| Przychody projektu | {total_revenue:.2f} PLN |
| Bilans projektu | {total_revenue - total_gross:.2f} PLN |
| ROI | {((total_revenue / total_gross - 1) * 100) if total_gross > 0 else 0:.1f}% |
"""
    return section, total_revenue


def format_doc_link(expense: Dict[str, Any]) -> str:
    """Format document link for expense."""
    doc_id = expense.get('document_id')
    doc_filename = expense.get('document_filename') or expense.get('filename')
    if doc_id:
        return f"[{doc_filename or 'Dokument'}](/api/documents/{doc_id}/file)"
    return "Brak dokumentu"
