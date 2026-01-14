# Articles - Status Projektów Softreck

Repozytorium zawiera artykuły WordPress dokumentujące status projektów w organizacji Softreck/Founder.pl.

## Struktura

```
articles/
├── README.md                           # Ten plik
├── br-generator-todo.md               # Lista TODO dla LLM
├── br-generator-status.md             # Status projektu BR Generator
└── br-generator-validation-system.md  # Architektura systemu walidacji
```

## Projekty

### 1. BR Documentation Generator

**Status**: W aktywnym rozwoju  
**Technologie**: Python, FastAPI, PostgreSQL, OpenRouter LLM

Artykuły:
- [Lista TODO dla LLM](br-generator-todo.md) - Szczegółowe zadania do implementacji
- [Status projektu](br-generator-status.md) - Przegląd funkcjonalności i roadmapa
- [System walidacji](br-generator-validation-system.md) - Dokumentacja techniczna

### 2. Prototypowanie.pl

*Artykuł w przygotowaniu*

### 3. Portigen.com

*Artykuł w przygotowaniu*

### 4. Code2Logic

*Artykuł w przygotowaniu*

---

## Formatowanie dla WordPress

Wszystkie artykuły są w formacie Markdown i mogą być bezpośrednio importowane do WordPress z pluginem Markdown (np. Jetpack Markdown, WP-Markdown).

### Wymagane pluginy WordPress

1. **Jetpack** - Markdown support
2. **Syntax Highlighter** - Kolorowanie kodu
3. **Table of Contents Plus** - Automatyczne spisy treści

### Import do WordPress

```bash
# Konwersja Markdown → HTML (opcjonalnie)
pandoc article.md -o article.html

# Lub użyj wp-cli
wp post create --post_type=post --post_title="Tytuł" --post_content="$(cat article.md)"
```

---

## Licencja

© 2026 Softreck. Wszystkie prawa zastrzeżone.
