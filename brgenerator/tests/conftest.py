"""
Pytest configuration and shared fixtures.
"""
import pytest
import os
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")
    # Don't set VALIDATION_LEVELS - let it use defaults


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing without API calls."""
    client = AsyncMock()
    
    # Mock generate method
    client.generate.return_value = "Generated content"
    
    # Mock generate_structured method
    client.generate_structured.return_value = {
        "valid": True,
        "issues": [],
        "score": 0.9,
    }
    
    # Mock validate_content method
    client.validate_content.return_value = {
        "is_valid": True,
        "issues": [],
        "suggestions": [],
        "score": 0.85,
    }
    
    # Mock improve_content method
    client.improve_content.return_value = "Improved content"
    
    return client


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_yaml_form():
    """Sample YAML form content."""
    return """
# BR Documentation Generator - Project Form
# Formularz danych projektu B+R

project:
  name: "Test Project"
  description: "Test project description for B+R"
  fiscal_year: 2024

company:
  name: "Test Company Sp. z o.o."
  nip: "5252448481"
  address: "ul. Testowa 1, 00-001 Warszawa"

timeline:
  start_date: "2024-01-01"
  end_date: "2024-12-31"
  milestones:
    - name: "Etap 1"
      date: "2024-06-30"
      description: "Halfway milestone"

innovation:
  type: "product"
  scale: "company"
  description: "Innovation description"
  novelty_justification: "Justification for novelty"

methodology: |
  Systematic approach with Agile methodology.
  Planned phases and milestones.

research_goals:
  - "Goal 1"
  - "Goal 2"

expected_results:
  - "Result 1"
  - "Result 2"

costs:
  personnel_employment:
    - name: "Jan Kowalski"
      role: "Developer"
      monthly_gross_salary: 10000
      br_time_percent: 100
      months_worked: 12

  materials:
    - description: "Test materials"
      amount: 5000
      justification: "For testing"

br_criteria:
  systematycznosc: true
  tworczosc: true
  nowatorstwo: true
  niepewnosc: true
"""
