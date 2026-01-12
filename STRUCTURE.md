# Struktura plików projektu System B+R

## Statystyki projektu

| Metryka | Wartość |
|---------|---------|
| **Plików ogółem** | 67 |
| **Plików Python** | 47 |
| **Plików testowych** | 12 |
| **Moduły integracji** | 14 |
| **Pliki dokumentacji** | 3 |

## Pełna lista plików

```
br-system/
│
├── 📄 .env.example                    # Przykładowa konfiguracja środowiska
├── 📄 .gitignore                      # Ignorowane pliki Git
├── 📄 docker-compose.yml              # Definicja serwisów Docker
├── 📄 Makefile                        # Komendy automatyzacji (40+ komend)
├── 📄 pytest.ini                      # Konfiguracja pytest
├── 📄 README.md                       # Główna dokumentacja
│
├── 📁 config/
│   └── 📄 litellm_config.yaml         # Konfiguracja LiteLLM (modele LLM)
│
├── 📁 docker/
│   ├── 📄 Dockerfile.api              # Dockerfile API Backend (FastAPI)
│   ├── 📄 Dockerfile.llm              # Dockerfile LLM Service (LiteLLM)
│   ├── 📄 Dockerfile.ocr              # Dockerfile OCR Service (PaddleOCR/Tesseract)
│   ├── 📄 Dockerfile.web              # Dockerfile Web Frontend (Nginx)
│   ├── 📄 init-db.sql                 # Skrypt inicjalizacji PostgreSQL
│   ├── 📄 nginx.conf                  # Konfiguracja Nginx
│   ├── 📄 requirements-api.txt        # Zależności Python dla API
│   └── 📄 requirements-ocr.txt        # Zależności Python dla OCR
│
├── 📁 docs/
│   ├── 📄 STRUCTURE.md                # Ten plik - dokumentacja struktury
│   └── 📄 INTEGRATIONS.md             # Dokumentacja integracji zewnętrznych
│
├── 📁 src/
│   │
│   ├── 📁 api/                        # API Backend (FastAPI)
│   │   ├── 📄 __init__.py
│   │   ├── 📄 config.py               # Konfiguracja aplikacji
│   │   ├── 📄 database.py             # Połączenie z bazą danych
│   │   ├── 📄 main.py                 # Główna aplikacja FastAPI
│   │   │
│   │   └── 📁 routers/                # Endpointy API
│   │       ├── 📄 __init__.py
│   │       ├── 📄 auth.py             # Autoryzacja (JWT)
│   │       ├── 📄 clarifications.py   # Pytania i wyjaśnienia
│   │       ├── 📄 documents.py        # Upload i zarządzanie dokumentami
│   │       ├── 📄 expenses.py         # Wydatki B+R
│   │       ├── 📄 integrations.py     # API integracji księgowych i cloud
│   │       ├── 📄 projects.py         # Projekty B+R
│   │       └── 📄 reports.py          # Raporty miesięczne/roczne
│   │
│   ├── 📁 infrastructure/             # Infrastruktura (Celery, tasks)
│   │   ├── 📄 __init__.py
│   │   ├── 📄 celery_app.py           # Konfiguracja Celery
│   │   └── 📄 tasks.py                # Zadania asynchroniczne
│   │
│   ├── 📁 integrations/               # Integracje zewnętrzne
│   │   ├── 📄 __init__.py             # Eksporty główne
│   │   ├── 📄 factory.py              # Factory do tworzenia klientów
│   │   │
│   │   ├── 📁 accounting/             # Programy księgowe
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 base.py             # Bazowy klient księgowy (ABC)
│   │   │   ├── 📄 ifirma.py           # Klient iFirma
│   │   │   ├── 📄 fakturownia.py      # Klient Fakturownia
│   │   │   └── 📄 wfirma_infakt.py    # Klienci wFirma i InFakt
│   │   │
│   │   ├── 📁 cloud/                  # Magazyny chmurowe
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 base.py             # Bazowy klient cloud (ABC)
│   │   │   ├── 📄 nextcloud.py        # Klient Nextcloud (WebDAV)
│   │   │   ├── 📄 google_s3.py        # Klienci Google Drive i S3/MinIO
│   │   │   └── 📄 dropbox_onedrive.py # Klienci Dropbox i OneDrive
│   │   │
│   │   └── 📁 config/                 # Konfiguracja integracji
│   │       ├── 📄 __init__.py
│   │       └── 📄 database.py         # SQLite/PostgreSQL config storage
│   │
│   └── 📁 ocr/                        # OCR Service
│       ├── 📄 __init__.py
│       ├── 📄 engines.py              # Silniki OCR (Tesseract, PaddleOCR)
│       ├── 📄 extractors.py           # Ekstrakcja danych z faktur
│       ├── 📄 main.py                 # Główna aplikacja OCR
│       ├── 📄 models.py               # Modele danych
│       └── 📄 preprocessing.py        # Preprocessing obrazów
│
├── 📁 tests/
│   ├── 📄 __init__.py
│   ├── 📄 conftest.py                 # Fixtures pytest (30+ fixtures)
│   │
│   ├── 📁 e2e/                        # Testy End-to-End
│   │   ├── 📄 __init__.py
│   │   ├── 📄 test_scenarios.py       # Scenariusze biznesowe (5 scenariuszy)
│   │   └── 📄 test_integrations_e2e.py # Testy E2E integracji (6 klas)
│   │
│   ├── 📁 integration/                # Testy integracyjne
│   │   ├── 📄 __init__.py
│   │   ├── 📄 test_api.py             # Testy API endpoints (19 testów)
│   │   └── 📄 test_integrations_api.py # Testy API integracji (15+ testów)
│   │
│   └── 📁 unit/                       # Testy jednostkowe
│       ├── 📄 __init__.py
│       ├── 📄 test_extractors.py      # Testy ekstraktorów (20 testów)
│       ├── 📄 test_validators.py      # Testy walidatorów NIP/REGON (25 testów)
│       └── 📄 test_integrations.py    # Testy klientów integracji (15+ testów)
│
├── 📁 web/                            # Frontend Web
│   ├── 📄 index.html                  # Główna strona HTML (450+ linii)
│   │
│   └── 📁 static/
│       ├── 📁 css/
│       │   └── 📄 style.css           # Style CSS (700+ linii)
│       │
│       └── 📁 js/
│           └── 📄 app.js              # JavaScript aplikacji (550+ linii)
│
├── 📁 uploads/                        # Uploadowane pliki
│   └── 📄 .gitkeep
│
├── 📁 processed/                      # Przetworzone pliki
│   └── 📄 .gitkeep
│
├── 📁 reports/                        # Wygenerowane raporty
│   └── 📄 .gitkeep
│
└── 📁 scripts/                        # Skrypty pomocnicze
```

## Integracje

### Programy księgowe (Accounting)

| Dostawca | Moduł | Funkcje |
|----------|-------|---------|
| iFirma | `ifirma.py` | Import faktur sprzedaży/zakupu, pobieranie PDF |
| Fakturownia | `fakturownia.py` | Import faktur i wydatków, API REST |
| wFirma | `wfirma_infakt.py` | Import faktur, ekspertyzy |
| InFakt | `wfirma_infakt.py` | Import faktur, integracja GTU/PKWiU |

### Magazyny chmurowe (Cloud Storage)

| Dostawca | Moduł | Protokół |
|----------|-------|----------|
| Nextcloud | `nextcloud.py` | WebDAV |
| Google Drive | `google_s3.py` | REST API v3 |
| AWS S3 | `google_s3.py` | S3 Protocol |
| MinIO | `google_s3.py` | S3 Protocol |
| Dropbox | `dropbox_onedrive.py` | REST API v2 |
| OneDrive | `dropbox_onedrive.py` | Microsoft Graph API |

### Konfiguracja integracji

Domyślnie używany jest SQLite do przechowywania konfiguracji:
- Plik: `config.db`
- Credentials są szyfrowane (Fernet)

Można zmienić na PostgreSQL/MySQL w `.env`:
```env
CONFIG_DB_TYPE=postgresql
CONFIG_DB_URL=postgresql://user:pass@host:5432/br_config
```

## Testy

### Testy jednostkowe (tests/unit/)

| Plik | Testy | Opis |
|------|-------|------|
| `test_validators.py` | 25 | Walidacja NIP/REGON |
| `test_extractors.py` | 20 | Ekstrakcja danych z faktur |
| `test_integrations.py` | 15+ | Klienci integracji |

### Testy integracyjne (tests/integration/)

| Plik | Testy | Opis |
|------|-------|------|
| `test_api.py` | 19 | Wszystkie endpointy API |
| `test_integrations_api.py` | 15+ | API integracji |

### Testy E2E (tests/e2e/)

| Plik | Scenariusze | Opis |
|------|-------------|------|
| `test_scenarios.py` | 5 | Scenariusze biznesowe B+R |
| `test_integrations_e2e.py` | 6 klas | Workflow integracji |

## Serwisy Docker

| Serwis | Port | Obraz | GPU |
|--------|------|-------|-----|
| postgres | 5432 | postgres:16-alpine | - |
| redis | 6379 | redis:7-alpine | - |
| api | 8000 | Dockerfile.api | - |
| ocr-service | 8001 | Dockerfile.ocr | ✅ |
| llm-service | 4000 | Dockerfile.llm | - |
| ollama | 11434 | ollama/ollama | ✅ |
| web | 80 | Dockerfile.web | - |
| celery-worker | - | Dockerfile.api | - |
| celery-beat | - | Dockerfile.api | - |
| flower | 5555 | Dockerfile.api | - |

## Uruchomienie testów

```bash
# Wszystkie testy
make test

# Testy jednostkowe (szybkie, bez zależności)
make test-unit
# lub
pytest tests/unit/ -v -m unit

# Testy integracyjne (wymagają PostgreSQL + Redis)
make test-integration
# lub
pytest tests/integration/ -v -m integration

# Testy E2E (wymagają wszystkich serwisów Docker)
make test-e2e
# lub
pytest tests/e2e/ -v -m e2e

# Z pokryciem kodu
make test-coverage
```

## API Endpoints - Pełna lista

### Dokumenty
| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/api/documents/upload` | Upload dokumentu |
| GET | `/api/documents/` | Lista dokumentów |
| GET | `/api/documents/{id}` | Szczegóły dokumentu |

### Wydatki
| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/api/expenses/` | Dodaj wydatek |
| GET | `/api/expenses/` | Lista wydatków |
| GET | `/api/expenses/{id}` | Szczegóły wydatku |
| PUT | `/api/expenses/{id}/classify` | Klasyfikuj wydatek |
| POST | `/api/expenses/{id}/auto-classify` | Auto-klasyfikacja LLM |
| GET | `/api/expenses/categories` | Lista kategorii B+R |

### Projekty
| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/api/projects/` | Utwórz projekt |
| GET | `/api/projects/` | Lista projektów |
| GET | `/api/projects/{id}` | Szczegóły projektu |
| GET | `/api/projects/{id}/summary` | Podsumowanie projektu |
| POST | `/api/projects/{id}/recalculate` | Przelicz sumy |

### Raporty
| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/api/reports/monthly/generate` | Generuj raport miesięczny |
| GET | `/api/reports/monthly/{id}` | Pobierz raport |
| GET | `/api/reports/monthly/` | Lista raportów |
| GET | `/api/reports/annual/br-summary` | Podsumowanie B+R |
| GET | `/api/reports/annual/ip-box-summary` | Podsumowanie IP Box |

### Integracje
| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/api/integrations/providers` | Dostępni dostawcy |
| POST | `/api/integrations/` | Dodaj integrację |
| GET | `/api/integrations/` | Lista integracji |
| GET | `/api/integrations/{id}` | Szczegóły integracji |
| PUT | `/api/integrations/{id}` | Aktualizuj |
| DELETE | `/api/integrations/{id}` | Usuń |
| POST | `/api/integrations/{id}/verify` | Weryfikuj połączenie |
| POST | `/api/integrations/{id}/sync/invoices` | Sync faktur |
| POST | `/api/integrations/{id}/upload/report` | Upload raportu |
| GET | `/api/integrations/{id}/logs` | Historia sync |
| POST | `/api/integrations/actions/sync-all-invoices` | Sync wszystko |
| POST | `/api/integrations/actions/upload-monthly-reports` | Upload wszystko |

### Wyjaśnienia
| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/api/clarifications/` | Utwórz pytanie |
| GET | `/api/clarifications/` | Lista pytań |
| GET | `/api/clarifications/{id}` | Szczegóły pytania |
| PUT | `/api/clarifications/{id}/answer` | Odpowiedz |

### Autoryzacja
| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/api/auth/register` | Rejestracja |
| POST | `/api/auth/login` | Logowanie |
| GET | `/api/auth/me` | Aktualny użytkownik |
