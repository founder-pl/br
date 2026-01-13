# Articles – Status Projektów Softreck

Repozytorium artykułów WordPress dokumentujących status projektów w organizacji.

## Zawartość

| # | Artykuł | Opis | Status |
|---|---------|------|--------|
| 01 | [BR Project Status Analysis](01-br-project-status-analysis.md) | Analiza stanu projektu BR i identyfikacja problemów jakościowych | ✅ Gotowy |
| 02 | [BR Refactoring Plan](02-br-refactoring-plan.md) | Szczegółowy plan refaktoryzacji z kodem implementacji | ✅ Gotowy |
| 03 | [BR Documentation Best Practices](03-br-documentation-best-practices.md) | Rekomendacje jakościowe dla dokumentacji B+R | ✅ Gotowy |
| 04 | [BR Technical Architecture](04-br-technical-architecture.md) | Przegląd architektury technicznej projektu | ✅ Gotowy |
| 05 | [BR Priority Roadmap](05-br-priority-roadmap.md) | Priorytety i roadmap rozwoju Q1 2026 | ✅ Gotowy |

## Projekt BR – Podsumowanie

**Problem główny:** Generowane raporty B+R mają niską jakość i mogą nie przejść kontroli skarbowej.

### Kluczowe ustalenia:

1. **Generyczne uzasadnienia** – wszystkie wydatki mają identyczny tekst
2. **Niespójność danych** – brakujące dostawcy, numery faktur, waluty w USD
3. **Brak wymaganych sekcji** – niepewność technologiczna, metodologia
4. **Ewidencja czasu** – tylko suma godzin, brak dziennego rejestru

### Rekomendowane działania:

1. Wdrożyć LLM-based indywidualizację uzasadnień (P0)
2. Dodać walidację i konwersję walut (P0)
3. Rozbudować strukturę dokumentacji o wymagane sekcje (P1)
4. Implementować dzienną ewidencję czasu z integracją Git (P1)

## Struktura Artykułów

Każdy artykuł jest w formacie Markdown gotowym do importu do WordPress:
- Nagłówki zgodne z hierarchią WordPress (H1 = tytuł, H2 = sekcje)
- Tabele w formacie Markdown
- Bloki kodu z syntax highlighting
- Brak obrazów (do dodania w WordPress)

## Import do WordPress

```bash
# Opcja 1: WP-CLI
wp post create 01-br-project-status-analysis.md --post_type=post --post_status=draft

# Opcja 2: REST API
curl -X POST https://your-site.com/wp-json/wp/v2/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"BR Project Status","content":"...","status":"draft"}'
```

## Harmonogram Publikacji

| Data | Artykuł | Kategoria |
|------|---------|-----------|
| 2026-01-14 | 01 - Analiza | Projekty |
| 2026-01-15 | 05 - Roadmap | Projekty |
| 2026-01-17 | 03 - Best Practices | Poradniki |
| 2026-01-20 | 02 - Refactoring | Techniczne |
| 2026-01-22 | 04 - Architektura | Techniczne |

---

*Wygenerowano: 2026-01-13*
