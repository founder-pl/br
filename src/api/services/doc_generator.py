"""
B+R Documentation Generator Service

Generates B+R documentation for expenses based on project data.
Each expense can generate a separate documentation file for tax deduction purposes.
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import httpx
import structlog

logger = structlog.get_logger(__name__)


class DocumentVersionControl:
    """Simple file-based version control for documents."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.versions_dir = repo_path / '.versions'
        self.versions_dir.mkdir(parents=True, exist_ok=True)
    
    def commit_file(self, file_path: Path, message: str) -> Optional[str]:
        """Save a version of the file and return version hash."""
        try:
            # Create version hash from timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            version_hash = f"v{timestamp}"
            
            # Create version directory structure
            rel_path = file_path.relative_to(self.repo_path)
            version_dir = self.versions_dir / rel_path.parent
            version_dir.mkdir(parents=True, exist_ok=True)
            
            # Save version file
            version_file = version_dir / f"{file_path.stem}_{version_hash}{file_path.suffix}"
            content = file_path.read_text(encoding='utf-8')
            version_file.write_text(content, encoding='utf-8')
            
            # Save metadata
            meta_file = version_dir / f"{file_path.stem}_{version_hash}.meta"
            meta = {
                'hash': version_hash,
                'date': datetime.now().isoformat(),
                'message': message,
                'filename': file_path.name
            }
            meta_file.write_text(json.dumps(meta), encoding='utf-8')
            
            logger.info("File version saved", file=str(rel_path), hash=version_hash)
            return version_hash
        except Exception as e:
            logger.warning("Could not save file version", error=str(e))
            return None
    
    def get_file_history(self, file_path: Path, limit: int = 20) -> List[Dict[str, Any]]:
        """Get version history for a file."""
        try:
            rel_path = file_path.relative_to(self.repo_path)
            version_dir = self.versions_dir / rel_path.parent
            
            if not version_dir.exists():
                return []
            
            # Find all meta files for this document
            history = []
            pattern = f"{file_path.stem}_v*.meta"
            for meta_file in sorted(version_dir.glob(pattern), reverse=True)[:limit]:
                try:
                    meta = json.loads(meta_file.read_text())
                    history.append({
                        'commit': meta.get('hash', 'unknown'),
                        'date': meta.get('date', ''),
                        'message': meta.get('message', '')
                    })
                except:
                    continue
            
            return history
        except Exception as e:
            logger.warning("Could not get file history", error=str(e))
            return []
    
    def get_file_at_commit(self, file_path: Path, commit: str) -> Optional[str]:
        """Get file content at specific version."""
        try:
            rel_path = file_path.relative_to(self.repo_path)
            version_dir = self.versions_dir / rel_path.parent
            version_file = version_dir / f"{file_path.stem}_{commit}{file_path.suffix}"
            
            if version_file.exists():
                return version_file.read_text(encoding='utf-8')
            return None
        except Exception as e:
            logger.warning("Could not get file at version", error=str(e))
            return None

# System prompt for B+R expense documentation
BR_EXPENSE_DOC_PROMPT = """Jesteś ekspertem w przygotowywaniu dokumentacji do polskiej ulgi badawczo-rozwojowej (B+R).
Generujesz profesjonalną dokumentację wydatku zgodną z wymaganiami art. 18d ustawy o CIT.

Dokumentacja wydatku B+R musi zawierać:
1. Identyfikację wydatku (nr faktury, data, dostawca)
2. Opis związku z działalnością B+R
3. Klasyfikację kategorii kosztów (wg CIT)
4. Uzasadnienie kwalifikowalności do odliczenia
5. Kwotę odliczenia i zastosowaną stawkę

Używaj języka formalnego, technicznego, odpowiedniego dla dokumentacji podatkowej.
Pisz w języku polskim."""


class ExpenseDocumentGenerator:
    """
    Generator dokumentacji B+R dla wydatków.
    Generuje dokumenty markdown dla każdego wydatku kwalifikowanego.
    """
    
    def __init__(self, llm_service_url: Optional[str] = None):
        self.llm_service_url = llm_service_url or os.getenv('LLM_SERVICE_URL', 'http://llm-service:4000')
        self.output_dir = Path('/app/reports/br_docs')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.version_control = DocumentVersionControl(self.output_dir)
    
    async def generate_expense_documentation(
        self,
        expense: Dict[str, Any],
        project: Dict[str, Any],
        document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate B+R documentation for a single expense.
        
        Args:
            expense: Expense data from database
            project: Project data the expense belongs to
            document: Optional source document data (OCR)
            
        Returns:
            Dict with status, file_path, and content
        """
        logger.info("Generating expense documentation", expense_id=expense.get('id'))
        
        # Build context for LLM
        prompt = self._build_expense_prompt(expense, project, document)
        
        # Try to generate with LLM, fall back to template if unavailable
        try:
            content = await self._generate_with_llm(prompt)
        except Exception as e:
            logger.warning("LLM generation failed, using template", error=str(e))
            content = self._generate_from_template(expense, project, document)
        
        # Save documentation file
        file_path = self._save_documentation(expense, project, content)
        
        return {
            'status': 'success',
            'file_path': str(file_path),
            'content': content,
            'expense_id': expense.get('id'),
            'generated_at': datetime.now().isoformat()
        }
    
    def _build_expense_prompt(
        self,
        expense: Dict[str, Any],
        project: Dict[str, Any],
        document: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for expense documentation generation."""
        
        # Get category description
        category_names = {
            'personnel_employment': 'Wynagrodzenia pracowników (umowa o pracę) - 200%',
            'personnel_civil': 'Wynagrodzenia (umowy cywilnoprawne) - 200%',
            'materials': 'Materiały i surowce - 100%',
            'equipment': 'Sprzęt specjalistyczny - 100%',
            'depreciation': 'Amortyzacja - 100%',
            'expertise': 'Ekspertyzy i opinie - 100%',
            'external_services': 'Usługi zewnętrzne - 100%',
            'other': 'Inne koszty kwalifikowane - 100%'
        }
        
        br_category = expense.get('br_category') or 'other'
        deduction_rate = expense.get('br_deduction_rate', 1.0)
        deduction_amount = float(expense.get('gross_amount', 0)) * deduction_rate
        
        prompt = f"""Wygeneruj dokumentację B+R dla poniższego wydatku:

DANE PROJEKTU:
- Nazwa projektu: {project.get('name', 'Projekt B+R')}
- Rok podatkowy: {project.get('fiscal_year', datetime.now().year)}
- Firma: {project.get('company_name', 'Firma')}

DANE WYDATKU:
- Nr faktury: {expense.get('invoice_number', 'N/A')}
- Data faktury: {expense.get('invoice_date', 'N/A')}
- Dostawca: {expense.get('vendor_name', 'N/A')}
- NIP dostawcy: {expense.get('vendor_nip', 'N/A')}
- Kwota brutto: {expense.get('gross_amount', 0)} {expense.get('currency', 'PLN')}
- Kwota netto: {expense.get('net_amount', 0)} {expense.get('currency', 'PLN')}
- VAT: {expense.get('vat_amount', 0)} {expense.get('currency', 'PLN')}

KLASYFIKACJA B+R:
- Kategoria: {category_names.get(br_category, br_category)}
- Kwalifikowany: {'Tak' if expense.get('br_qualified') else 'Nie'}
- Stawka odliczenia: {int(deduction_rate * 100)}%
- Kwota odliczenia: {deduction_amount:.2f} PLN
- Uzasadnienie: {expense.get('br_qualification_reason', 'Brak')}

{f"OPIS Z DOKUMENTU: {document.get('ocr_text', '')[:500]}..." if document and document.get('ocr_text') else ''}

Wygeneruj profesjonalną dokumentację B+R w formacie Markdown zawierającą:
1. Nagłówek z numerem dokumentu i datą
2. Identyfikację wydatku
3. Związek z działalnością B+R projektu
4. Uzasadnienie kategorii kosztów
5. Kalkulację odliczenia
6. Podsumowanie

Format: Markdown z nagłówkami H1, H2, H3"""

        return prompt
    
    async def _generate_with_llm(self, prompt: str) -> str:
        """Generate documentation using LLM service."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.llm_service_url}/v1/chat/completions",
                json={
                    "model": "default",
                    "messages": [
                        {"role": "system", "content": BR_EXPENSE_DOC_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                raise Exception(f"LLM service error: {response.status_code}")
    
    def _generate_from_template(
        self,
        expense: Dict[str, Any],
        project: Dict[str, Any],
        document: Optional[Dict[str, Any]]
    ) -> str:
        """Generate documentation from template (fallback)."""
        
        category_names = {
            'personnel_employment': 'Wynagrodzenia pracowników (umowa o pracę)',
            'personnel_civil': 'Wynagrodzenia (umowy cywilnoprawne)',
            'materials': 'Materiały i surowce',
            'equipment': 'Sprzęt specjalistyczny',
            'depreciation': 'Amortyzacja',
            'expertise': 'Ekspertyzy i opinie',
            'external_services': 'Usługi zewnętrzne',
            'other': 'Inne koszty kwalifikowane'
        }
        
        br_category = expense.get('br_category') or 'other'
        deduction_rate = expense.get('br_deduction_rate', 1.0)
        gross = float(expense.get('gross_amount', 0))
        net = float(expense.get('net_amount', 0))
        vat = float(expense.get('vat_amount', 0))
        deduction_amount = gross * deduction_rate
        
        doc_date = datetime.now().strftime('%Y-%m-%d')
        invoice_date = expense.get('invoice_date') or 'N/A'
        iteration_num = hash(expense.get('id', '')) % 1000 + 1
        
        # OCR/Document info section
        ocr_section = ""
        if document:
            ocr_text = document.get('ocr_text', '')[:500] if document.get('ocr_text') else ''
            ocr_confidence = document.get('ocr_confidence', 0) * 100 if document.get('ocr_confidence') else 0
            ocr_section = f"""
## 6. Dane źródłowe dokumentu

### Wyniki przetwarzania OCR

| Parametr | Wartość |
|----------|---------|
| Nazwa pliku | {document.get('filename', 'N/A')} |
| Typ dokumentu | {document.get('document_type', 'N/A')} |
| Status OCR | {document.get('ocr_status', 'N/A')} |
| Pewność OCR | {ocr_confidence:.1f}% |

### Fragment rozpoznanego tekstu

```
{ocr_text}
```
"""
        
        return f"""# Dokumentacja Wydatku B+R - Iteracja #{iteration_num}

**Nr dokumentu:** BR-{expense.get('id', 'N/A')[:8]}
**Data sporządzenia:** {doc_date}
**Wersja:** 1.0

---

## 1. Identyfikacja wydatku

| Parametr | Wartość |
|----------|---------|
| Nr faktury | {expense.get('invoice_number', 'N/A')} |
| Data faktury | {invoice_date} |
| Dostawca | {expense.get('vendor_name', 'N/A')} |
| NIP dostawcy | {expense.get('vendor_nip', 'N/A')} |
| Kwota brutto | {gross:.2f} {expense.get('currency', 'PLN')} |
| Kwota netto | {net:.2f} {expense.get('currency', 'PLN')} |
| VAT | {vat:.2f} {expense.get('currency', 'PLN')} |

## 2. Powiązanie z projektem B+R

**Projekt:** {project.get('name', 'Projekt B+R')}
**Rok podatkowy:** {project.get('fiscal_year', datetime.now().year)}

Niniejszy wydatek stanowi iterację #{iteration_num} w ramach projektu badawczo-rozwojowego
i dokumentuje postęp prac nad innowacyjnymi rozwiązaniami.

## 3. Opis prac badawczo-rozwojowych

### Cel iteracji

W ramach tej iteracji projektu przeprowadzono prace związane z:
- Testowaniem nowych rozwiązań technologicznych
- Weryfikacją hipotez badawczych
- Dokumentacją wyników eksperymentów

### Metodologia

Prace prowadzono zgodnie z metodyką badawczo-rozwojową obejmującą:
1. Planowanie eksperymentu
2. Realizację testów
3. Analiza wyników
4. Dokumentacja wniosków

### Wyniki i wnioski

Iteracja #{iteration_num} przyniosła następujące rezultaty:
- Zweryfikowano założenia techniczne
- Udokumentowano nowe doświadczenia
- Zidentyfikowano obszary do dalszych prac

## 4. Klasyfikacja kosztów B+R

**Kategoria:** {category_names.get(br_category, br_category)}

### Uzasadnienie klasyfikacji

{expense.get('br_qualification_reason') or 'Wydatek został zakwalifikowany jako koszt kwalifikowany w ramach działalności badawczo-rozwojowej na podstawie związku z realizowanym projektem B+R.'}

## 5. Kalkulacja odliczenia

| Element | Wartość | Obliczenie |
|---------|---------|------------|
| Kwota brutto | {gross:.2f} PLN | - |
| Kwota netto | {net:.2f} PLN | - |
| VAT ({((vat/net)*100) if net > 0 else 23:.0f}%) | {vat:.2f} PLN | {net:.2f} × {((vat/net)*100) if net > 0 else 23:.0f}% |
| Kwota kwalifikowana | {gross:.2f} PLN | kwota brutto |
| Stawka odliczenia | {int(deduction_rate * 100)}% | art. 18d CIT |
| **Odliczenie B+R** | **{deduction_amount:.2f} PLN** | {gross:.2f} × {int(deduction_rate * 100)}% |
{ocr_section}
## 7. Podsumowanie

Wydatek stanowi część iteracji #{iteration_num} projektu B+R i kwalifikuje się do odliczenia
zgodnie z art. 18d ustawy o CIT. Dokumentacja potwierdza związek wydatku z działalnością
badawczo-rozwojową oraz prawidłowość kalkulacji.

**Całkowita kwota do odliczenia: {deduction_amount:.2f} PLN**

---

*Dokumentacja wygenerowana automatycznie przez System B+R*
*Data: {doc_date} | Iteracja: #{iteration_num}*
"""
    
    def _save_documentation(
        self,
        expense: Dict[str, Any],
        project: Dict[str, Any],
        content: str
    ) -> Path:
        """Save documentation to file with version control."""
        
        # Create project subdirectory
        project_dir = self.output_dir / str(project.get('id', 'default'))
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        expense_id = expense.get('id', 'unknown')[:8]
        invoice_num = (expense.get('invoice_number') or 'no-inv').replace('/', '-').replace('\\', '-')
        date_str = datetime.now().strftime('%Y%m%d')
        
        filename = f"BR_DOC_{date_str}_{invoice_num}_{expense_id}.md"
        file_path = project_dir / filename
        
        # Save content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Commit to version control
        commit_msg = f"Expense doc: {invoice_num} ({expense_id})"
        self.version_control.commit_file(file_path, commit_msg)
        
        logger.info("Documentation saved", path=str(file_path))
        return file_path
    
    def get_document_history(self, project_id: str, filename: str) -> List[Dict[str, Any]]:
        """Get version history for a document."""
        file_path = self.output_dir / project_id / filename
        return self.version_control.get_file_history(file_path)
    
    def get_document_at_version(self, project_id: str, filename: str, commit: str) -> Optional[str]:
        """Get document content at specific version."""
        file_path = self.output_dir / project_id / filename
        return self.version_control.get_file_at_commit(file_path, commit)
    
    async def generate_project_summary(
        self,
        project: Dict[str, Any],
        expenses: list[Dict[str, Any]],
        timesheet_data: Optional[Dict[str, Any]] = None,
        contractors: Optional[list[Dict[str, Any]]] = None,
        revenues: Optional[list[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate summary documentation for entire project.
        
        Args:
            project: Project data
            expenses: List of all expenses for project
            
        Returns:
            Dict with status, file_path, and content
        """
        logger.info("Generating project summary", project_id=project.get('id'))
        
        # Calculate totals
        total_gross = sum(float(e.get('gross_amount', 0)) for e in expenses)
        br_qualified = [e for e in expenses if e.get('br_qualified')]
        total_br = sum(float(e.get('gross_amount', 0)) for e in br_qualified)
        total_deduction = sum(
            float(e.get('gross_amount', 0)) * float(e.get('br_deduction_rate', 1.0))
            for e in br_qualified
        )
        
        # Group by category
        by_category = {}
        for e in br_qualified:
            cat = e.get('br_category', 'other')
            if cat not in by_category:
                by_category[cat] = {'count': 0, 'amount': 0, 'deduction': 0}
            by_category[cat]['count'] += 1
            by_category[cat]['amount'] += float(e.get('gross_amount', 0))
            by_category[cat]['deduction'] += float(e.get('gross_amount', 0)) * float(e.get('br_deduction_rate', 1.0))
        
        content = self._generate_summary_template(project, expenses, by_category, total_gross, total_br, total_deduction, timesheet_data, contractors, revenues)
        
        # Save summary
        project_dir = self.output_dir / str(project.get('id', 'default'))
        project_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y%m%d')
        file_path = project_dir / f"BR_SUMMARY_{date_str}.md"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Commit to version control
        commit_msg = f"Summary: {project.get('name', 'project')} - {len(expenses)} expenses"
        self.version_control.commit_file(file_path, commit_msg)
        
        return {
            'status': 'success',
            'file_path': str(file_path),
            'content': content,
            'project_id': project.get('id'),
            'generated_at': datetime.now().isoformat(),
            'total_expenses': len(expenses),
            'br_qualified_count': len(br_qualified),
            'total_deduction': total_deduction
        }
    
    def _generate_summary_template(
        self,
        project: Dict[str, Any],
        expenses: list,
        by_category: Dict,
        total_gross: float,
        total_br: float,
        total_deduction: float,
        timesheet_data: Optional[Dict[str, Any]] = None,
        contractors: Optional[list[Dict[str, Any]]] = None,
        revenues: Optional[list[Dict[str, Any]]] = None
    ) -> str:
        """Generate comprehensive B+R project summary template."""
        
        category_names = {
            'personnel_employment': 'Wynagrodzenia pracowników (umowa o pracę)',
            'personnel_civil': 'Wynagrodzenia (umowy cywilnoprawne)',
            'materials': 'Materiały i surowce',
            'equipment': 'Sprzęt specjalistyczny',
            'depreciation': 'Amortyzacja',
            'expertise': 'Ekspertyzy i opinie',
            'external_services': 'Usługi zewnętrzne',
            'other': 'Inne koszty kwalifikowane'
        }
        
        doc_date = datetime.now().strftime('%Y-%m-%d')
        fiscal_year = project.get('fiscal_year', datetime.now().year)
        
        # Build category table
        category_rows = ""
        for cat, data in by_category.items():
            cat_name = category_names.get(cat, cat)
            category_rows += f"| {cat_name} | {data['count']} | {data['amount']:.2f} PLN | {data['deduction']:.2f} PLN |\n"
        
        # Build detailed expense descriptions
        expense_details = self._build_expense_details(expenses)
        
        # Build timesheet section
        timesheet_section = ""
        if timesheet_data and timesheet_data.get('total_hours', 0) > 0:
            timesheet_section = f"""
## 7. Ewidencja czasu pracy

| Parametr | Wartość |
|----------|---------|
| Łączna liczba godzin | {timesheet_data.get('total_hours', 0)} h |

### Podział godzin według pracowników:

"""
            for w in timesheet_data.get('by_worker', []):
                timesheet_section += f"| {w['worker_name']} | {w['total_hours']} h |\n"
        
        # Build contractors section
        contractors_section = ""
        if contractors and len(contractors) > 0:
            contractors_section = """
## 8. Kooperanci i dostawcy (faktury kosztowe)

| Nazwa | NIP | Kwota | Liczba faktur |
|-------|-----|-------|---------------|
"""
            for c in contractors:
                contractors_section += f"| {c.get('vendor_name', '-')} | {c.get('vendor_nip', '-')} | {c.get('total_amount', 0):.2f} PLN | {c.get('invoice_count', 0)} |\n"
        
        # Build revenues section (monetization)
        revenues_section = ""
        total_revenue = 0
        if revenues and len(revenues) > 0:
            total_revenue = sum(float(r.get('gross_amount', 0)) for r in revenues)
            revenues_section = f"""
## 9. Monetyzacja projektu B+R (faktury przychodowe)

Poniższa sekcja dokumentuje przychody z komercjalizacji wyników projektu B+R.

| Data | Nr faktury | Klient | Kwota | Opis |
|------|------------|--------|-------|------|
"""
            for r in revenues:
                revenues_section += f"| {r.get('invoice_date', 'N/A')} | {r.get('invoice_number', 'N/A')} | {r.get('client_name', 'N/A')} | {float(r.get('gross_amount', 0)):.2f} PLN | {r.get('ip_description', 'Usługi B+R')[:30]} |\n"
            
            revenues_section += f"""
**Łączne przychody z projektu B+R:** {total_revenue:.2f} PLN

### Analiza rentowności projektu

| Wskaźnik | Wartość |
|----------|---------|
| Koszty projektu | {total_gross:.2f} PLN |
| Przychody projektu | {total_revenue:.2f} PLN |
| Bilans projektu | {total_revenue - total_gross:.2f} PLN |
| ROI | {((total_revenue / total_gross - 1) * 100) if total_gross > 0 else 0:.1f}% |
"""
        
        return f"""# Dokumentacja Projektu B+R: {project.get('name', 'Projekt B+R')}

**Kod projektu:** BR-{fiscal_year}-{str(project.get('id', '000'))[:8]}
**Rok podatkowy:** {fiscal_year}
**Data sporządzenia:** {doc_date}
**Firma:** Tomasz Sapletta
**NIP:** 5881918662

---

## Streszczenie Wykonawcze

Niniejsza dokumentacja przedstawia kompleksowe podsumowanie projektu badawczo-rozwojowego 
realizowanego w roku podatkowym {fiscal_year}. Projekt spełnia kryteria działalności B+R 
określone w art. 4a pkt 26-28 ustawy o CIT: systematyczność, twórczość i innowacyjność.

| Parametr | Wartość |
|----------|---------|
| Całkowite koszty projektu | {total_gross:.2f} PLN |
| Koszty kwalifikowane B+R | {total_br:.2f} PLN |
| Kwota odliczenia podatkowego | {total_deduction:.2f} PLN |
| Przychody z komercjalizacji | {total_revenue:.2f} PLN |

---

## 1. Opis projektu

### 1.1 Cel projektu

{project.get('description', 'Brak opisu projektu.')}

### 1.2 Innowacyjność rozwiązania

Projekt charakteryzuje się następującymi elementami innowacyjności:
- Rozwój nowych technologii i metod
- Testowanie prototypowych rozwiązań
- Dokumentacja doświadczeń i wniosków z eksperymentów

### 1.3 Zakres prac B+R

Prace badawczo-rozwojowe obejmowały:
- Badania stosowane i prace rozwojowe
- Tworzenie prototypów i modeli doświadczalnych
- Testowanie i walidacja rozwiązań

## 2. Metodologia badawcza

### 2.1 Systematyczność

Projekt realizowany zgodnie z przyjętym harmonogramem i metodyką, z regularnymi 
przeglądami postępów i dokumentacją wyników każdej iteracji.

### 2.2 Twórczość

Prace projektowe miały charakter twórczy - oparte na oryginalnych koncepcjach 
i kreatywnym podejściu do rozwiązywania problemów technologicznych.

### 2.3 Element niepewności

W projekcie występował element niepewności co do osiągnięcia zakładanych rezultatów,
co jest cechą charakterystyczną działalności badawczo-rozwojowej.

## 3. Podsumowanie kosztów

### 3.1 Zestawienie ogólne

| Parametr | Wartość |
|----------|---------|
| Liczba wszystkich wydatków | {len(expenses)} |
| Liczba wydatków kwalifikowanych B+R | {len([e for e in expenses if e.get('br_qualified')])} |
| Suma wszystkich wydatków | {total_gross:.2f} PLN |
| Suma wydatków kwalifikowanych | {total_br:.2f} PLN |
| **Całkowita kwota odliczenia B+R** | **{total_deduction:.2f} PLN** |

### 3.2 Podział według kategorii kosztów kwalifikowanych

| Kategoria | Liczba | Kwota | Odliczenie |
|-----------|--------|-------|------------|
{category_rows}| **RAZEM** | **{sum(d['count'] for d in by_category.values()) if by_category else 0}** | **{total_br:.2f} PLN** | **{total_deduction:.2f} PLN** |

## 4. Podstawa prawna

Dokumentacja sporządzona zgodnie z wymogami:
- Art. 18d ustawy z dnia 15 lutego 1992 r. o podatku dochodowym od osób prawnych
- Art. 26e ustawy z dnia 26 lipca 1991 r. o podatku dochodowym od osób fizycznych

### Stawki odliczenia kosztów kwalifikowanych:

| Kategoria | Stawka | Podstawa prawna |
|-----------|--------|-----------------|
| Wynagrodzenia (umowa o pracę) | 200% | art. 18d ust. 2 pkt 1 |
| Umowy cywilnoprawne | 200% | art. 18d ust. 2 pkt 1a |
| Materiały i surowce | 100% | art. 18d ust. 2 pkt 2 |
| Ekspertyzy i usługi | 100% | art. 18d ust. 2 pkt 3 |
| Amortyzacja | 100% | art. 18d ust. 3 |

## 5. Szczegółowa dokumentacja wydatków

Każdy wydatek stanowi odrębną iterację w projekcie B+R, dokumentując postęp prac:

{expense_details}
{timesheet_section}{contractors_section}{revenues_section}
## 10. Oświadczenie

Oświadczam, że:
1. Wydatki ujęte w dokumentacji zostały faktycznie poniesione w roku podatkowym {fiscal_year}
2. Wydatki są bezpośrednio związane z prowadzoną działalnością badawczo-rozwojową
3. Dokumentacja odzwierciedla rzeczywisty przebieg prac B+R
4. Projekt spełnia kryteria systematyczności, twórczości i innowacyjności

---

*Dokumentacja wygenerowana automatycznie przez System B+R*
*Data: {doc_date}*
*Wersja dokumentu: 1.0*
"""


    def _build_expense_details(self, expenses: list) -> str:
        """Build detailed expense descriptions with justifications."""
        if not expenses:
            return "Brak wydatków do udokumentowania.\n"
        
        category_names = {
            'personnel_employment': 'Wynagrodzenia pracowników',
            'personnel_civil': 'Umowy cywilnoprawne',
            'materials': 'Materiały i surowce',
            'equipment': 'Sprzęt specjalistyczny',
            'depreciation': 'Amortyzacja',
            'expertise': 'Ekspertyzy i opinie',
            'external_services': 'Usługi zewnętrzne',
            'other': 'Inne koszty'
        }
        
        details = ""
        for i, e in enumerate(expenses, 1):
            iteration = hash(e.get('id', '')) % 1000 + 1
            inv_date = e.get('invoice_date', 'N/A')
            inv_num = e.get('invoice_number', 'N/A')
            vendor = e.get('vendor_name', 'Nieznany dostawca')
            vendor_nip = e.get('vendor_nip', 'N/A')
            gross = float(e.get('gross_amount', 0))
            net = float(e.get('net_amount', 0))
            vat = float(e.get('vat_amount', 0))
            currency = e.get('currency', 'PLN')
            br_cat = e.get('br_category', 'other')
            br_qualified = e.get('br_qualified', False)
            br_reason = e.get('br_qualification_reason', '')
            deduction_rate = float(e.get('br_deduction_rate', 1.0))
            
            status_icon = "✅" if br_qualified else "⏳"
            cat_name = category_names.get(br_cat, br_cat)
            
            details += f"""
### Iteracja #{iteration} - Wydatek {i}

| Parametr | Wartość |
|----------|---------|
| Nr faktury | {inv_num} |
| Data | {inv_date} |
| Dostawca | {vendor} |
| NIP dostawcy | {vendor_nip} |
| Kwota netto | {net:.2f} {currency} |
| VAT | {vat:.2f} {currency} |
| Kwota brutto | {gross:.2f} {currency} |
| Kategoria B+R | {cat_name} |
| Status kwalifikacji | {status_icon} {'Kwalifikowany' if br_qualified else 'Oczekuje na klasyfikację'} |
| Stawka odliczenia | {int(deduction_rate * 100)}% |
| Kwota odliczenia | {gross * deduction_rate if br_qualified else 0:.2f} PLN |

**Uzasadnienie kwalifikacji B+R:**

{br_reason if br_reason else 'Wydatek związany z realizacją prac badawczo-rozwojowych w ramach projektu. Stanowi koszt niezbędny do przeprowadzenia eksperymentów i testów prototypowych rozwiązań.'}

**Powiązanie z działalnością B+R:**

Wydatek dokumentuje iterację #{iteration} projektu B+R, w ramach której:
- Przeprowadzono testy i eksperymenty technologiczne
- Zweryfikowano hipotezy badawcze
- Udokumentowano wyniki i wnioski

---
"""
        return details
    
    def _build_expense_list(self, expenses: list) -> str:
        """Build expense list table for summary."""
        rows = ""
        for i, e in enumerate(expenses, 1):
            iteration = hash(e.get('id', '')) % 1000 + 1
            inv_date = e.get('invoice_date', 'N/A')
            inv_num = e.get('invoice_number', 'N/A')[:20] if e.get('invoice_number') else 'N/A'
            vendor = e.get('vendor_name', 'N/A')[:25] if e.get('vendor_name') else 'N/A'
            amount = float(e.get('gross_amount', 0))
            rows += f"| {i} | {inv_date} | {inv_num} | {vendor} | {amount:.2f} PLN | #{iteration} |\n"
        return rows if rows else "| - | Brak wydatków | - | - | - | - |\n"


# Singleton instance
_doc_generator: Optional[ExpenseDocumentGenerator] = None


def get_doc_generator() -> ExpenseDocumentGenerator:
    """Get singleton instance of document generator."""
    global _doc_generator
    if _doc_generator is None:
        _doc_generator = ExpenseDocumentGenerator()
    return _doc_generator
