"""
B+R Documentation Generator - Main Generator Class.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import structlog

from .version_control import DocumentVersionControl
from .llm import generate_with_llm, refine_with_llm
from .templates import (
    build_expense_prompt,
    generate_expense_template,
    generate_summary_template,
)

logger = structlog.get_logger(__name__)


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
        prompt = build_expense_prompt(expense, project, document)
        
        # Try to generate with LLM, fall back to template if unavailable
        try:
            content = await generate_with_llm(prompt, self.llm_service_url)
        except Exception as e:
            logger.warning("LLM generation failed, using template", error=str(e))
            content = generate_expense_template(expense, project, document)
        
        # Save documentation file
        file_path = self._save_documentation(expense, project, content)
        
        return {
            'status': 'success',
            'file_path': str(file_path),
            'content': content,
            'expense_id': expense.get('id'),
            'generated_at': datetime.now().isoformat()
        }
    
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
    
    async def refine_documentation(
        self,
        content: str,
        validation_issues: List[Dict[str, Any]],
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Stage 6: Iterative Refinement - Use LLM to fix validation issues.
        """
        return await refine_with_llm(content, validation_issues, max_iterations)
    
    async def generate_project_summary(
        self,
        project: Dict[str, Any],
        expenses: List[Dict[str, Any]],
        timesheet_data: Optional[Dict[str, Any]] = None,
        contractors: Optional[List[Dict[str, Any]]] = None,
        revenues: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate summary documentation for entire project.
        
        Args:
            project: Project data
            expenses: List of all expenses for project
            timesheet_data: Optional timesheet data
            contractors: Optional contractors data
            revenues: Optional revenues data
            
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
        
        content = generate_summary_template(
            project, expenses, by_category, total_gross, total_br, total_deduction,
            timesheet_data, contractors, revenues
        )
        
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


# Singleton instance
_doc_generator: Optional[ExpenseDocumentGenerator] = None


def get_doc_generator() -> ExpenseDocumentGenerator:
    """Get singleton instance of document generator."""
    global _doc_generator
    if _doc_generator is None:
        _doc_generator = ExpenseDocumentGenerator()
    return _doc_generator
