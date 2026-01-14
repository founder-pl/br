"""
Prompt templates for B+R documentation.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PromptTemplate:
    """Template for LLM prompts"""
    name: str
    system_prompt: str
    user_prompt_template: str
    description: str = ""
    
    def format(self, **kwargs) -> tuple[str, str]:
        """Format prompt with variables"""
        return self.system_prompt, self.user_prompt_template.format(**kwargs)


# B+R-specific prompts
BR_PROMPTS = {
    "expense_qualification": PromptTemplate(
        name="expense_qualification",
        description="Qualify expense for B+R deduction",
        system_prompt="""Jesteś ekspertem od ulgi B+R w Polsce (art. 18d ustawy o CIT).
Twoim zadaniem jest analiza wydatków i określenie ich kwalifikowalności do odliczenia B+R.

Kategorie kosztów kwalifikowanych:
- Wynagrodzenia pracowników (UoP) - proporcjonalnie do czasu B+R
- Umowy cywilnoprawne (dzieło, zlecenie) - gdy dotyczą B+R
- Materiały i surowce - bezpośrednio zużyte w B+R
- Sprzęt specjalistyczny - wykorzystywany wyłącznie do B+R
- Usługi zewnętrzne (od podmiotów niepowiązanych)
- Amortyzacja środków trwałych używanych w B+R

Odpowiadaj w formacie JSON.""",
        user_prompt_template="""Przeanalizuj następujący wydatek:

Opis: {description}
Kwota: {amount} PLN
Kontrahent: {vendor}
Kategoria: {category}
Data: {date}

Określ:
1. Czy wydatek kwalifikuje się do ulgi B+R? (tak/nie)
2. Jeśli tak, do jakiej kategorii należy?
3. Uzasadnienie kwalifikacji
4. Potencjalne ryzyka przy kontroli US

Odpowiedz w formacie JSON:
{{
    "qualified": true/false,
    "category": "nazwa_kategorii",
    "justification": "uzasadnienie",
    "risks": ["ryzyko1", "ryzyko2"],
    "confidence": 0.0-1.0
}}""",
    ),
    
    "document_review": PromptTemplate(
        name="document_review",
        description="Review B+R document for completeness",
        system_prompt="""Jesteś ekspertem od dokumentacji B+R.
Sprawdzasz dokumenty pod kątem kompletności, poprawności i zgodności z wymogami prawnymi.

Zwracaj uwagę na:
- Kompletność sekcji
- Poprawność obliczeń
- Zgodność z art. 18d CIT
- Spójność danych""",
        user_prompt_template="""Sprawdź poniższy dokument B+R:

---
{document_content}
---

Typ dokumentu: {document_type}
Rok podatkowy: {year}

Oceń:
1. Kompletność dokumentu (0-100%)
2. Lista brakujących elementów
3. Znalezione błędy lub niespójności
4. Rekomendacje poprawek

Odpowiedz w formacie JSON.""",
    ),
    
    "nexus_explanation": PromptTemplate(
        name="nexus_explanation",
        description="Explain Nexus calculation for IP Box",
        system_prompt="""Jesteś ekspertem od IP Box w Polsce (art. 24d ustawy o CIT).
Wyjaśniasz obliczenia wskaźnika Nexus w przystępny sposób.""",
        user_prompt_template="""Wyjaśnij obliczenie wskaźnika Nexus:

Składniki:
- a (koszty bezpośrednie B+R): {a} PLN
- b (usługi od podmiotów niepowiązanych): {b} PLN
- c (usługi od podmiotów powiązanych): {c} PLN
- d (zakup gotowego IP): {d} PLN

Wzór: Nexus = min(1, ((a + b) × 1.3) / (a + b + c + d))
Obliczony Nexus: {nexus}

Wyjaśnij:
1. Co oznacza ten wskaźnik dla podatnika
2. Jak wpływa na wysokość ulgi IP Box
3. Czy są optymalizacje możliwe do zastosowania
4. Rekomendacje na przyszłość""",
    ),
    
    "project_summary": PromptTemplate(
        name="project_summary",
        description="Generate project summary for B+R",
        system_prompt="""Generujesz profesjonalne podsumowania projektów B+R.
Styl: formalny, rzeczowy, zgodny z wymogami dokumentacji podatkowej.""",
        user_prompt_template="""Na podstawie danych wygeneruj podsumowanie projektu B+R:

Nazwa projektu: {project_name}
Okres: {start_date} - {end_date}
Koszty kwalifikowane: {qualified_costs} PLN
Liczba pracowników: {worker_count}
Godziny B+R: {total_hours}

Cele projektu:
{project_goals}

Wygeneruj formalne podsumowanie projektu zawierające:
1. Opis działalności badawczo-rozwojowej
2. Osiągnięte rezultaty
3. Innowacyjność rozwiązania
4. Wykorzystane zasoby""",
    ),
}


class PromptBuilder:
    """Builder for LLM prompts with B+R context"""
    
    def __init__(self, templates: Optional[Dict[str, PromptTemplate]] = None):
        self.templates = templates or BR_PROMPTS
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get template by name"""
        return self.templates.get(name)
    
    def build(self, template_name: str, **kwargs) -> tuple[str, str]:
        """Build prompt from template"""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")
        return template.format(**kwargs)
    
    def build_expense_qualification(
        self,
        description: str,
        amount: float,
        vendor: str,
        category: str,
        date: str,
    ) -> tuple[str, str]:
        """Build expense qualification prompt"""
        return self.build(
            "expense_qualification",
            description=description,
            amount=amount,
            vendor=vendor,
            category=category,
            date=date,
        )
    
    def build_document_review(
        self,
        document_content: str,
        document_type: str,
        year: int,
    ) -> tuple[str, str]:
        """Build document review prompt"""
        return self.build(
            "document_review",
            document_content=document_content,
            document_type=document_type,
            year=year,
        )
    
    def build_nexus_explanation(
        self,
        a: float,
        b: float,
        c: float,
        d: float,
        nexus: float,
    ) -> tuple[str, str]:
        """Build Nexus explanation prompt"""
        return self.build(
            "nexus_explanation",
            a=a,
            b=b,
            c=c,
            d=d,
            nexus=nexus,
        )
