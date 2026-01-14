"""
LLM Prompts and Constants for B+R Documentation Generation.
"""

# System prompt for B+R expense documentation
BR_EXPENSE_DOC_PROMPT = """Jesteś ekspertem w przygotowywaniu dokumentacji do polskiej ulgi badawczo-rozwojowej (B+R).
Generujesz profesjonalną dokumentację wydatku zgodną z wymaganiami art. 18d ustawy o CIT.

Dokumentacja wydatku B+R musi zawierać:
1. Identyfikację wydatku (nr faktury, data, dostawca)
2. Opis związku z działalnością B+R
3. Klasyfikację kategorii kosztów (wg CIT)
4. Uzasadnienie kwalifikowalności do odliczenia
5. Kwotę odliczenia i zastosowaną stawkę

Używaj języka formalnego, technicznego, odpowiedniego dla dokumentacji podatkowej.
Pisz w języku polskim."""


# LLM refinement prompt
LLM_REFINEMENT_PROMPT = """Jesteś ekspertem w dokumentacji B+R (ulga badawczo-rozwojowa w Polsce).

Poniższy dokument B+R zawiera błędy/ostrzeżenia wykryte podczas walidacji:

PROBLEMY DO NAPRAWY:
{issues}

AKTUALNY DOKUMENT:
{document}

Twoim zadaniem jest poprawić TYLKO wskazane problemy, zachowując resztę dokumentu bez zmian.
Zwróć poprawiony dokument w formacie Markdown.

ZASADY:
1. Zachowaj strukturę sekcji (nagłówki ##)
2. Popraw brakujące dane gdzie to możliwe
3. Uzupełnij uzasadnienia B+R dla wydatków
4. Nie zmieniaj danych liczbowych (kwot, NIP-ów)
5. Zachowaj tabele w poprawnym formacie Markdown

Odpowiedz TYLKO poprawionym dokumentem, bez dodatkowych komentarzy."""


# Category names mapping
CATEGORY_NAMES = {
    'personnel_employment': 'Wynagrodzenia pracowników (umowa o pracę)',
    'personnel_civil': 'Wynagrodzenia (umowy cywilnoprawne)',
    'materials': 'Materiały i surowce',
    'equipment': 'Sprzęt specjalistyczny',
    'depreciation': 'Amortyzacja',
    'expertise': 'Ekspertyzy i opinie',
    'external_services': 'Usługi zewnętrzne',
    'other': 'Inne koszty kwalifikowane'
}


# Category names with deduction rates
CATEGORY_NAMES_WITH_RATES = {
    'personnel_employment': 'Wynagrodzenia pracowników (umowa o pracę) - 200%',
    'personnel_civil': 'Wynagrodzenia (umowy cywilnoprawne) - 200%',
    'materials': 'Materiały i surowce - 100%',
    'equipment': 'Sprzęt specjalistyczny - 100%',
    'depreciation': 'Amortyzacja - 100%',
    'expertise': 'Ekspertyzy i opinie - 100%',
    'external_services': 'Usługi zewnętrzne - 100%',
    'other': 'Inne koszty kwalifikowane - 100%'
}


# Month names in Polish
MONTH_NAMES_PL = {
    1: 'Styczeń', 2: 'Luty', 3: 'Marzec', 4: 'Kwiecień',
    5: 'Maj', 6: 'Czerwiec', 7: 'Lipiec', 8: 'Sierpień',
    9: 'Wrzesień', 10: 'Październik', 11: 'Listopad', 12: 'Grudzień'
}
