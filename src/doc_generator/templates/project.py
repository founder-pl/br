"""
Project Templates - Project-related document templates
"""
from typing import List
from .base import DocumentTemplate, DocumentCategory, TimeScope, TemplateDataRequirement


def get_project_templates() -> List[DocumentTemplate]:
    """Return all project-related templates"""
    return [
        DocumentTemplate(
            id="project_card",
            name="Karta Projektowa B+R",
            description="Karta identyfikacyjna projektu badawczo-rozwojowego zawierająca cele, zespół i koszty",
            category=DocumentCategory.PROJECT,
            time_scope=TimeScope.PROJECT,
            data_requirements=[
                TemplateDataRequirement(
                    source_name="project_info",
                    required_params=["project_id"],
                    description="Podstawowe informacje o projekcie"
                ),
                TemplateDataRequirement(
                    source_name="workers",
                    required_params=["project_id"],
                    description="Zespół projektowy"
                ),
                TemplateDataRequirement(
                    source_name="expenses_by_category",
                    required_params=["project_id"],
                    description="Podsumowanie kosztów"
                )
            ],
            template_content=PROJECT_CARD_TEMPLATE,
            demo_content=PROJECT_CARD_DEMO,
            llm_prompt="""Na podstawie dostarczonych danych projektu B+R wygeneruj profesjonalną Kartę Projektową.
Dokument powinien zawierać:
1. Pełną identyfikację projektu
2. Szczegółowy opis celów badawczych i hipotez
3. Listę zespołu z rolami
4. Zestawienie kosztów według kategorii

Użyj formalnego języka urzędowego. Wszystkie kwoty formatuj z separatorem tysięcy i symbolem PLN."""
        )
    ]


PROJECT_CARD_TEMPLATE = """# KARTA PROJEKTOWA BADAWCZO-ROZWOJOWA

## 1. IDENTYFIKACJA PROJEKTU

| Pole | Wartość |
|------|---------|
| **Nazwa projektu** | {{project.name or 'Brak nazwy'}} |
| **Kod/Symbol projektu** | BR-{{year}}-{{(project.id|string)[:8] if project.id else '00000000'}} |
| **Rok fiskalny** | {{project.fiscal_year or year}} |
| **Data rozpoczęcia** | {{project.start_date|format_date if project.start_date else 'Do ustalenia'}} |
| **Przewidywana data zakończenia** | {{project.end_date|format_date if project.end_date else 'Do ustalenia'}} |
| **Status** | {{project.status or 'active'}} |

## 2. OPIS DZIAŁALNOŚCI B+R

### Cel badań / zakres prac:
{{project.description or 'Projekt obejmuje prace badawczo-rozwojowe w zakresie innowacyjnych rozwiązań technologicznych.'}}

### Problem techniczny:
{{project.technical_problem or 'Określenie problemu technicznego wymaga dalszej analizy i dokumentacji.'}}

### Hipoteza badawcza:
{{project.hypothesis or 'Hipoteza badawcza zostanie sformułowana na podstawie wstępnych analiz.'}}

## 3. ZESPÓŁ BADAWCZY

| Imię i nazwisko | Rola | Stawka | Godziny B+R |
|-----------------|------|--------|-------------|
{% for worker in workers %}
| {{worker.name}} | {{worker.role or 'Specjalista B+R'}} | {{worker.hourly_rate or 0}} zł/h | {{worker.total_hours or 0}} h |
{% endfor %}
{% if not workers %}
| *(Brak przypisanych pracowników)* | - | - | - |
{% endif %}

## 4. KOSZTY PROJEKTOWE

| Kategoria | Liczba pozycji | Kwota brutto (PLN) | Kwalifikowane B+R |
|-----------|----------------|-------------------|-------------------|
{% for cat in expenses_by_category %}
{% if cat.category %}
| {{cat.category}} | {{cat.count}} | {{cat.total_gross|format_currency}} | {{cat.qualified_amount|format_currency}} |
{% endif %}
{% endfor %}
{% if not expenses_by_category %}
| *(Brak wydatków)* | 0 | 0,00 zł | 0,00 zł |
{% endif %}
| **RAZEM** | | **{{total_gross|format_currency}}** | **{{total_qualified|format_currency}}** |

## 5. ZATWIERDZENIE

Osoba odpowiedzialna: _________________________

Data zatwierdzenia: {{generated_date}}

Podpis: _________________________
"""


PROJECT_CARD_DEMO = """# KARTA PROJEKTOWA BADAWCZO-ROZWOJOWA

## 1. IDENTYFIKACJA PROJEKTU

| Pole | Wartość |
|------|---------|
| **Nazwa projektu** | System automatyzacji procesów B+R |
| **Kod/Symbol projektu** | BR-2025-00000001 |
| **Data rozpoczęcia** | 2025-01-01 |
| **Przewidywana data zakończenia** | 2025-12-31 |
| **Status** | W realizacji |

## 2. OPIS DZIAŁALNOŚCI B+R

### Cel badań / zakres prac:
Opracowanie innowacyjnego systemu do automatyzacji procesów badawczo-rozwojowych...

### Problem techniczny:
Brak efektywnych narzędzi do zarządzania dokumentacją B+R i obliczania wskaźnika Nexus...

### Hipoteza badawcza:
Zastosowanie sztucznej inteligencji pozwoli na automatyzację 80% procesów dokumentacyjnych...

## 3. ZESPÓŁ BADAWCZY

| Imię i nazwisko | Rola | Typ umowy | Zaangażowanie B+R |
|-----------------|------|-----------|-------------------|
| Jan Kowalski | Kierownik projektu | UoP | 100% |
| Anna Nowak | Programista senior | B2B | 80% |

## 4. KOSZTY PROJEKTOWE

| Kategoria | Liczba pozycji | Kwota brutto (PLN) | Kwalifikowane B+R |
|-----------|----------------|-------------------|-------------------|
| Wynagrodzenia | 12 | 120 000,00 zł | 120 000,00 zł |
| Materiały | 5 | 15 000,00 zł | 15 000,00 zł |
| Usługi IT | 8 | 45 000,00 zł | 45 000,00 zł |
| **RAZEM** | | **180 000,00 zł** | **180 000,00 zł** |
"""
