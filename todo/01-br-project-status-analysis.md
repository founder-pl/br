# Projekt BR – Analiza Stanu i Identyfikacja Problemów Jakościowych

**Data publikacji:** 2026-01-13  
**Projekt:** BR Documentation Generator  
**Wersja:** 1.0  

## Podsumowanie

System BR to kompleksowe narzędzie do automatycznego generowania dokumentacji ulgi badawczo-rozwojowej (B+R) oraz IP Box dla polskich przedsiębiorstw. Projekt składa się z ~28 000 linii kodu Python rozłożonych na 90 modułów, z architekturą opartą o REST API, OCR, integracje z systemami księgowymi oraz silnik walidacji dokumentów.

Po przeprowadzonej analizie wygenerowanego raportu „Dokumentacja_Praktyczna_BR_IPBOX.md" zidentyfikowano krytyczne problemy wpływające na jakość dokumentacji i jej zgodność z wymogami prawnymi.

## Architektura Projektu

**Struktura modułowa:**
- `src/api/` – REST API z routerami dla wydatków, dokumentów, projektów, raportów
- `src/ocr/` – ekstrakcja danych z faktur (OCR + preprocessing)
- `src/integrations/` – połączenia z Fakturownia, wFirma, iFirma, Dropbox, Google Drive, S3
- `brgenerator/` – główny generator dokumentacji z pipeline'em walidacji

**Statystyki kodu:**
- 88 modułów Python, 2 moduły JavaScript
- 28 176 linii kodu
- Pokrycie testami: unit, integration, e2e

## Zidentyfikowane Problemy

### 1. Generyczne Uzasadnienia Wydatków

**Problem krytyczny:** Wszystkie wydatki w raporcie mają identyczne, szablonowe uzasadnienia:

> „Wydatek związany z realizacją prac badawczo-rozwojowych w ramach projektu. Stanowi koszt niezbędny do przeprowadzenia eksperymentów i testów prototypowych rozwiązań."

**Dlaczego to problem:**
- Organy skarbowe weryfikują substancję merytoryczną dokumentacji
- Identyczne uzasadnienia sugerują brak faktycznej analizy każdego wydatku
- Dokumentacja ma potwierdzać, a nie tworzyć kwalifikację – generyczne opisy tego nie spełniają

**Wymóg prawny:** Każdy wydatek musi być indywidualnie uzasadniony pod kątem jego związku z konkretnym zadaniem badawczo-rozwojowym.

### 2. Brak Konkretnego Opisu Projektu

**Problem:** Nazwa „Prototypowy system modularny" jest zbyt ogólna i nie spełnia wymogu identyfikacji projektu B+R.

**Brakujące elementy:**
- Szczegółowy opis problemu naukowego/technicznego rozwiązywanego przez projekt
- Charakterystyka innowacyjności w skali firmy
- Opis niepewności technologicznej (kluczowy element kwalifikacji B+R)
- Powiązanie wydatków z konkretnymi zadaniami badawczymi

### 3. Niespójność Danych Finansowych

**Zidentyfikowane błędy:**
- Wydatki w USD bez przeliczenia na PLN (pozycje 5, 6, 10)
- Brakujące dane dostawców (wartość `None`)
- Generyczne numery faktur: „faktury", „sprzedazy"
- 9 z 14 wydatków „oczekuje na klasyfikację" bez automatycznej kategoryzacji

**Tabela problematycznych pozycji:**

| # | Nr faktury | Problem | Kwota |
|---|------------|---------|-------|
| 5 | faktury | Brak dostawcy, waluta USD | 15.00 USD |
| 6 | SVFOB8UM-0001 | Brak dostawcy, waluta USD | 15.00 USD |
| 10 | faktury | Brak dostawcy, waluta USD | 15.00 USD |

### 4. Niedostateczna Ewidencja Czasu Pracy

**Obecny stan:** Raport zawiera jedynie łączną sumę godzin (280h) bez wymaganego rozbicia.

**Wymagania dokumentacyjne:**
- Dzienny rejestr prac B+R
- Przyporządkowanie godzin do konkretnych zadań/projektów
- Opis wykonanych czynności badawczo-rozwojowych
- Podział według kategorii prac (badania stosowane, prace rozwojowe)

### 5. Brak Kluczowych Sekcji Dokumentacji

**Nieobecne elementy wymagane przez przepisy:**
- Opis metodologii badawczej
- Kamienie milowe z konkretnymi datami i rezultatami
- Analiza ryzyka niepowodzenia (obligatoryjny element B+R)
- Opis elementu twórczego i systematyczności prac
- Dokumentacja niepewności technologicznej

## Wpływ na Kwalifikację B+R

Według objaśnień podatkowych Ministerstwa Finansów, działalność kwalifikuje się do ulgi B+R gdy:

1. **Systematyczność** – projekt realizowany według harmonogramu ✓ (częściowo spełnione)
2. **Twórczość** – oryginalne rozwiązania ✗ (brak opisu)
3. **Innowacyjność** – nowe w skali firmy ✗ (brak charakterystyki)
4. **Niepewność** – ryzyko niepowodzenia ✗ (całkowity brak)

**Ocena zgodności:** 1/4 kryteriów – dokumentacja w obecnej formie może nie zostać zaakceptowana podczas kontroli.

## Rekomendacje Natychmiastowe

1. **Wdrożyć indywidualizację uzasadnień** – każdy wydatek musi mieć unikalny opis powiązany z konkretnym zadaniem B+R
2. **Rozbudować opis projektu** – dodać sekcje o problemie technicznym, metodologii, innowacyjności
3. **Naprawić spójność danych** – przeliczenie walut, uzupełnienie dostawców, walidacja numerów faktur
4. **Implementować ewidencję czasu** – dzienny timesheet z opisem czynności
5. **Dodać analizę ryzyka** – obowiązkowa sekcja o niepewności technologicznej

## Następne Kroki

Szczegółowy plan refaktoryzacji przedstawiono w artykule „Plan Refaktoryzacji Systemu BR".

---

*Artykuł wygenerowany na podstawie analizy projektu BR v1.0*
