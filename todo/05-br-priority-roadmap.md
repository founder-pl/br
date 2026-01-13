# Priorytety Rozwoju Projektu BR – Roadmap Q1 2026

**Data publikacji:** 2026-01-13  
**Status:** Aktywny rozwój  
**Sprint aktualny:** Refaktoryzacja jakości dokumentacji  

## Executive Summary

Projekt BR wymaga pilnej refaktoryzacji w obszarze generowania uzasadnień wydatków i kompletności dokumentacji. Obecna jakość raportów nie spełnia wymogów kontroli skarbowej.

## Priorytety według Pilności

### P0 – Krytyczne (Tydzień 1-2)

| # | Zadanie | Estymacja | Odpowiedzialny |
|---|---------|-----------|----------------|
| 1 | Indywidualizacja uzasadnień wydatków | 3 dni | Backend |
| 2 | Walidacja numerów faktur (eliminacja "faktury", "sprzedazy") | 1 dzień | Backend |
| 3 | Konwersja walut USD→PLN z kursem NBP | 1 dzień | Backend |
| 4 | Uzupełnienie brakujących danych dostawców | 2 dni | Data |

**Kryteria akceptacji P0:**
- [ ] 0% generycznych uzasadnień w raporcie
- [ ] 0 faktur z generycznymi numerami
- [ ] 100% kwot w PLN
- [ ] 100% wydatków z danymi dostawcy

### P1 – Wysoki (Tydzień 3-4)

| # | Zadanie | Estymacja | Odpowiedzialny |
|---|---------|-----------|----------------|
| 5 | Sekcja niepewności technologicznej | 2 dni | Generator |
| 6 | Rozbudowa opisu projektu (problem techniczny) | 2 dni | Generator |
| 7 | Dzienny rejestr czasu pracy | 3 dni | Backend |
| 8 | Integracja z Git dla ewidencji | 2 dni | Backend |

**Kryteria akceptacji P1:**
- [ ] Sekcja "Niepewność technologiczna" obecna w każdym raporcie
- [ ] Opis projektu >500 słów
- [ ] Ewidencja czasu z dzienną granularnością
- [ ] Powiązanie wpisów z commitami Git

### P2 – Średni (Tydzień 5-6)

| # | Zadanie | Estymacja | Odpowiedzialny |
|---|---------|-----------|----------------|
| 9 | Pipeline walidacji – nowe reguły | 3 dni | Walidator |
| 10 | Automatyczna kategoryzacja wydatków | 3 dni | ML |
| 11 | Event sourcing dla audit trail | 4 dni | Backend |

### P3 – Niski (Tydzień 7-8)

| # | Zadanie | Estymacja | Odpowiedzialny |
|---|---------|-----------|----------------|
| 12 | Refaktoryzacja expenses.py | 2 dni | Backend |
| 13 | Plugin architecture dla walidatorów | 3 dni | Architektura |
| 14 | Dokumentacja API | 2 dni | Docs |

## Metryki Sukcesu

### Jakość Dokumentacji

| Metryka | Obecnie | Cel | Deadline |
|---------|---------|-----|----------|
| Unikalność uzasadnień | 0% | 100% | Tydzień 2 |
| Kompletność sekcji | 50% | 100% | Tydzień 4 |
| Walidacja danych | 36% | 95% | Tydzień 2 |
| Ewidencja dzienna | 0% | 100% | Tydzień 4 |

### Jakość Kodu

| Metryka | Obecnie | Cel | Deadline |
|---------|---------|-----|----------|
| Złożoność cyklomatyczna | ~35 | <15 | Tydzień 8 |
| Pokrycie testami | ? | >80% | Tydzień 8 |
| Dokumentacja funkcji | ? | 100% | Tydzień 8 |

## Ryzyka

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitygacja |
|--------|-------------------|-------|-----------|
| Opóźnienia w P0 | Średnie | Krytyczny | Daily standup, pair programming |
| API NBP niedostępne | Niskie | Średni | Cache kursów, fallback na średni kurs |
| Regresje w generatorze | Średnie | Wysoki | Testy e2e przed każdym deployem |

## Następny Sprint Review

**Data:** 2026-01-27  
**Cel:** Zamknięcie wszystkich zadań P0  
**Uczestnicy:** Team Dev, Product Owner  

---

*Roadmap aktualizowany co 2 tygodnie*
