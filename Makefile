# =============================================================================
# System B+R - Makefile
# Prototypowy system modularny dla Tomasz Sapletta (NIP: 5881918662)
# =============================================================================

.PHONY: help build up down logs shell test clean setup-ollama test-all test-libs publish-all install-libs

# Default target
help:
	@echo "System B+R - Dostępne komendy:"
	@echo ""
	@echo "  Docker:"
	@echo "  make build        - Buduj obrazy Docker"
	@echo "  make up           - Uruchom wszystkie serwisy"
	@echo "  make up-gpu       - Uruchom z obsługą GPU NVIDIA"
	@echo "  make down         - Zatrzymaj wszystkie serwisy"
	@echo "  make logs         - Pokaż logi wszystkich serwisów"
	@echo "  make shell-api    - Shell w kontenerze API"
	@echo "  make shell-db     - Shell PostgreSQL"
	@echo ""
	@echo "  Testy:"
	@echo "  make test         - Uruchom testy główne"
	@echo "  make test-all     - Uruchom wszystkie testy (libs + main)"
	@echo "  make test-libs    - Uruchom testy bibliotek"
	@echo "  make test-lib LIB=br-core - Testuj pojedynczą bibliotekę"
	@echo ""
	@echo "  Biblioteki (libs/):"
	@echo "  make install-libs - Zainstaluj wszystkie biblioteki (dev)"
	@echo "  make build-libs   - Zbuduj wszystkie biblioteki"
	@echo "  make publish-all  - Opublikuj wszystkie do PyPI"
	@echo "  make publish-lib LIB=br-core - Opublikuj pojedynczą"
	@echo "  make clean-libs   - Wyczyść artefakty budowania"
	@echo ""
	@echo "  Inne:"
	@echo "  make clean        - Usuń kontenery i wolumeny"
	@echo "  make setup-ollama - Pobierz modele Ollama"
	@echo "  make setup-env    - Utwórz plik .env"
	@echo ""

# Setup environment
setup-env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Utworzono plik .env - uzupełnij klucze API"; \
	else \
		echo "Plik .env już istnieje"; \
	fi

# Build images with BuildKit cache
build:
	DOCKER_BUILDKIT=1 docker compose build

# Start services (without GPU)
up: setup-env
	docker compose up -d postgres redis
	@echo "Czekam na uruchomienie bazy danych..."
	@sleep 10
	docker compose up -d

# Start services with GPU
up-gpu: setup-env
	docker compose --profile gpu up -d postgres redis
	@echo "Czekam na uruchomienie bazy danych..."
	@sleep 10
	docker compose --profile gpu up -d

# Stop services
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-ocr:
	docker compose logs -f ocr-service

logs-llm:
	docker compose logs -f llm-service

# Shell access
shell-api:
	docker compose exec api /bin/bash

shell-ocr:
	docker compose exec ocr-service /bin/bash

shell-db:
	docker compose exec postgres psql -U br_admin -d br_system

# Database operations
db-migrate:
	docker compose exec api alembic upgrade head

db-reset:
	docker compose down -v
	docker compose up -d postgres
	@sleep 10
	docker compose up -d

# Setup Ollama models (lokalny Ollama na hoście)
setup-ollama:
	@echo "Pobieranie modeli Ollama (lokalny)..."
	ollama pull llama3.2
	ollama pull mistral
	ollama pull qwen2.5
	@echo "Modele pobrane!"

# Run tests
test:
	docker compose exec api pytest tests/ -v

test-unit:
	docker compose exec api pytest tests/unit/ -v -m unit

test-integration:
	docker compose exec api pytest tests/integration/ -v -m integration

test-e2e:
	docker compose exec api pytest tests/e2e/ -v -m e2e

test-coverage:
	docker compose exec api pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# =============================================================================
# Library Management (libs/)
# =============================================================================

LIBS_DIR := libs
LIBS := br-core md-render br-data-sources br-validators br-llm-client br-variable-api

# Test all libraries
test-all: test-libs test
	@echo "✓ Wszystkie testy zakończone"

test-libs:
	@echo "=== Testowanie bibliotek ==="
	@for lib in $(LIBS); do \
		echo ""; \
		echo ">>> Testowanie $$lib..."; \
		if [ -d "$(LIBS_DIR)/$$lib/tests" ]; then \
			cd $(LIBS_DIR)/$$lib && pip install -e . -q && pytest tests/ -v && cd ../..; \
		else \
			echo "Brak testów dla $$lib"; \
		fi; \
	done
	@echo ""
	@echo "=== Testy bibliotek zakończone ==="

test-lib:
	@if [ -z "$(LIB)" ]; then \
		echo "Użycie: make test-lib LIB=br-core"; \
	else \
		cd $(LIBS_DIR)/$(LIB) && pip install -e . -q && pytest tests/ -v; \
	fi

# Install all libraries in development mode
install-libs:
	@echo "=== Instalacja bibliotek (development mode) ==="
	@for lib in $(LIBS); do \
		echo ">>> Instalacja $$lib..."; \
		pip install -e $(LIBS_DIR)/$$lib -q; \
	done
	@echo "✓ Wszystkie biblioteki zainstalowane"

# Publish all libraries to PyPI
publish-all:
	@echo "=== Publikowanie wszystkich bibliotek ==="
	@for lib in $(LIBS); do \
		echo ""; \
		echo ">>> Publikowanie $$lib..."; \
		cd $(LIBS_DIR)/$$lib && \
		python -m build && \
		python -m twine upload dist/* --skip-existing && \
		rm -rf dist build *.egg-info && \
		cd ../..; \
	done
	@echo ""
	@echo "✓ Wszystkie biblioteki opublikowane"

# Publish single library
publish-lib:
	@if [ -z "$(LIB)" ]; then \
		echo "Użycie: make publish-lib LIB=br-core"; \
	else \
		cd $(LIBS_DIR)/$(LIB) && \
		python -m build && \
		python -m twine upload dist/* && \
		rm -rf dist build *.egg-info; \
	fi

# Build all libraries (without publishing)
build-libs:
	@echo "=== Budowanie bibliotek ==="
	@for lib in $(LIBS); do \
		echo ">>> Budowanie $$lib..."; \
		cd $(LIBS_DIR)/$$lib && python -m build && cd ../..; \
	done
	@echo "✓ Wszystkie biblioteki zbudowane"

# Clean library build artifacts
clean-libs:
	@echo "=== Czyszczenie artefaktów bibliotek ==="
	@for lib in $(LIBS); do \
		rm -rf $(LIBS_DIR)/$$lib/dist $(LIBS_DIR)/$$lib/build $(LIBS_DIR)/$$lib/*.egg-info; \
	done
	@find $(LIBS_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find $(LIBS_DIR) -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Artefakty wyczyszczone"

# Lint all libraries
lint-libs:
	@echo "=== Linting bibliotek ==="
	@for lib in $(LIBS); do \
		echo ">>> Linting $$lib..."; \
		cd $(LIBS_DIR)/$$lib && ruff check src/ tests/ || true && cd ../..; \
	done

# Clean everything
clean:
	docker compose down -v --rmi local
	rm -rf uploads/* processed/* reports/*

# Development mode with hot reload
dev: setup-env
	@echo "Upewnij się, że lokalny Ollama jest uruchomiony (ollama serve)"
	docker compose up -d postgres redis
	@sleep 5
	@echo "Uruchamiam serwisy w trybie deweloperskim..."
	@echo "API: http://localhost:8000"
	@echo "OCR: http://localhost:8001"
	@echo "LLM: http://localhost:4000"
	@echo "Web: http://localhost:80"
	docker compose up

# Status
status:
	docker compose ps

# Health check
health:
	@echo "Sprawdzam status serwisów..."
	@curl -s http://localhost:8000/health | jq . || echo "API: niedostępne"
	@curl -s http://localhost:8021/health | jq . || echo "OCR: niedostępne"
	@curl -s http://localhost:4000/health | jq . || echo "LLM: niedostępne"
