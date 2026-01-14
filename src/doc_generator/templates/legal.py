"""
Legal Templates - Legal document templates (contracts, agreements)
"""
from typing import List
from .base import DocumentTemplate, DocumentCategory, TimeScope, TemplateDataRequirement


def get_legal_templates() -> List[DocumentTemplate]:
    """Return all legal templates"""
    return [
        DocumentTemplate(
            id="br_contract",
            name="Umowa o Świadczenie Usług B+R",
            description="Wzór umowy na realizację prac badawczo-rozwojowych",
            category=DocumentCategory.LEGAL,
            time_scope=TimeScope.PROJECT,
            data_requirements=[
                TemplateDataRequirement(source_name="project_info", required_params=["project_id"], description="Informacje o projekcie"),
                TemplateDataRequirement(source_name="workers", required_params=["project_id"], description="Dane pracowników")
            ],
            template_content=BR_CONTRACT_TEMPLATE,
            llm_prompt="Wygeneruj profesjonalną umowę o świadczenie usług B+R."
        )
    ]


BR_CONTRACT_TEMPLATE = """# UMOWA O ŚWIADCZENIE USŁUG BADAWCZO-ROZWOJOWYCH

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
"""
