"""
Document Templates Registry

Defines available document templates with their metadata, data requirements,
and generation logic.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import json


class DocumentCategory(str, Enum):
    PROJECT = "project"
    FINANCIAL = "financial"
    TIMESHEET = "timesheet"
    LEGAL = "legal"
    TAX = "tax"
    REPORT = "report"


class TimeScope(str, Enum):
    NONE = "none"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    PROJECT = "project"
    CUSTOM = "custom"


@dataclass
class TemplateDataRequirement:
    """Defines a data source requirement for a template"""
    source_name: str
    required_params: List[str]
    optional_params: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class DocumentTemplate:
    """Document template definition"""
    id: str
    name: str
    description: str
    category: DocumentCategory
    time_scope: TimeScope
    data_requirements: List[TemplateDataRequirement]
    template_content: str
    demo_content: Optional[str] = None
    llm_prompt: Optional[str] = None
    output_format: str = "markdown"
    version: str = "1.0"
    
    def get_required_params(self) -> List[str]:
        """Get all required parameters across data sources"""
        params = set()
        for req in self.data_requirements:
            params.update(req.required_params)
        return list(params)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "time_scope": self.time_scope.value,
            "required_params": self.get_required_params(),
            "output_format": self.output_format,
            "version": self.version
        }


class TemplateRegistry:
    """Registry for document templates"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._templates = {}
            cls._instance._initialize_templates()
        return cls._instance
    
    def _initialize_templates(self):
        """Initialize all B+R and IP Box document templates"""
        
        self.register(DocumentTemplate(
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
            template_content="""# KARTA PROJEKTOWA BADAWCZO-ROZWOJOWA

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
""",
            demo_content="""# KARTA PROJEKTOWA BADAWCZO-ROZWOJOWA

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
""",
            llm_prompt="""Na podstawie dostarczonych danych projektu B+R wygeneruj profesjonalną Kartę Projektową.
Dokument powinien zawierać:
1. Pełną identyfikację projektu
2. Szczegółowy opis celów badawczych i hipotez
3. Listę zespołu z rolami
4. Zestawienie kosztów według kategorii

Użyj formalnego języka urzędowego. Wszystkie kwoty formatuj z separatorem tysięcy i symbolem PLN."""
        ))
        
        self.register(DocumentTemplate(
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
            template_content="""# REJESTR CZASU PRACY - PROJEKT B+R

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
""",
            llm_prompt="""Wygeneruj miesięczny rejestr czasu pracy dla projektu B+R.
Podsumuj godziny każdego pracownika i opisz wykonane zadania.
Oblicz statystyki zbiorcze."""
        ))
        
        self.register(DocumentTemplate(
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
            template_content="""# EWIDENCJA WYDATKÓW B+R

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
""",
            llm_prompt="""Wygeneruj ewidencję wydatków B+R na podstawie dostarczonych danych.
Dla każdego wydatku podaj uzasadnienie kwalifikacji do B+R.
Podsumuj według kategorii i oblicz procent kwalifikowanych."""
        ))
        
        self.register(DocumentTemplate(
            id="nexus_calculation",
            name="Obliczenie Wskaźnika Nexus",
            description="Kalkulacja wskaźnika Nexus dla potrzeb IP Box",
            category=DocumentCategory.TAX,
            time_scope=TimeScope.YEARLY,
            data_requirements=[
                TemplateDataRequirement(
                    source_name="project_info",
                    required_params=["project_id"],
                    description="Informacje o projekcie"
                ),
                TemplateDataRequirement(
                    source_name="nexus_calculation",
                    required_params=["project_id"],
                    optional_params=["year"],
                    description="Dane do obliczenia Nexus"
                ),
                TemplateDataRequirement(
                    source_name="revenues",
                    required_params=["project_id"],
                    optional_params=["year"],
                    description="Przychody z IP"
                )
            ],
            template_content="""# OBLICZENIE WSKAŹNIKA NEXUS - IP BOX

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
""",
            llm_prompt="""Wykonaj obliczenie wskaźnika Nexus dla IP Box na podstawie dostarczonych danych.
Wyjaśnij każdy składnik wzoru i jego źródło.
Oblicz dochód kwalifikowany i należny podatek."""
        ))
        
        self.register(DocumentTemplate(
            id="br_annual_summary",
            name="Roczne Podsumowanie B+R",
            description="Kompleksowe roczne zestawienie działalności B+R dla celów podatkowych",
            category=DocumentCategory.REPORT,
            time_scope=TimeScope.YEARLY,
            data_requirements=[
                TemplateDataRequirement(
                    source_name="project_info",
                    required_params=["project_id"],
                    description="Informacje o projekcie"
                ),
                TemplateDataRequirement(
                    source_name="expenses_by_category",
                    required_params=["project_id", "year"],
                    description="Wydatki według kategorii"
                ),
                TemplateDataRequirement(
                    source_name="timesheet_monthly_breakdown",
                    required_params=["project_id", "year"],
                    description="Godziny pracy miesięcznie"
                ),
                TemplateDataRequirement(
                    source_name="revenues",
                    required_params=["project_id", "year"],
                    description="Przychody"
                ),
                TemplateDataRequirement(
                    source_name="nexus_calculation",
                    required_params=["project_id", "year"],
                    description="Wskaźnik Nexus"
                )
            ],
            template_content="""# ROCZNE PODSUMOWANIE DZIAŁALNOŚCI B+R

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
""",
            llm_prompt="""Wygeneruj kompleksowe roczne podsumowanie działalności B+R.
Dokument powinien zawierać:
1. Pełne zestawienie kosztów kwalifikowanych według kategorii
2. Miesięczne rozbicie godzin pracy dla każdego pracownika
3. Przychody z IP z oznaczeniem kwalifikacji IP Box
4. Obliczenie wskaźnika Nexus
5. Podsumowanie korzyści podatkowych

Użyj profesjonalnego języka. Wszystkie kwoty w PLN z formatowaniem."""
        ))
        
        self.register(DocumentTemplate(
            id="br_contract",
            name="Umowa o Świadczenie Usług B+R",
            description="Wzór umowy na realizację prac badawczo-rozwojowych",
            category=DocumentCategory.LEGAL,
            time_scope=TimeScope.PROJECT,
            data_requirements=[
                TemplateDataRequirement(
                    source_name="project_info",
                    required_params=["project_id"],
                    description="Informacje o projekcie"
                ),
                TemplateDataRequirement(
                    source_name="workers",
                    required_params=["project_id"],
                    description="Dane pracowników"
                )
            ],
            template_content="""# UMOWA O ŚWIADCZENIE USŁUG BADAWCZO-ROZWOJOWYCH

Nr umowy: _____________________

zawarta w dniu {{generated_date}} w _____________________

pomiędzy:

**Zleceniodawcą (Zamawiającym):**
- Nazwa: _____________________
- Siedziba: _____________________
- NIP: _____________________
- reprezentowanym przez: _____________________

a

**Zleceniobiorcą (Wykonawcą):**
- Nazwa: _____________________
- Siedziba: _____________________
- NIP: _____________________
- reprezentowanym przez: _____________________

---

## § 1. PRZEDMIOT UMOWY

1. Wykonawca zobowiązuje się do realizacji następujących prac badawczo-rozwojowych:

   **Projekt:** {{project.name}}
   
   **Kod projektu:** {{project.code}}
   
   **Opis prac:**
   {{project.description}}
   
   **Cel i przewidywany rezultat:**
   {{project.hypothesis}}

2. Prace stanowią działalność badawczo-rozwojową w rozumieniu art. 4a pkt 26-28 ustawy o CIT / art. 5a pkt 38-40 ustawy o PIT.

---

## § 2. WARUNKI FINANSOWE

1. Okres realizacji: od {{project.start_date}} do {{project.end_date}}

2. Wynagrodzenie za usługi: _________ PLN netto (plus VAT 23%)

3. Rozliczenie:
   - Miesięcznie: ___% wartości
   - Po zakończeniu: ___% wartości

4. Dokumenty rozliczeniowe: Faktury VAT

---

## § 3. OBOWIĄZKI WYKONAWCY

Wykonawca zobowiązuje się do:

1. Realizacji prac zgodnie z harmonogramem
2. Prowadzenia ewidencji czasu pracy w projekcie
3. Zbierania i archiwizowania dowodów wydatków
4. Raportowania postępu prac (co _____ dni)
5. Przekazywania dokumentacji zgodnie z § 6

---

## § 4. OBOWIĄZKI ZAMAWIAJĄCEGO

Zamawiający zobowiązuje się do:

1. Zapewnienia warunków do realizacji prac
2. Terminowego opłacania faktur (_____ dni od otrzymania)
3. Dostarczania informacji niezbędnych do realizacji prac
4. Udostępniania zasobów określonych w Załączniku nr 1

---

## § 5. WŁASNOŚĆ INTELEKTUALNA

1. Prawa do wyników prac badawczo-rozwojowych:
   [ ] W pełni przechodzą na Zamawiającego
   [ ] Dzielone między strony (proporcja: _______)
   [ ] Pozostają u Wykonawcy (licencja dla Zamawiającego)

2. Przeniesienie praw następuje z chwilą zapłaty wynagrodzenia.

---

## § 6. DOKUMENTACJA B+R

Wykonawca przekaże Zamawiającemu:

1. Raporty z postępu prac (co _____ dni)
2. Ewidencję czasu pracy (do 5. dnia następnego miesiąca)
3. Kopie faktur za materiały i usługi (na bieżąco)
4. Raport końcowy (w ciągu 14 dni od zakończenia)

---

## § 7. CELE PODATKOWE

1. Strony potwierdzają, że niniejsza umowa zawierana jest w celu realizacji działalności badawczo-rozwojowej kwalifikującej się do ulgi B+R.

2. Zamawiający zamierza korzystać z ulgi B+R w zakresie rozliczenia kosztów niniejszej umowy.

3. Wykonawca zobowiązuje się do dostarczania dokumentacji umożliwiającej prawidłowe rozliczenie ulgi.

---

## § 8. POSTANOWIENIA KOŃCOWE

1. Umowa wchodzi w życie z dniem podpisania.
2. Zmiany umowy wymagają formy pisemnej pod rygorem nieważności.
3. W sprawach nieuregulowanych stosuje się przepisy Kodeksu cywilnego.
4. Spory rozstrzygane będą przez sąd właściwy dla siedziby Zamawiającego.

---

**ZLECENIODAWCA:**

_____________________
(podpis, pieczęć)

**ZLECENIOBIORCA:**

_____________________
(podpis, pieczęć)

---

*Załączniki:*
1. Harmonogram prac i kosztorys
2. Specyfikacja techniczna
3. Wzór ewidencji czasu pracy
""",
            llm_prompt="""Wygeneruj profesjonalną umowę o świadczenie usług B+R.
Uwzględnij wszystkie wymagane elementy prawne i podatkowe.
Dostosuj treść do specyfiki projektu."""
        ))
        
        self.register(DocumentTemplate(
            id="ip_box_procedure",
            name="Procedura Wewnętrzna IP Box",
            description="Dokument opisujący wewnętrzne procedury stosowania preferencji IP Box",
            category=DocumentCategory.TAX,
            time_scope=TimeScope.PROJECT,
            data_requirements=[
                TemplateDataRequirement(
                    source_name="project_info",
                    required_params=["project_id"],
                    description="Informacje o projekcie"
                )
            ],
            template_content="""# PROCEDURA WEWNĘTRZNA - STOSOWANIE IP BOX

**Podmiot:** _____________________

**NIP:** _____________________

**Data wdrożenia:** {{generated_date}}

---

## 1. CEL PROCEDURY

Niniejsza procedura określa zasady identyfikacji, ewidencji i rozliczania kwalifikowanych praw własności intelektualnej (IP) dla potrzeb zastosowania preferencyjnej stawki podatku 5% (IP Box).

---

## 2. IDENTYFIKACJA KWALIFIKOWANEGO IP

### 2.1 Rodzaje kwalifikowanego IP

Procedura obejmuje następujące kategorie IP:

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

Dla każdego kwalifikowanego IP prowadzi się odrębną ewidencję zawierającą:

1. **Przychody z IP:**
   - Sprzedaż licencji
   - Opłaty licencyjne
   - Przychody z usług wykorzystujących IP

2. **Koszty bezpośrednie:**
   - Wynagrodzenia pracowników B+R
   - Materiały i surowce
   - Usługi zewnętrzne

3. **Koszty pośrednie (dla Nexus):**
   - Koszty od podmiotów powiązanych
   - Koszty zakupu gotowego IP

### 3.2 Terminy aktualizacji

| Czynność | Termin |
|----------|--------|
| Rejestracja przychodów | Na bieżąco |
| Rejestracja kosztów | Do 5. dnia następnego miesiąca |
| Podsumowanie miesięczne | Do 10. dnia następnego miesiąca |
| Obliczenie Nexus | Rocznie, do 31 stycznia |

---

## 4. OBLICZANIE WSKAŹNIKA NEXUS

### 4.1 Wzór

```
Nexus = ((a + b) × 1,3) / (a + b + c + d)
```

Gdzie:
- **a** = koszty B+R poniesione bezpośrednio
- **b** = koszty nabycia B+R od podmiotów niepowiązanych
- **c** = koszty nabycia B+R od podmiotów powiązanych
- **d** = koszty zakupu gotowego IP

### 4.2 Zasady

1. Wskaźnik Nexus nie może przekroczyć 1
2. Obliczany oddzielnie dla każdego IP
3. W przypadku braku kosztów przyjmuje się wartość 1

---

## 5. ROZLICZENIE W ZEZNANIU ROCZNYM

### 5.1 Dochód kwalifikowany

```
Dochód kwalifikowany = Dochód z IP × Wskaźnik Nexus
```

### 5.2 Opodatkowanie

- Dochód kwalifikowany: stawka 5%
- Pozostały dochód: stawka standardowa (19% / skala)

---

## 6. PRZECHOWYWANIE DOKUMENTACJI

### 6.1 Zakres archiwizacji

1. Ewidencje IP Box
2. Faktury i dokumenty kosztowe
3. Umowy dotyczące komercjalizacji IP
4. Dokumenty rejestracyjne IP
5. Zeznania podatkowe

### 6.2 Okres przechowywania

Minimum 5 lat od końca roku, w którym złożono zeznanie.

---

## 7. ODPOWIEDZIALNOŚĆ

| Rola | Zakres odpowiedzialności |
|------|-------------------------|
| Kierownik projektu | Identyfikacja IP, nadzór nad ewidencją |
| Księgowość | Prowadzenie ewidencji, obliczenia |
| Zarząd | Zatwierdzenie procedury, nadzór |

---

## 8. ZAŁĄCZNIKI

1. Wzór ewidencji IP Box (Excel)
2. Wzór obliczenia Nexus
3. Checklist rocznego rozliczenia

---

**Zatwierdzam:**

_____________________
(podpis, data)
""",
            llm_prompt="""Wygeneruj procedurę wewnętrzną IP Box dostosowaną do specyfiki projektu.
Uwzględnij wszystkie wymagane elementy ewidencyjne i obliczeniowe."""
        ))
        
        self.register(DocumentTemplate(
            id="tax_interpretation_request",
            name="Wniosek o Interpretację Indywidualną",
            description="Wzór wniosku do KIS o interpretację przepisów B+R/IP Box",
            category=DocumentCategory.TAX,
            time_scope=TimeScope.PROJECT,
            data_requirements=[
                TemplateDataRequirement(
                    source_name="project_info",
                    required_params=["project_id"],
                    description="Informacje o projekcie"
                ),
                TemplateDataRequirement(
                    source_name="expenses_by_category",
                    required_params=["project_id"],
                    description="Struktura kosztów"
                )
            ],
            template_content="""# WNIOSEK O WYDANIE INTERPRETACJI INDYWIDUALNEJ

**Do:** Dyrektor Krajowej Informacji Skarbowej

**Od:**
- Nazwa/Imię i nazwisko: _____________________
- NIP: _____________________
- Adres: _____________________

**Data:** {{generated_date}}

---

## I. OPIS ZDARZENIA PRZYSZŁEGO

Wnioskodawca prowadzi działalność gospodarczą w zakresie _____________________. 

W ramach tej działalności realizuje projekt badawczo-rozwojowy:

**Nazwa projektu:** {{project.name}}

**Kod projektu:** {{project.code}}

**Opis projektu:**
{{project.description}}

**Problem techniczny:**
{{project.technical_problem}}

**Hipoteza badawcza:**
{{project.hypothesis}}

### Struktura kosztów projektu:

| Kategoria | Szacowana kwota roczna |
|-----------|----------------------|
{% for cat in expenses_by_category %}
| {{cat.category}} | {{cat.total_gross|format_currency}} |
{% endfor %}

---

## II. PYTANIA

### Pytanie 1: Kwalifikacja działalności jako B+R

Czy opisana powyżej działalność stanowi działalność badawczo-rozwojową w rozumieniu art. 4a pkt 26 ustawy o podatku dochodowym od osób prawnych (odpowiednio art. 5a pkt 38 ustawy o PIT)?

### Pytanie 2: Kwalifikacja kosztów

Czy wymienione kategorie kosztów stanowią koszty kwalifikowane, o których mowa w art. 18d ustawy o CIT (odpowiednio art. 26e ustawy o PIT), uprawniające do odliczenia w ramach ulgi B+R?

### Pytanie 3: Kwalifikowane IP

Czy wytwarzane w ramach projektu oprogramowanie stanowi kwalifikowane prawo własności intelektualnej w rozumieniu art. 24d ust. 2 pkt 8 ustawy o CIT, uprawniające do zastosowania preferencyjnej stawki 5%?

### Pytanie 4: Wskaźnik Nexus

Jak prawidłowo obliczyć wskaźnik Nexus w przypadku, gdy Wnioskodawca ponosi wyłącznie koszty bezpośrednie działalności B+R (kategoria "a" we wzorze)?

---

## III. STANOWISKO WNIOSKODAWCY

### Ad. Pytanie 1:
Zdaniem Wnioskodawcy, opisana działalność spełnia wszystkie przesłanki działalności badawczo-rozwojowej:
1. Ma charakter twórczy
2. Jest prowadzona w sposób systematyczny
3. Zmierza do zwiększenia zasobów wiedzy i wykorzystania ich do nowych zastosowań

### Ad. Pytanie 2:
Zdaniem Wnioskodawcy, wszystkie wymienione kategorie kosztów stanowią koszty kwalifikowane...

### Ad. Pytanie 3:
Zdaniem Wnioskodawcy, wytwarzane oprogramowanie stanowi kwalifikowane IP...

### Ad. Pytanie 4:
Zdaniem Wnioskodawcy, w przypadku braku kosztów kategorii "b", "c" i "d", wskaźnik Nexus wynosi 1...

---

## IV. OŚWIADCZENIE

Oświadczam, że elementy stanu faktycznego objęte wnioskiem o wydanie interpretacji w dniu złożenia wniosku nie są przedmiotem toczącego się postępowania podatkowego, kontroli podatkowej, kontroli celno-skarbowej oraz że w tym zakresie sprawa nie została rozstrzygnięta co do jej istoty w decyzji lub postanowieniu organu podatkowego.

---

_____________________
(podpis Wnioskodawcy)

---

*Załączniki:*
1. Dowód uiszczenia opłaty (40 PLN)
2. Pełnomocnictwo (jeśli dotyczy)
""",
            llm_prompt="""Wygeneruj wniosek o interpretację indywidualną do KIS.
Szczegółowo opisz stan faktyczny projektu B+R.
Sformułuj precyzyjne pytania dotyczące kwalifikacji B+R i IP Box.
Przedstaw stanowisko wnioskodawcy z argumentacją prawną."""
        ))
    
    def register(self, template: DocumentTemplate):
        """Register a new template"""
        self._templates[template.id] = template
    
    def get(self, template_id: str) -> Optional[DocumentTemplate]:
        """Get a template by ID"""
        return self._templates.get(template_id)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates with metadata"""
        return [t.to_dict() for t in self._templates.values()]
    
    def get_by_category(self, category: DocumentCategory) -> List[DocumentTemplate]:
        """Get all templates in a category"""
        return [t for t in self._templates.values() if t.category == category]
    
    def get_by_time_scope(self, scope: TimeScope) -> List[DocumentTemplate]:
        """Get all templates with a specific time scope"""
        return [t for t in self._templates.values() if t.time_scope == scope]


def get_template_registry() -> TemplateRegistry:
    """Get singleton instance of template registry"""
    return TemplateRegistry()
