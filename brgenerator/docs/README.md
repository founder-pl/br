# Softreck Articles

Repozytorium artykułów WordPress opisujących status projektów w organizacji Softreck.

## Struktura

Każdy plik Markdown to osobny artykuł gotowy do publikacji w WordPress.

```
articles/
├── README.md                           # Ten plik
├── 01-br-project-status.md             # Status systemu B+R
└── 02-brgenerator-component.md    # Generator dokumentacji B+R
```

## Artykuły

### 01 - System B+R (ulga podatkowa)

Status głównego systemu do obsługi ulgi B+R:
- Architektura: FastAPI, PostgreSQL, Redis
- OCR: PaddleOCR, Tesseract, EasyOCR
- Integracje: 4 systemy księgowe, 6 platform chmurowych
- 54 moduły, 13,637 linii kodu

### 02 - BR Documentation Generator

Komponent do automatycznego generowania dokumentacji:
- Generator LLM przez LiteLLM
- 4-poziomowy pipeline walidacji
- Formularze YAML z komentarzami
- Export do PDF

## Publikacja w WordPress

### Metoda 1: Kopiuj-wklej

1. Otwórz plik `.md`
2. Skopiuj zawartość
3. W WordPress: Dodaj nowy wpis → Blok "Markdown" lub "Custom HTML"
4. Wklej zawartość

### Metoda 2: Plugin Markdown

Zainstaluj plugin np. "WP Githuber MD":
1. Zainstaluj i aktywuj plugin
2. Przy tworzeniu wpisu wybierz edytor Markdown
3. Wklej zawartość pliku

### Metoda 3: REST API

```bash
# Publikacja przez API
curl -X POST "https://twoja-strona.pl/wp-json/wp/v2/posts" \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "System B+R - Status projektu",
       "content": "'"$(cat 01-br-project-status.md)"'",
       "status": "draft"
     }'
```

## Format artykułów

Każdy artykuł zawiera:
- Tytuł (H1)
- Meta informacje (data, autor, tagi)
- Streszczenie
- Sekcje tematyczne
- Kod/diagramy (jeśli dotyczy)
- Podsumowanie

## Konwencje nazewnictwa

```
NN-nazwa-artykulu.md
```

- `NN` - numer porządkowy (01, 02, ...)
- `nazwa-artykulu` - slug (małe litery, myślniki)

## Autor

**Softreck** - [softreck.com](https://softreck.com)

## Licencja

MIT License
