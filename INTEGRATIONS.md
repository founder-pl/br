# Dokumentacja Integracji

## Przegląd

System B+R oferuje integracje z zewnętrznymi systemami:

1. **Programy księgowe** - automatyczny import faktur kosztowych
2. **Magazyny chmurowe** - automatyczny upload raportów miesięcznych

## Architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  POST /integrations/                   - Dodaj integrację        │
│  GET  /integrations/                   - Lista integracji        │
│  POST /integrations/{id}/sync/invoices - Synchronizuj faktury    │
│  POST /integrations/{id}/upload/report - Wyślij raport           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Integration Manager                          │
│  - Tworzenie klientów (factory pattern)                         │
│  - Koordynacja synchronizacji                                    │
│  - Logowanie operacji                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│   Accounting Clients    │     │   Cloud Storage Clients │
│   - iFirma              │     │   - Nextcloud (WebDAV)  │
│   - Fakturownia         │     │   - Google Drive        │
│   - wFirma              │     │   - Dropbox             │
│   - InFakt              │     │   - OneDrive            │
│                         │     │   - AWS S3 / MinIO      │
└─────────────────────────┘     └─────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Config Database                               │
│  - SQLite (default) / PostgreSQL / MySQL                        │
│  - Szyfrowanie credentials (Fernet)                             │
│  - Historia synchronizacji                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Konfiguracja

### Zmienne środowiskowe

```env
# Typ bazy danych dla konfiguracji (sqlite, postgresql, mysql)
CONFIG_DB_TYPE=sqlite

# Connection string dla bazy konfiguracji
CONFIG_DB_URL=sqlite:///config.db

# Klucz szyfrowania dla credentials (generuj: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
CONFIG_ENCRYPTION_KEY=your-generated-key-here
```

### Generowanie klucza szyfrowania

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Programy księgowe

### iFirma

```json
{
  "id": "moja-ifirma",
  "provider": "ifirma",
  "integration_type": "accounting",
  "credentials": {
    "api_key": "klucz-api-z-panelu-ifirma",
    "username": "twoj-login@email.com",
    "company_name": "Nazwa Firmy",
    "invoice_key": "klucz-do-faktur",
    "expense_key": "klucz-do-wydatkow"
  }
}
```

**Jak uzyskać credentials:**
1. Zaloguj się do iFirma
2. Ustawienia → API
3. Wygeneruj klucze API

### Fakturownia

```json
{
  "id": "moja-fakturownia",
  "provider": "fakturownia",
  "integration_type": "accounting",
  "credentials": {
    "api_token": "token-z-ustawien-fakturownia",
    "subdomain": "twoja-subdomena"
  }
}
```

**Jak uzyskać credentials:**
1. Zaloguj się do Fakturownia
2. Ustawienia → Integracje → API
3. Skopiuj API Token

### wFirma

```json
{
  "id": "moja-wfirma",
  "provider": "wfirma",
  "integration_type": "accounting",
  "credentials": {
    "access_key": "klucz-dostepu",
    "secret_key": "klucz-tajny",
    "company_id": "id-firmy"
  }
}
```

### InFakt

```json
{
  "id": "moj-infakt",
  "provider": "infakt",
  "integration_type": "accounting",
  "credentials": {
    "api_key": "klucz-api-infakt"
  }
}
```

## Magazyny chmurowe

### Nextcloud

```json
{
  "id": "moj-nextcloud",
  "provider": "nextcloud",
  "integration_type": "cloud_storage",
  "credentials": {
    "username": "uzytkownik",
    "password": "haslo-lub-app-password"
  },
  "base_url": "https://cloud.twojadomena.pl",
  "settings": {
    "default_folder": "/BR-Reports"
  }
}
```

### Google Drive

```json
{
  "id": "moj-gdrive",
  "provider": "google_drive",
  "integration_type": "cloud_storage",
  "credentials": {
    "client_id": "twoj-client-id.apps.googleusercontent.com",
    "client_secret": "twoj-client-secret",
    "access_token": "ya29.token",
    "refresh_token": "1//refresh-token"
  },
  "settings": {
    "default_folder_id": "folder-id-lub-root"
  }
}
```

**Jak uzyskać credentials:**
1. Przejdź do [Google Cloud Console](https://console.cloud.google.com/)
2. Utwórz projekt i włącz Google Drive API
3. Utwórz OAuth 2.0 credentials
4. Wykonaj autoryzację OAuth

### Dropbox

```json
{
  "id": "moj-dropbox",
  "provider": "dropbox",
  "integration_type": "cloud_storage",
  "credentials": {
    "access_token": "sl.token-z-dropbox"
  }
}
```

### OneDrive

```json
{
  "id": "moj-onedrive",
  "provider": "onedrive",
  "integration_type": "cloud_storage",
  "credentials": {
    "client_id": "azure-app-client-id",
    "client_secret": "azure-app-secret",
    "access_token": "eyJ0-token",
    "refresh_token": "refresh-token"
  }
}
```

### AWS S3

```json
{
  "id": "moj-s3",
  "provider": "aws_s3",
  "integration_type": "cloud_storage",
  "credentials": {
    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
    "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "bucket": "br-reports-bucket"
  },
  "settings": {
    "region": "eu-central-1"
  }
}
```

### MinIO (Self-hosted S3)

```json
{
  "id": "moj-minio",
  "provider": "minio",
  "integration_type": "cloud_storage",
  "credentials": {
    "access_key_id": "minioadmin",
    "secret_access_key": "minioadmin",
    "bucket": "br-reports"
  },
  "settings": {
    "endpoint_url": "http://minio.local:9000"
  }
}
```

## API Endpoints

### Zarządzanie integracjami

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/integrations/providers` | Lista dostępnych dostawców |
| POST | `/integrations/` | Dodaj nową integrację |
| GET | `/integrations/` | Lista skonfigurowanych integracji |
| GET | `/integrations/{id}` | Szczegóły integracji |
| PUT | `/integrations/{id}` | Aktualizuj integrację |
| DELETE | `/integrations/{id}` | Usuń integrację |
| POST | `/integrations/{id}/verify` | Weryfikuj połączenie |

### Operacje synchronizacji

| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/integrations/{id}/sync/invoices` | Synchronizuj faktury |
| POST | `/integrations/{id}/upload/report` | Wyślij raport |
| GET | `/integrations/{id}/logs` | Historia synchronizacji |

### Akcje zbiorcze

| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/integrations/actions/sync-all-invoices` | Sync ze wszystkich źródeł |
| POST | `/integrations/actions/upload-monthly-reports` | Upload do wszystkich magazynów |

## Przykłady użycia

### Dodanie integracji iFirma

```bash
curl -X POST http://localhost:8000/api/integrations/ \
  -H "Content-Type: application/json" \
  -d '{
    "id": "moja-ifirma",
    "provider": "ifirma",
    "integration_type": "accounting",
    "credentials": {
      "api_key": "twoj-klucz-api",
      "username": "email@firma.pl",
      "company_name": "Moja Firma"
    }
  }'
```

### Synchronizacja faktur

```bash
curl -X POST http://localhost:8000/api/integrations/moja-ifirma/sync/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": "2025-01-01",
    "date_to": "2025-01-31",
    "project_id": "00000000-0000-0000-0000-000000000001"
  }'
```

### Upload raportu do chmury

```bash
curl -X POST http://localhost:8000/api/integrations/moj-nextcloud/upload/report \
  -H "Content-Type: application/json" \
  -d '{
    "report_name": "raport-br-2025-01.pdf",
    "year": 2025,
    "month": 1
  }'
```

## Struktura folderów w chmurze

Raporty są uploadowane z następującą strukturą:

```
/BR-Reports/
├── 2025/
│   ├── 01/
│   │   └── raport-br-2025-01.pdf
│   ├── 02/
│   │   └── raport-br-2025-02.pdf
│   └── ...
└── 2024/
    └── ...
```

## Bezpieczeństwo

1. **Szyfrowanie credentials** - wszystkie hasła i tokeny są szyfrowane algorytmem Fernet (AES-128-CBC)
2. **Izolacja bazy konfiguracji** - credentials są przechowywane oddzielnie od danych biznesowych
3. **Brak zwracania credentials** - API nigdy nie zwraca zapisanych credentials
4. **Rotacja kluczy** - możliwość zmiany klucza szyfrowania

## Rozwiązywanie problemów

### Błąd weryfikacji połączenia

1. Sprawdź poprawność credentials
2. Upewnij się, że URL bazowy jest poprawny
3. Sprawdź logi: `GET /integrations/{id}/logs`

### Błąd synchronizacji

1. Weryfikuj połączenie: `POST /integrations/{id}/verify`
2. Sprawdź zakres dat
3. Upewnij się, że masz odpowiednie uprawnienia API

### Błąd uploadu

1. Sprawdź czy folder docelowy istnieje
2. Weryfikuj uprawnienia do zapisu
3. Sprawdź limit rozmiaru pliku
