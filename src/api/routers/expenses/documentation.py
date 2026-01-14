"""
Expenses Documentation - Documentation generation endpoints
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ...database import get_db

logger = structlog.get_logger()
router = APIRouter()


@router.post("/{expense_id}/generate-doc")
async def generate_expense_documentation(
    expense_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate B+R documentation for a single expense"""
    from ...services.doc_generator import get_doc_generator
    
    result = await db.execute(
        text("""
        SELECT e.*, p.name as project_name, p.fiscal_year, p.description as project_description,
               d.ocr_text, d.extracted_data
        FROM read_models.expenses e
        JOIN read_models.projects p ON e.project_id = p.id
        LEFT JOIN read_models.documents d ON e.document_id = d.id
        WHERE e.id = :id
        """),
        {"id": expense_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    expense = {
        'id': str(row[0]),
        'project_id': str(row[1]),
        'document_id': str(row[2]) if row[2] else None,
        'invoice_number': row[3],
        'invoice_date': str(row[4]) if row[4] else None,
        'vendor_name': row[5],
        'vendor_nip': row[6],
        'gross_amount': float(row[7] or 0),
        'net_amount': float(row[8] or 0),
        'vat_amount': float(row[9] or 0),
        'currency': row[10],
        'description': row[11],
        'expense_category': row[12],
        'br_category': row[13],
        'br_qualified': row[14],
        'br_deduction_rate': float(row[15] or 1.0),
        'br_qualification_reason': row[16],
        'status': row[17]
    }
    
    project = {
        'id': str(row[1]),
        'name': row[21],
        'fiscal_year': row[22],
        'description': row[23]
    }
    
    document = None
    if row[24]:
        document = {
            'ocr_text': row[24],
            'extracted_data': row[25]
        }
    
    doc_generator = get_doc_generator()
    result = await doc_generator.generate_expense_documentation(expense, project, document)
    
    logger.info("Expense documentation generated", expense_id=expense_id)
    return result


@router.post("/project/{project_id}/generate-summary")
async def generate_project_documentation_summary(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Generate B+R documentation summary for entire project"""
    from ...services.doc_generator import get_doc_generator
    
    proj_result = await db.execute(
        text("SELECT id, name, description, fiscal_year FROM read_models.projects WHERE id = :id"),
        {"id": project_id}
    )
    proj_row = proj_result.fetchone()
    
    if not proj_row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = {
        'id': str(proj_row[0]),
        'name': proj_row[1],
        'description': proj_row[2],
        'fiscal_year': proj_row[3]
    }
    
    exp_result = await db.execute(
        text("""
        SELECT id, invoice_number, invoice_date, vendor_name, vendor_nip,
               gross_amount, net_amount, vat_amount, currency,
               br_category, br_qualified, br_deduction_rate, br_qualification_reason, status
        FROM read_models.expenses WHERE project_id = :project_id
        ORDER BY invoice_date
        """),
        {"project_id": project_id}
    )
    
    expenses = []
    for row in exp_result.fetchall():
        expenses.append({
            'id': str(row[0]),
            'invoice_number': row[1],
            'invoice_date': str(row[2]) if row[2] else None,
            'vendor_name': row[3],
            'vendor_nip': row[4],
            'gross_amount': float(row[5] or 0),
            'net_amount': float(row[6] or 0),
            'vat_amount': float(row[7] or 0),
            'currency': row[8],
            'br_category': row[9],
            'br_qualified': row[10],
            'br_deduction_rate': float(row[11] or 1.0),
            'br_qualification_reason': row[12],
            'status': row[13]
        })
    
    year = project['fiscal_year']
    timesheet_data = None
    try:
        ts_result = await db.execute(
            text("""
                SELECT p.name as project_name, SUM(t.hours) as total_hours
                FROM read_models.timesheet_entries t
                JOIN read_models.projects p ON t.project_id = p.id
                WHERE t.project_id = :project_id AND EXTRACT(YEAR FROM t.work_date) = :year
                GROUP BY p.name
            """),
            {"project_id": project_id, "year": year}
        )
        by_project = [{"project_name": r[0], "total_hours": float(r[1])} for r in ts_result.fetchall()]
        
        worker_result = await db.execute(
            text("""
                SELECT w.name as worker_name, SUM(t.hours) as total_hours
                FROM read_models.timesheet_entries t
                JOIN read_models.workers w ON t.worker_id = w.id
                WHERE t.project_id = :project_id AND EXTRACT(YEAR FROM t.work_date) = :year
                GROUP BY w.name
            """),
            {"project_id": project_id, "year": year}
        )
        by_worker = [{"worker_name": r[0], "total_hours": float(r[1])} for r in worker_result.fetchall()]
        
        total_hours = sum(p["total_hours"] for p in by_project)
        if total_hours > 0:
            timesheet_data = {"total_hours": total_hours, "by_project": by_project, "by_worker": by_worker}
    except Exception as e:
        logger.warning("Could not load timesheet data", error=str(e))
    
    contractors = []
    try:
        contr_result = await db.execute(
            text("""
                SELECT vendor_name, vendor_nip, SUM(gross_amount) as total, COUNT(*) as count
                FROM read_models.expenses
                WHERE project_id = :project_id AND vendor_name IS NOT NULL AND vendor_name != ''
                GROUP BY vendor_name, vendor_nip ORDER BY total DESC
            """),
            {"project_id": project_id}
        )
        contractors = [
            {"vendor_name": r[0], "vendor_nip": r[1], "total_amount": float(r[2]), "invoice_count": r[3]}
            for r in contr_result.fetchall()
        ]
    except Exception as e:
        logger.warning("Could not load contractors data", error=str(e))
    
    revenues = []
    try:
        rev_result = await db.execute(
            text("""
                SELECT id, invoice_number, invoice_date, client_name, client_nip,
                       gross_amount, net_amount, currency, ip_description
                FROM read_models.revenues WHERE project_id = :project_id ORDER BY invoice_date
            """),
            {"project_id": project_id}
        )
        revenues = [
            {
                "id": str(r[0]), "invoice_number": r[1],
                "invoice_date": str(r[2]) if r[2] else None,
                "client_name": r[3], "client_nip": r[4],
                "gross_amount": float(r[5] or 0), "net_amount": float(r[6] or 0),
                "currency": r[7], "ip_description": r[8]
            }
            for r in rev_result.fetchall()
        ]
    except Exception as e:
        logger.warning("Could not load revenues data", error=str(e))
    
    doc_generator = get_doc_generator()
    result = await doc_generator.generate_project_summary(project, expenses, timesheet_data, contractors, revenues)
    
    await db.execute(
        text("""
        UPDATE read_models.projects SET
            total_expenses = COALESCE((SELECT SUM(gross_amount) FROM read_models.expenses WHERE project_id = :id), 0),
            br_qualified_expenses = COALESCE((SELECT SUM(gross_amount) FROM read_models.expenses WHERE project_id = :id AND br_qualified = true), 0),
            updated_at = NOW()
        WHERE id = :id
        """),
        {"id": project_id}
    )
    
    logger.info("Project summary generated", project_id=project_id, expenses=len(expenses))
    return result


@router.get("/project/{project_id}/docs")
async def list_project_documentation(project_id: str):
    """List all generated documentation files for a project"""
    docs_dir = Path('/app/reports/br_docs') / project_id
    
    if not docs_dir.exists():
        return {"project_id": project_id, "files": []}
    
    files = []
    for f in sorted(docs_dir.glob('*.md'), reverse=True):
        files.append({
            "filename": f.name,
            "path": str(f),
            "size": f.stat().st_size,
            "modified": f.stat().st_mtime
        })
    
    return {"project_id": project_id, "files": files}


@router.get("/project/{project_id}/docs/{filename}")
async def get_documentation_content(project_id: str, filename: str):
    """Get content of a specific documentation file"""
    if '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = Path('/app/reports/br_docs') / project_id / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Documentation file not found")
    
    content = file_path.read_text(encoding='utf-8')
    return {"filename": filename, "content": content, "project_id": project_id}


@router.get("/project/{project_id}/docs/{filename}/history")
async def get_documentation_history(project_id: str, filename: str):
    """Get version history for a documentation file"""
    from ...services.doc_generator import get_doc_generator
    
    if '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    doc_generator = get_doc_generator()
    history = doc_generator.get_document_history(project_id, filename)
    
    return {"project_id": project_id, "filename": filename, "history": history}


@router.get("/project/{project_id}/docs/{filename}/version/{commit}")
async def get_documentation_version(project_id: str, filename: str, commit: str):
    """Get document content at specific version"""
    from ...services.doc_generator import get_doc_generator
    
    if '..' in filename or '..' in commit:
        raise HTTPException(status_code=400, detail="Invalid parameters")
    
    doc_generator = get_doc_generator()
    content = doc_generator.get_document_at_version(project_id, filename, commit)
    
    if content is None:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {"project_id": project_id, "filename": filename, "commit": commit, "content": content}


@router.get("/project/{project_id}/docs/{filename}/pdf")
async def get_documentation_pdf(project_id: str, filename: str):
    """Generate and return PDF from markdown documentation"""
    if '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    md_path = Path('/app/reports/br_docs') / project_id / filename
    
    if not md_path.exists() or not md_path.is_file():
        raise HTTPException(status_code=404, detail="Documentation file not found")
    
    md_content = md_path.read_text(encoding='utf-8')
    
    html_content = _markdown_to_html(md_content)
    pdf_filename = filename.replace('.md', '.pdf')
    
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{pdf_filename}"'}
        )
    except ImportError:
        return Response(
            content=html_content.encode('utf-8'),
            media_type='text/html',
            headers={'Content-Disposition': f'inline; filename="{pdf_filename.replace(".pdf", ".html")}"'}
        )


def _markdown_to_html(md_content: str) -> str:
    """Convert markdown to HTML for PDF generation"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        h1 { color: #1e40af; border-bottom: 2px solid #1e40af; padding-bottom: 10px; }
        h2 { color: #1e40af; margin-top: 30px; }
        h3 { color: #374151; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th { background: #1e40af; color: white; padding: 10px; text-align: left; }
        td { border: 1px solid #e5e7eb; padding: 8px; }
        tr:nth-child(even) td { background: #f9fafb; }
        hr { border: none; border-top: 1px solid #e5e7eb; margin: 30px 0; }
    </style>
</head>
<body>
"""
    
    lines = md_content.split('\n')
    in_table = False
    table_html = ''
    
    for line in lines:
        if line.strip().startswith('|') and line.strip().endswith('|'):
            if not in_table:
                in_table = True
                table_html = '<table>'
            
            cleaned = line.replace('|', '').strip()
            if cleaned and all(c in '-: ' for c in cleaned):
                continue
            
            cells = [c.strip() for c in line.split('|')[1:-1]]
            tag = 'th' if not table_html.count('<tr>') else 'td'
            table_html += '<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>'
            continue
        elif in_table:
            table_html += '</table>'
            html_content += table_html
            in_table = False
            table_html = ''
        
        if line.startswith('### '):
            html_content += f'<h3>{line[4:]}</h3>'
        elif line.startswith('## '):
            html_content += f'<h2>{line[3:]}</h2>'
        elif line.startswith('# '):
            html_content += f'<h1>{line[2:]}</h1>'
        elif line.strip() == '---':
            html_content += '<hr>'
        elif line.strip():
            line = line.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
            while '**' in line:
                line = line.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
            html_content += f'<p>{line}</p>'
    
    if in_table:
        table_html += '</table>'
        html_content += table_html
    
    html_content += '</body></html>'
    return html_content
