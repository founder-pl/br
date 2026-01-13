"""
BR Documentation Generator - Web API

FastAPI-based web interface for the BR documentation generator.

Usage:
    uvicorn br_doc_generator.web:app --reload --port 8000

Then open http://localhost:8000 in your browser.
"""

from __future__ import annotations

import asyncio
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import structlog

from .config import AppConfig, load_config
from .generators import FormGenerator, PDFRenderer
from .validators import ValidationPipeline
from .models import ValidationStatus

logger = structlog.get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="BR Documentation Generator",
    description="Generator dokumentacji B+R z walidacją wielopoziomową",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global config
config = load_config()


# =============================================================================
# Request/Response Models
# =============================================================================

class FormGenerationRequest(BaseModel):
    """Request to generate a new form."""
    project_name: str = "Nowy Projekt B+R"
    fiscal_year: Optional[int] = None


class ValidationRequest(BaseModel):
    """Request to validate documentation."""
    markdown_content: str
    validation_levels: list[str] = ["structure", "legal", "financial"]


class ValidationResponse(BaseModel):
    """Validation result response."""
    status: str
    quality_score: float
    stages: list[dict]
    issues_count: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    llm_provider: str


class ConfigResponse(BaseModel):
    """Configuration info response."""
    llm_provider: str
    llm_model: str
    validation_levels: list[str]
    pdf_template: str


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface."""
    return """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BR Documentation Generator</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-blue-600">BR Documentation Generator</h1>
            <p class="text-gray-600">Generator dokumentacji B+R z walidacją wielopoziomową</p>
        </header>
        
        <!-- Tabs -->
        <div class="mb-6">
            <nav class="flex space-x-4">
                <button onclick="showTab('form')" class="tab-btn px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                    Generuj Formularz
                </button>
                <button onclick="showTab('validate')" class="tab-btn px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">
                    Waliduj Dokument
                </button>
                <button onclick="showTab('render')" class="tab-btn px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">
                    Renderuj PDF
                </button>
                <button onclick="showTab('info')" class="tab-btn px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">
                    Informacje
                </button>
            </nav>
        </div>
        
        <!-- Form Generation Tab -->
        <div id="form-tab" class="tab-content active bg-white rounded-lg shadow p-6">
            <h2 class="text-xl font-semibold mb-4">Generuj Formularz YAML</h2>
            <form id="form-gen" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700">Nazwa projektu</label>
                    <input type="text" id="project-name" value="Nowy Projekt B+R" 
                           class="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700">Rok podatkowy</label>
                    <input type="number" id="fiscal-year" value="2025" 
                           class="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
                </div>
                <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                    Generuj Formularz
                </button>
            </form>
            <div id="form-result" class="mt-4 hidden">
                <h3 class="font-semibold mb-2">Wygenerowany formularz:</h3>
                <pre id="form-content" class="bg-gray-100 p-4 rounded overflow-auto max-h-96 text-sm"></pre>
                <a id="form-download" class="mt-2 inline-block bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                    Pobierz YAML
                </a>
            </div>
        </div>
        
        <!-- Validation Tab -->
        <div id="validate-tab" class="tab-content bg-white rounded-lg shadow p-6">
            <h2 class="text-xl font-semibold mb-4">Waliduj Dokumentację</h2>
            <form id="validate-form" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700">Treść dokumentacji (Markdown)</label>
                    <textarea id="markdown-content" rows="10" 
                              class="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                              placeholder="Wklej tutaj dokumentację w formacie Markdown..."></textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700">Poziomy walidacji</label>
                    <div class="mt-2 space-x-4">
                        <label><input type="checkbox" value="structure" checked> Struktura</label>
                        <label><input type="checkbox" value="legal" checked> Prawna</label>
                        <label><input type="checkbox" value="financial" checked> Finansowa</label>
                        <label><input type="checkbox" value="content"> Treść (LLM)</label>
                    </div>
                </div>
                <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                    Waliduj
                </button>
            </form>
            <div id="validation-result" class="mt-4 hidden">
                <h3 class="font-semibold mb-2">Wyniki walidacji:</h3>
                <div id="validation-summary" class="mb-4"></div>
                <div id="validation-details" class="space-y-2"></div>
            </div>
        </div>
        
        <!-- PDF Rendering Tab -->
        <div id="render-tab" class="tab-content bg-white rounded-lg shadow p-6">
            <h2 class="text-xl font-semibold mb-4">Renderuj do PDF</h2>
            <form id="render-form" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700">Treść dokumentacji (Markdown)</label>
                    <textarea id="pdf-content" rows="10" 
                              class="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                              placeholder="Wklej tutaj dokumentację w formacie Markdown..."></textarea>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700">Szablon</label>
                    <select id="pdf-template" class="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
                        <option value="professional">Profesjonalny</option>
                        <option value="minimal">Minimalny</option>
                        <option value="detailed">Szczegółowy</option>
                    </select>
                </div>
                <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                    Renderuj PDF
                </button>
            </form>
            <div id="pdf-result" class="mt-4 hidden">
                <a id="pdf-download" class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                    Pobierz PDF
                </a>
            </div>
        </div>
        
        <!-- Info Tab -->
        <div id="info-tab" class="tab-content bg-white rounded-lg shadow p-6">
            <h2 class="text-xl font-semibold mb-4">Informacje o systemie</h2>
            <div id="system-info" class="space-y-2">
                <p>Ładowanie...</p>
            </div>
        </div>
    </div>
    
    <script>
        // Tab switching
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => {
                el.classList.remove('bg-blue-500', 'text-white');
                el.classList.add('bg-gray-300', 'text-gray-700');
            });
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.remove('bg-gray-300', 'text-gray-700');
            event.target.classList.add('bg-blue-500', 'text-white');
        }
        
        // Form generation
        document.getElementById('form-gen').addEventListener('submit', async (e) => {
            e.preventDefault();
            const projectName = document.getElementById('project-name').value;
            const fiscalYear = document.getElementById('fiscal-year').value;
            
            const response = await fetch('/api/form/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_name: projectName, fiscal_year: parseInt(fiscalYear) })
            });
            
            const data = await response.json();
            document.getElementById('form-content').textContent = data.content;
            document.getElementById('form-download').href = 'data:text/yaml;charset=utf-8,' + encodeURIComponent(data.content);
            document.getElementById('form-download').download = 'projekt_br.yaml';
            document.getElementById('form-result').classList.remove('hidden');
        });
        
        // Validation
        document.getElementById('validate-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const content = document.getElementById('markdown-content').value;
            const levels = Array.from(document.querySelectorAll('#validate-form input[type=checkbox]:checked'))
                               .map(cb => cb.value);
            
            const response = await fetch('/api/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ markdown_content: content, validation_levels: levels })
            });
            
            const data = await response.json();
            
            const statusColor = data.status === 'passed' ? 'green' : data.status === 'warning' ? 'yellow' : 'red';
            document.getElementById('validation-summary').innerHTML = `
                <div class="p-4 bg-${statusColor}-100 border border-${statusColor}-400 rounded">
                    <p><strong>Status:</strong> ${data.status}</p>
                    <p><strong>Jakość:</strong> ${(data.quality_score * 100).toFixed(1)}%</p>
                    <p><strong>Liczba problemów:</strong> ${data.issues_count}</p>
                </div>
            `;
            
            let detailsHtml = '';
            for (const stage of data.stages) {
                detailsHtml += `
                    <div class="border rounded p-3">
                        <h4 class="font-semibold">${stage.stage}</h4>
                        <p>Status: ${stage.status}, Wynik: ${(stage.score * 100).toFixed(0)}%</p>
                        ${stage.issues.length > 0 ? '<ul class="list-disc list-inside text-sm text-gray-600">' + 
                            stage.issues.map(i => `<li>${i.message}</li>`).join('') + '</ul>' : ''}
                    </div>
                `;
            }
            document.getElementById('validation-details').innerHTML = detailsHtml;
            document.getElementById('validation-result').classList.remove('hidden');
        });
        
        // PDF Rendering
        document.getElementById('render-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const content = document.getElementById('pdf-content').value;
            const template = document.getElementById('pdf-template').value;
            
            const response = await fetch('/api/render/pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ markdown_content: content, template: template })
            });
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            document.getElementById('pdf-download').href = url;
            document.getElementById('pdf-download').download = 'dokumentacja_br.pdf';
            document.getElementById('pdf-result').classList.remove('hidden');
        });
        
        // Load system info
        async function loadInfo() {
            const response = await fetch('/api/config');
            const data = await response.json();
            document.getElementById('system-info').innerHTML = `
                <table class="w-full">
                    <tr><td class="font-semibold">LLM Provider:</td><td>${data.llm_provider}</td></tr>
                    <tr><td class="font-semibold">Model:</td><td>${data.llm_model}</td></tr>
                    <tr><td class="font-semibold">Poziomy walidacji:</td><td>${data.validation_levels.join(', ')}</td></tr>
                    <tr><td class="font-semibold">Szablon PDF:</td><td>${data.pdf_template}</td></tr>
                </table>
            `;
        }
        loadInfo();
    </script>
</body>
</html>
"""


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        llm_provider=config.llm.default_provider.value,
    )


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Get current configuration."""
    return ConfigResponse(
        llm_provider=config.llm.default_provider.value,
        llm_model=config.llm.openrouter_model if config.llm.default_provider.value == "openrouter" else config.llm.ollama_model,
        validation_levels=[level.value for level in config.validation.levels],
        pdf_template=config.pdf.template.value,
    )


@app.post("/api/form/generate")
async def generate_form(request: FormGenerationRequest):
    """Generate a new YAML form."""
    generator = FormGenerator(config)
    content = generator.generate_empty_form(
        project_name=request.project_name,
        fiscal_year=request.fiscal_year,
    )
    return {"content": content}


@app.post("/api/validate", response_model=ValidationResponse)
async def validate_document(request: ValidationRequest):
    """Validate documentation."""
    from .models import (
        ProjectInput, ProjectBasicInfo, CompanyInfo, ProjectTimeline,
        InnovationInfo, MethodologyInfo, ProjectCosts, InnovationType,
        InnovationScale, DocumentationConfig
    )
    
    # Create minimal project input for validation
    dummy_project = ProjectInput(
        project=ProjectBasicInfo(
            name="Validation",
            code="VAL-001",
            fiscal_year=date.today().year,
            company=CompanyInfo(name="Test", nip="1234567854"),
        ),
        timeline=ProjectTimeline(
            start_date=date.today(),
            end_date=date.today(),
            milestones=[],
        ),
        innovation=InnovationInfo(
            type=InnovationType.PRODUCT,
            scale=InnovationScale.COMPANY,
            description="Validation target placeholder description for testing",
            novelty_aspects=["Placeholder"],
        ),
        methodology=MethodologyInfo(
            systematic=True,
            creative=True,
            innovative=True,
        ),
        costs=ProjectCosts(),
        documentation=DocumentationConfig(),
    )
    
    pipeline = ValidationPipeline(config=config.validation, use_llm=False)
    
    final_content, result = await pipeline.run(
        markdown_content=request.markdown_content,
        project_input=dummy_project,
        levels=request.validation_levels,
        max_iterations=1,
    )
    
    stages = []
    for stage in result.validation_stages:
        stages.append({
            "stage": stage.stage,
            "status": stage.status.value,
            "score": stage.score,
            "issues": [
                {"severity": i.severity.value, "message": i.message, "suggestion": i.suggestion}
                for i in stage.issues
            ]
        })
    
    total_issues = sum(len(s.issues) for s in result.validation_stages)
    
    return ValidationResponse(
        status=result.status.value,
        quality_score=result.quality_score,
        stages=stages,
        issues_count=total_issues,
    )


class PDFRenderRequest(BaseModel):
    """Request to render PDF."""
    markdown_content: str
    template: str = "professional"


@app.post("/api/render/pdf")
async def render_pdf(request: PDFRenderRequest):
    """Render markdown to PDF."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        renderer = PDFRenderer(template=request.template)
        output_path = renderer.render(
            markdown_content=request.markdown_content,
            output_path=tmp.name,
            metadata={"title": "Dokumentacja B+R"}
        )
        
        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename="dokumentacja_br.pdf"
        )


# =============================================================================
# CLI Entry Point for Web Server
# =============================================================================

def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the web server."""
    import uvicorn
    uvicorn.run(
        "br_doc_generator.web:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    run_server()
