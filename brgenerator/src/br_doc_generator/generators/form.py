"""
BR Documentation Generator - Form Generator

Generates YAML input forms for project data collection.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import yaml
import structlog

from ..config import get_config

logger = structlog.get_logger(__name__)


# YAML form template
FORM_TEMPLATE = """# ============================================================================
# BR Documentation Generator - Formularz Projektu
# ============================================================================
# Wypełnij poniższe pola danymi projektu B+R
# Pola oznaczone [WYMAGANE] są obowiązkowe
# Pola oznaczone [OPCJONALNE] można pominąć
# ============================================================================
# Wygenerowano: {timestamp}
# ============================================================================

# ----------------------------------------------------------------------------
# PODSTAWOWE INFORMACJE O PROJEKCIE [WYMAGANE]
# ----------------------------------------------------------------------------
project:
  # Nazwa projektu B+R
  name: "{project_name}"
  
  # Kod projektu (opcjonalny identyfikator wewnętrzny)
  code: "{project_code}"
  
  # Rok podatkowy dla rozliczenia ulgi B+R
  fiscal_year: {fiscal_year}
  
  # Dane firmy
  company:
    # Pełna nazwa firmy [WYMAGANE]
    name: "{company_name}"
    
    # NIP firmy (10 cyfr, bez kresek) [WYMAGANE]
    nip: "{company_nip}"
    
    # REGON (opcjonalny)
    regon: "{company_regon}"
    
    # Adres siedziby [OPCJONALNE]
    address: ""

# ----------------------------------------------------------------------------
# HARMONOGRAM REALIZACJI [WYMAGANE]
# ----------------------------------------------------------------------------
timeline:
  # Data rozpoczęcia projektu (format: YYYY-MM-DD)
  start_date: "{start_date}"
  
  # Data zakończenia projektu (format: YYYY-MM-DD)  
  end_date: "{end_date}"
  
  # Kamienie milowe projektu
  # Dodaj kolejne etapy według wzoru
  milestones:
    - date: "{milestone_1_date}"
      name: "Faza 1: Analiza i projektowanie"
      description: "Analiza wymagań i opracowanie specyfikacji technicznej"
      deliverables:
        - name: "Dokumentacja wymagań"
          description: "Specyfikacja funkcjonalna i techniczna"
          completed: false
        - name: "Projekt architektury"
          description: "Schemat architektury rozwiązania"
          completed: false
    
    - date: "{milestone_2_date}"
      name: "Faza 2: Prototypowanie"
      description: "Opracowanie i testowanie prototypu"
      deliverables:
        - name: "Prototyp MVP"
          completed: false
        - name: "Raport z testów"
          completed: false
    
    - date: "{milestone_3_date}"
      name: "Faza 3: Wdrożenie"
      description: "Finalizacja i wdrożenie rozwiązania"
      deliverables:
        - name: "Wersja produkcyjna"
          completed: false
        - name: "Dokumentacja końcowa"
          completed: false

# ----------------------------------------------------------------------------
# CHARAKTERYSTYKA INNOWACJI [WYMAGANE]
# ----------------------------------------------------------------------------
innovation:
  # Typ innowacji: product | process | mixed
  type: "product"
  
  # Skala innowacji: company | industry | global
  # Dla ulgi B+R wystarczy innowacja w skali przedsiębiorstwa (company)
  scale: "company"
  
  # Opis innowacji (minimum 50 znaków) [WYMAGANE]
  description: |
    Opisz tutaj na czym polega innowacyjność projektu.
    Wskaż jakie nowe rozwiązania są opracowywane
    i jakie problemy techniczne są rozwiązywane.
  
  # Aspekty nowatorskie - co jest nowego/innowacyjnego [WYMAGANE]
  novelty_aspects:
    - "Nowe podejście do rozwiązania problemu X"
    - "Zastosowanie innowacyjnej technologii Y"
    - "Opracowanie autorskiego algorytmu Z"
  
  # Wyzwania techniczne [OPCJONALNE]
  technical_challenges:
    - "Optymalizacja wydajności przy ograniczonych zasobach"
    - "Integracja z istniejącymi systemami"

# ----------------------------------------------------------------------------
# METODOLOGIA BADAWCZA [WYMAGANE]
# Kryteria kwalifikacji do ulgi B+R:
# - Systematyczność: projekt realizowany planowo
# - Twórczość: działania kreatywne, oryginalne
# - Nowatorstwo: innowacja w skali firmy
# ----------------------------------------------------------------------------
methodology:
  # Czy projekt jest realizowany systematycznie? [WYMAGANE: true]
  systematic: true
  
  # Czy projekt ma charakter twórczy? [WYMAGANE: true]
  creative: true
  
  # Czy projekt prowadzi do innowacji? [WYMAGANE: true]
  innovative: true
  
  # Czynniki ryzyka - kluczowe dla B+R
  # Ulga B+R wymaga elementu niepewności/ryzyka nieosiągnięcia celu
  risk_factors:
    - description: "Ryzyko nieosiągnięcia zakładanej wydajności"
      probability: "medium"  # low | medium | high
      mitigation: "Iteracyjne testowanie i optymalizacja"
    
    - description: "Niepewność co do skuteczności nowego algorytmu"
      probability: "medium"
      mitigation: "Eksperymenty porównawcze z rozwiązaniami alternatywnymi"
  
  # Metody badawcze [WYMAGANE]
  research_methods:
    - name: "Eksperymenty porównawcze"
      description: "Porównanie różnych podejść technicznych"
      tools:
        - "Testy A/B"
        - "Benchmarking"
    
    - name: "Prototypowanie iteracyjne"
      description: "Stopniowe udoskonalanie rozwiązania"
      tools:
        - "Agile/Scrum"
        - "CI/CD"
  
  # Hipotezy badawcze [OPCJONALNE]
  hypotheses:
    - "Nowy algorytm X poprawi wydajność o co najmniej 30%"
    - "Proponowane rozwiązanie zredukuje czas przetwarzania"
  
  # Oczekiwane rezultaty [OPCJONALNE]
  expected_results:
    - "Działający system spełniający wymagania funkcjonalne"
    - "Dokumentacja techniczna i raport z badań"

# ----------------------------------------------------------------------------
# KALKULACJA KOSZTÓW KWALIFIKOWANYCH [WYMAGANE]
# Kategorie kosztów zgodne z art. 18d ustawy o CIT
# ----------------------------------------------------------------------------
costs:
  # KOSZTY OSOBOWE - PRACOWNICY (200% odliczenia)
  # Wynagrodzenia pracowników zatrudnionych na umowę o pracę
  personnel_employment:
    - name: "Jan Kowalski"
      role: "Lead Developer"
      percentage: 80  # % czasu pracy poświęconego na B+R
      gross_salary: 15000  # miesięczne wynagrodzenie brutto PLN
      months: 12  # liczba miesięcy pracy w projekcie
    
    - name: "Anna Nowak"
      role: "Software Engineer"
      percentage: 60
      gross_salary: 12000
      months: 12
  
  # KOSZTY OSOBOWE - UMOWY CYWILNOPRAWNE (200% odliczenia)
  # Umowy zlecenie, umowy o dzieło
  personnel_civil:
    - name: "Piotr Wiśniewski"
      role: "Konsultant ML"
      contract_type: "UZ"  # UZ = umowa zlecenie, UD = umowa o dzieło
      amount: 30000  # całkowita kwota umowy PLN
      description: "Konsultacje dot. algorytmów ML"
  
  # MATERIAŁY I SPRZĘT (100% odliczenia)
  materials:
    - name: "Serwer GPU"
      category: "equipment"  # equipment | materials
      amount: 25000
      description: "Sprzęt do trenowania modeli ML"
      vendor: "Dell Technologies"
    
    - name: "Licencje oprogramowania"
      category: "materials"
      amount: 5000
      description: "Narzędzia deweloperskie"
  
  # USŁUGI ZEWNĘTRZNE (100% odliczenia)
  external_services:
    - name: "Konsultacje naukowe"
      provider: "Politechnika Warszawska"
      amount: 15000
      description: "Ekspertyzy dot. algorytmów NLP"
      is_scientific_unit: true  # czy jednostka naukowa?
    
    - name: "Usługi chmurowe"
      provider: "Amazon Web Services"
      amount: 10000
      description: "Infrastruktura do testów"
      is_scientific_unit: false

# ----------------------------------------------------------------------------
# KONFIGURACJA DOKUMENTACJI [OPCJONALNE]
# ----------------------------------------------------------------------------
documentation:
  # Istniejące pliki do uwzględnienia
  existing_files: []
  #  - path: "/docs/specification.md"
  #    description: "Specyfikacja techniczna"
  
  # Sekcje do wygenerowania
  generate_sections:
    - "executive_summary"
    - "project_description"
    - "methodology"
    - "innovation_analysis"
    - "cost_calculation"
    - "timeline"
    - "risk_assessment"
    - "conclusions"
  
  # Czy dodać załączniki
  include_appendices: true
  
  # Język dokumentacji
  language: "pl"
"""


class FormGenerator:
    """
    Generator for project input YAML forms.
    
    Creates pre-filled YAML templates for easy project data entry.
    """
    
    def __init__(self, config=None):
        """Initialize form generator."""
        self.config = config or get_config()
    
    def generate_empty_form(
        self,
        project_name: str = "Nazwa projektu",
        fiscal_year: Optional[int] = None,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate empty form template.
        
        Args:
            project_name: Default project name
            fiscal_year: Fiscal year (default: current year)
            output_path: Optional path to save form
            
        Returns:
            YAML form content
        """
        now = datetime.now()
        fiscal_year = fiscal_year or now.year
        
        # Calculate default dates
        start_date = date(fiscal_year, 1, 1)
        end_date = date(fiscal_year, 12, 31)
        
        # Milestone dates
        milestone_1 = date(fiscal_year, 3, 31)
        milestone_2 = date(fiscal_year, 6, 30)
        milestone_3 = date(fiscal_year, 12, 31)
        
        # Get company defaults from config
        company_name = self.config.company.company_name or "Nazwa firmy"
        company_nip = self.config.company.company_nip or "0000000000"
        company_regon = self.config.company.company_regon or ""
        
        form_content = FORM_TEMPLATE.format(
            timestamp=now.isoformat(),
            project_name=project_name,
            project_code=f"BR-{fiscal_year}-001",
            fiscal_year=fiscal_year,
            company_name=company_name,
            company_nip=company_nip,
            company_regon=company_regon,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            milestone_1_date=milestone_1.isoformat(),
            milestone_2_date=milestone_2.isoformat(),
            milestone_3_date=milestone_3.isoformat(),
        )
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(form_content, encoding="utf-8")
            logger.info(f"Form saved to: {output_path}")
        
        return form_content
    
    def generate_prefilled_form(
        self,
        project_name: str,
        company_name: str,
        company_nip: str,
        fiscal_year: int,
        start_date: date,
        end_date: date,
        output_path: Optional[Path] = None,
        **kwargs
    ) -> str:
        """
        Generate form with pre-filled company and project data.
        
        Args:
            project_name: Project name
            company_name: Company name
            company_nip: Company NIP
            fiscal_year: Fiscal year
            start_date: Project start date
            end_date: Project end date
            output_path: Optional path to save form
            **kwargs: Additional fields to fill
            
        Returns:
            YAML form content
        """
        now = datetime.now()
        
        # Calculate milestone dates based on project duration
        duration = (end_date - start_date).days
        milestone_1 = start_date + timedelta(days=duration // 4)
        milestone_2 = start_date + timedelta(days=duration // 2)
        milestone_3 = end_date
        
        form_content = FORM_TEMPLATE.format(
            timestamp=now.isoformat(),
            project_name=project_name,
            project_code=kwargs.get("project_code", f"BR-{fiscal_year}-001"),
            fiscal_year=fiscal_year,
            company_name=company_name,
            company_nip=company_nip,
            company_regon=kwargs.get("company_regon", ""),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            milestone_1_date=milestone_1.isoformat(),
            milestone_2_date=milestone_2.isoformat(),
            milestone_3_date=milestone_3.isoformat(),
        )
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(form_content, encoding="utf-8")
            logger.info(f"Form saved to: {output_path}")
        
        return form_content
    
    @staticmethod
    def load_form(path: Path) -> dict:
        """
        Load and validate form from YAML file.
        
        Args:
            path: Path to YAML form file
            
        Returns:
            Parsed form data
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Form file not found: {path}")
        
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        
        logger.info(f"Loaded form from: {path}")
        return data
    
    @staticmethod
    def validate_form(data: dict) -> list[str]:
        """
        Validate form data for completeness.
        
        Args:
            data: Parsed form data
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required top-level keys
        required_keys = ["project", "timeline", "innovation", "methodology", "costs"]
        for key in required_keys:
            if key not in data:
                errors.append(f"Missing required section: {key}")
        
        # Validate project section
        if "project" in data:
            project = data["project"]
            if not project.get("name"):
                errors.append("Project name is required")
            if not project.get("fiscal_year"):
                errors.append("Fiscal year is required")
            
            company = project.get("company", {})
            if not company.get("name"):
                errors.append("Company name is required")
            if not company.get("nip"):
                errors.append("Company NIP is required")
        
        # Validate methodology B+R criteria
        if "methodology" in data:
            methodology = data["methodology"]
            if not methodology.get("systematic"):
                errors.append("B+R requires systematic approach (systematic: true)")
            if not methodology.get("creative"):
                errors.append("B+R requires creative approach (creative: true)")
            if not methodology.get("innovative"):
                errors.append("B+R requires innovative approach (innovative: true)")
        
        # Validate costs
        if "costs" in data:
            costs = data["costs"]
            has_costs = any([
                costs.get("personnel_employment"),
                costs.get("personnel_civil"),
                costs.get("materials"),
                costs.get("external_services"),
            ])
            if not has_costs:
                errors.append("At least one cost category must be filled")
        
        return errors


# Import for type hints
from datetime import timedelta
