"""
BR Documentation Generator CLI

Command-line interface for generating B+R documentation.

Usage:
    br-doc generate-form --output project_form.yaml
    br-doc generate --input project_form.yaml --output docs/
    br-doc validate --input docs/documentation.md --report validation.yaml
    br-doc render --input docs/documentation.md --output final.pdf
"""

import asyncio
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(
    name="br-doc",
    help="Generator dokumentacji B+R z wykorzystaniem LLM",
    add_completion=False
)

console = Console()


def get_config():
    """Load configuration from environment."""
    from br_doc_generator.config import load_config
    return load_config()


@app.command("generate-form")
def generate_form(
    output: str = typer.Option(
        "project_form.yaml",
        "--output", "-o",
        help="Ścieżka do pliku wyjściowego formularza YAML"
    ),
    project_name: Optional[str] = typer.Option(
        None,
        "--name", "-n",
        help="Nazwa projektu do wstępnego wypełnienia"
    ),
    fiscal_year: Optional[int] = typer.Option(
        None,
        "--year", "-y",
        help="Rok podatkowy"
    )
):
    """
    Generuj pusty formularz YAML do wypełnienia.
    
    Formularz zawiera wszystkie wymagane pola do wygenerowania
    dokumentacji B+R z komentarzami objaśniającymi.
    """
    from br_doc_generator.generators import FormGenerator
    
    console.print("[bold blue]Generowanie formularza projektu B+R...[/bold blue]")
    
    try:
        generator = FormGenerator()
        
        generator.generate_empty_form(
            project_name=project_name or "Nowy Projekt B+R",
            fiscal_year=fiscal_year,
            output_path=output
        )
        
        console.print(f"[green]✓[/green] Formularz zapisany: [cyan]{output}[/cyan]")
        console.print("\n[dim]Wypełnij formularz i uruchom:[/dim]")
        console.print(f"  br-doc generate --input {output}")
        
    except Exception as e:
        console.print(f"[red]✗ Błąd: {e}[/red]")
        raise typer.Exit(1)


@app.command("generate")
def generate(
    input_file: str = typer.Option(
        ...,
        "--input", "-i",
        help="Ścieżka do formularza YAML"
    ),
    output_dir: str = typer.Option(
        "./output",
        "--output", "-o",
        help="Katalog wyjściowy"
    ),
    format: str = typer.Option(
        "both",
        "--format", "-f",
        help="Format wyjściowy: pdf, md, both"
    ),
    validation_levels: Optional[str] = typer.Option(
        None,
        "--validation", "-v",
        help="Poziomy walidacji (oddzielone przecinkami): structure,content,legal,financial"
    ),
    max_iterations: int = typer.Option(
        3,
        "--max-iter",
        help="Maksymalna liczba iteracji poprawek"
    )
):
    """
    Generuj dokumentację B+R z formularza YAML.
    
    Uruchamia pełny pipeline: generowanie dokumentu LLM,
    wielopoziomowa walidacja, renderowanie do PDF.
    """
    from br_doc_generator import BRDocumentationPipeline
    
    if not Path(input_file).exists():
        console.print(f"[red]✗ Plik nie istnieje: {input_file}[/red]")
        raise typer.Exit(1)
    
    # Parse validation levels
    levels = None
    if validation_levels:
        levels = [l.strip() for l in validation_levels.split(",")]
    
    console.print(Panel.fit(
        "[bold]Generator Dokumentacji B+R[/bold]\n"
        f"Formularz: {input_file}\n"
        f"Katalog wyjściowy: {output_dir}",
        border_style="blue"
    ))
    
    async def run_generation():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Ładowanie konfiguracji...", total=None)
            
            try:
                pipeline = BRDocumentationPipeline.from_env()
                
                progress.update(task, description="[cyan]Generowanie dokumentacji...")
                
                result = await pipeline.generate(
                    form_path=input_file,
                    output_dir=output_dir,
                    validation_levels=levels,
                    max_iterations=max_iterations,
                    output_format=format
                )
                
                progress.update(task, description="[green]Generowanie zakończone!")
                
                return result
                
            except Exception as e:
                progress.update(task, description=f"[red]Błąd: {e}")
                raise
    
    try:
        result = asyncio.run(run_generation())
        
        # Show results
        console.print()
        
        if result.errors:
            console.print("[yellow]⚠ Ostrzeżenia podczas generowania:[/yellow]")
            for error in result.errors:
                console.print(f"  • {error}")
            console.print()
        
        # Results table
        table = Table(title="Wyniki Generowania")
        table.add_column("Parametr", style="cyan")
        table.add_column("Wartość", style="green")
        
        table.add_row("Status", result.status.value)
        table.add_row("Jakość", f"{result.quality_score:.1%}")
        table.add_row("Iteracje", str(result.iterations))
        table.add_row("Plik wyjściowy", result.output_path or "-")
        
        console.print(table)
        
        # Validation summary
        if result.validation_results:
            console.print("\n[bold]Podsumowanie walidacji:[/bold]")
            for vr in result.validation_results:
                status_icon = "✓" if vr.status.value == "passed" else "⚠" if vr.status.value == "warning" else "✗"
                status_color = "green" if vr.status.value == "passed" else "yellow" if vr.status.value == "warning" else "red"
                console.print(f"  [{status_color}]{status_icon}[/{status_color}] {vr.stage}: {vr.score:.0%}")
        
        console.print(f"\n[green]✓ Dokumentacja wygenerowana w: {output_dir}[/green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Błąd generowania: {e}[/red]")
        raise typer.Exit(1)


@app.command("validate")
def validate(
    input_file: str = typer.Option(
        ...,
        "--input", "-i",
        help="Ścieżka do dokumentacji markdown"
    ),
    report: str = typer.Option(
        "validation_report.yaml",
        "--report", "-r",
        help="Ścieżka do raportu walidacji"
    ),
    levels: Optional[str] = typer.Option(
        "structure,content,legal,financial",
        "--levels", "-l",
        help="Poziomy walidacji do uruchomienia"
    )
):
    """
    Waliduj istniejącą dokumentację B+R.
    
    Uruchamia wybrane poziomy walidacji na istniejącym
    dokumencie i generuje raport z wynikami.
    """
    from br_doc_generator import (
        ValidationPipeline,
        LLMClient,
        ProjectInput,
        ProjectBasicInfo,
        CompanyInfo,
        ProjectTimeline,
        InnovationInfo,
        MethodologyInfo,
        ProjectCosts,
        InnovationType,
        InnovationScale,
    )
    from br_doc_generator.config import DocumentationConfig
    from datetime import date
    
    if not Path(input_file).exists():
        console.print(f"[red]✗ Plik nie istnieje: {input_file}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold blue]Walidacja dokumentacji: {input_file}[/bold blue]")
    
    # Parse levels
    validation_levels = [l.strip() for l in levels.split(",")]
    
    async def run_validation():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Uruchamianie walidacji...", total=None)
            
            try:
                # Load markdown content
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Create minimal project input for validation
                config = get_config()
                llm_client = LLMClient(config.llm)
                pipeline = ValidationPipeline(llm_client, config.validation)
                
                # Dummy project input for validation context
                # Use a valid test NIP: 1234567854
                dummy_project = ProjectInput(
                    project=ProjectBasicInfo(
                        name="Validation Target",
                        code="VAL-001",
                        fiscal_year=date.today().year,
                        company=CompanyInfo(
                            name="Test Company",
                            nip="1234567854",  # Valid test NIP
                        )
                    ),
                    timeline=ProjectTimeline(
                        start_date=date.today(),
                        end_date=date.today(),
                        milestones=[]
                    ),
                    innovation=InnovationInfo(
                        type=InnovationType.PRODUCT,
                        scale=InnovationScale.COMPANY,
                        description="Validation target project - description placeholder for validation",
                        novelty_aspects=["Placeholder aspect"]
                    ),
                    methodology=MethodologyInfo(
                        systematic=True,
                        creative=True,
                        innovative=True,
                        risk_factors=[],
                        research_methods=[]
                    ),
                    costs=ProjectCosts(
                        personnel_employment=[],
                        personnel_civil=[],
                        materials=[],
                        external_services=[]
                    ),
                    documentation=DocumentationConfig()
                )
                
                final_content, result = await pipeline.run(
                    content,
                    dummy_project,
                    validation_levels,
                    max_iterations=1  # Just validate, don't iterate
                )
                
                progress.update(task, description="[green]Walidacja zakończona!")
                
                return result
                
            except Exception as e:
                progress.update(task, description=f"[red]Błąd: {e}")
                raise
                raise
    
    try:
        result = asyncio.run(run_validation())
        
        # Display results
        console.print()
        
        table = Table(title="Wyniki Walidacji")
        table.add_column("Etap", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Jakość", style="green")
        table.add_column("Problemy", style="yellow")
        
        for vr in result.validation_results:
            status_style = "green" if vr.status.value == "passed" else "yellow" if vr.status.value == "warning" else "red"
            table.add_row(
                vr.stage,
                f"[{status_style}]{vr.status.value}[/{status_style}]",
                f"{vr.score:.0%}",
                str(len(vr.issues))
            )
        
        console.print(table)
        
        # Show issues
        for vr in result.validation_results:
            if vr.issues:
                console.print(f"\n[bold yellow]Problemy - {vr.stage}:[/bold yellow]")
                for issue in vr.issues:
                    severity_color = "red" if issue.severity == "critical" else "yellow"
                    console.print(f"  [{severity_color}]•[/{severity_color}] [{issue.severity}] {issue.message}")
                    if issue.suggestion:
                        console.print(f"    [dim]→ {issue.suggestion}[/dim]")
        
        # Save report
        import yaml
        report_data = {
            "input_file": input_file,
            "status": result.status.value,
            "quality_score": float(result.quality_score),
            "validation_results": [
                {
                    "stage": vr.stage,
                    "status": vr.status.value,
                    "score": float(vr.score),
                    "issues": [
                        {
                            "type": i.type,
                            "severity": i.severity,
                            "message": i.message,
                            "location": i.location
                        }
                        for i in vr.issues
                    ]
                }
                for vr in result.validation_results
            ]
        }
        
        with open(report, 'w', encoding='utf-8') as f:
            yaml.safe_dump(report_data, f, allow_unicode=True)
        
        console.print(f"\n[green]✓ Raport zapisany: {report}[/green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Błąd walidacji: {e}[/red]")
        raise typer.Exit(1)


@app.command("render")
def render(
    input_file: str = typer.Option(
        ...,
        "--input", "-i",
        help="Ścieżka do dokumentacji markdown"
    ),
    output: str = typer.Option(
        "documentation.pdf",
        "--output", "-o",
        help="Ścieżka do pliku PDF wyjściowego"
    ),
    template: str = typer.Option(
        "professional",
        "--template", "-t",
        help="Szablon PDF: professional, minimal, detailed"
    ),
    logo: Optional[str] = typer.Option(
        None,
        "--logo",
        help="Ścieżka do logo firmy"
    ),
    company_name: Optional[str] = typer.Option(
        None,
        "--company",
        help="Nazwa firmy (do nagłówka/stopki)"
    )
):
    """
    Renderuj dokumentację markdown do PDF.
    
    Konwertuje plik markdown do profesjonalnego PDF
    z możliwością customizacji szablonu.
    """
    from br_doc_generator.generators import PDFRenderer
    
    if not Path(input_file).exists():
        console.print(f"[red]✗ Plik nie istnieje: {input_file}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold blue]Renderowanie do PDF: {input_file}[/bold blue]")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Renderowanie PDF...", total=None)
            
            renderer = PDFRenderer(
                template=template,
                company_logo=logo,
                header="Dokumentacja B+R",
                footer=f"Poufne - {company_name}" if company_name else "Poufne"
            )
            
            with open(input_file, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            output_path = renderer.render(
                markdown_content,
                output,
                metadata={
                    "title": "Dokumentacja B+R",
                    "company_name": company_name
                }
            )
            
            progress.update(task, description="[green]Renderowanie zakończone!")
        
        file_size = Path(output_path).stat().st_size / 1024
        console.print(f"\n[green]✓ PDF wygenerowany: {output_path} ({file_size:.1f} KB)[/green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Błąd renderowania: {e}[/red]")
        raise typer.Exit(1)


@app.command("info")
def info():
    """
    Pokaż informacje o konfiguracji i stanie systemu.
    """
    from br_doc_generator import __version__
    
    console.print(Panel.fit(
        f"[bold]BR Documentation Generator[/bold]\n"
        f"Wersja: {__version__}",
        border_style="blue"
    ))
    
    try:
        config = get_config()
        
        table = Table(title="Konfiguracja")
        table.add_column("Parametr", style="cyan")
        table.add_column("Wartość", style="green")
        
        table.add_row("LLM Provider", config.llm.default_provider.value)
        if config.llm.default_provider.value == "openrouter":
            table.add_row("LLM Model", config.llm.openrouter_model)
        else:
            table.add_row("LLM Model", config.llm.ollama_model)
        table.add_row("Temperatura", str(config.llm.temperature))
        table.add_row("Max Tokens", str(config.llm.max_tokens))
        table.add_row("Poziomy walidacji", ", ".join([l.value for l in config.validation.levels]))
        table.add_row("Max iteracji", str(config.validation.max_iterations))
        table.add_row("Szablon PDF", config.pdf.template.value)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[yellow]⚠ Nie można załadować konfiguracji: {e}[/yellow]")
        console.print("[dim]Upewnij się, że plik .env istnieje w bieżącym katalogu.[/dim]")


@app.command("web")
def web_server(
    host: str = typer.Option(
        "0.0.0.0",
        "--host", "-h",
        help="Host do nasłuchiwania"
    ),
    port: int = typer.Option(
        8000,
        "--port", "-p",
        help="Port do nasłuchiwania"
    ),
    reload: bool = typer.Option(
        False,
        "--reload", "-r",
        help="Automatyczne przeładowanie przy zmianach"
    )
):
    """
    Uruchom serwer web z interfejsem graficznym.
    
    Otwórz http://localhost:8000 w przeglądarce po uruchomieniu.
    """
    console.print(Panel.fit(
        f"[bold]BR Documentation Generator - Web Server[/bold]\n"
        f"Uruchamianie na http://{host}:{port}",
        border_style="blue"
    ))
    
    try:
        import uvicorn
        uvicorn.run(
            "br_doc_generator.web:app",
            host=host,
            port=port,
            reload=reload,
        )
    except ImportError:
        console.print("[red]✗ Brak modułu uvicorn. Zainstaluj: pip install uvicorn[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Błąd uruchamiania serwera: {e}[/red]")
        raise typer.Exit(1)


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
