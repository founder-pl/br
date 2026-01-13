"""
Document Generation Engine

Orchestrates data fetching, template rendering, and LLM-based generation.
"""
import re
import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .data_sources import DataSourceRegistry, get_data_registry, DataSourceResult
from .templates import TemplateRegistry, get_template_registry, DocumentTemplate, TimeScope

logger = structlog.get_logger()

MONTH_NAMES_PL = {
    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień",
    5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień",
    9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
}


def format_currency(value: Optional[Union[int, float]], currency: str = "PLN") -> str:
    """Format a number as currency"""
    if value is None:
        return "0,00 zł"
    try:
        formatted = f"{float(value):,.2f}".replace(",", " ").replace(".", ",")
        return f"{formatted} zł" if currency == "PLN" else f"{formatted} {currency}"
    except (ValueError, TypeError):
        return str(value)


def format_date(value: Optional[Union[str, datetime, date]]) -> str:
    """Format a date value"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return str(value)


class TemplateRenderer:
    """Simple template renderer with Jinja2-like syntax"""
    
    def __init__(self):
        self.filters = {
            "format_currency": format_currency,
            "format_date": format_date,
            "round": lambda x, n=2: round(float(x), n) if x else 0,
            "length": len,
        }
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context"""
        result = template
        
        result = self._render_for_loops(result, context)
        result = self._render_if_blocks(result, context)
        result = self._render_variables(result, context)
        
        return result
    
    def _render_for_loops(self, template: str, context: Dict[str, Any]) -> str:
        """Render {% for item in items %} ... {% endfor %} blocks"""
        pattern = r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}'
        
        def replace_for(match):
            item_name = match.group(1)
            collection_name = match.group(2)
            inner_template = match.group(3)
            
            collection = context.get(collection_name, [])
            if not isinstance(collection, (list, tuple)):
                return ""
            
            result_parts = []
            for idx, item in enumerate(collection):
                loop_context = {
                    **context,
                    item_name: item,
                    "loop": {"index": idx + 1, "index0": idx, "first": idx == 0, "last": idx == len(collection) - 1}
                }
                rendered = self._render_variables(inner_template, loop_context)
                result_parts.append(rendered)
            
            return "".join(result_parts)
        
        return re.sub(pattern, replace_for, template, flags=re.DOTALL)
    
    def _render_if_blocks(self, template: str, context: Dict[str, Any]) -> str:
        """Render {% if condition %} ... {% endif %} blocks"""
        pattern = r'\{%\s*if\s+(.+?)\s*%\}(.*?)(?:\{%\s*else\s*%\}(.*?))?\{%\s*endif\s*%\}'
        
        def replace_if(match):
            condition_str = match.group(1)
            true_block = match.group(2)
            false_block = match.group(3) or ""
            
            condition_result = self._evaluate_condition(condition_str, context)
            return true_block if condition_result else false_block
        
        return re.sub(pattern, replace_if, template, flags=re.DOTALL)
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a simple condition"""
        condition = condition.strip()
        
        if ">=" in condition:
            parts = condition.split(">=")
            left = self._get_value(parts[0].strip(), context)
            right = self._get_value(parts[1].strip(), context)
            return float(left or 0) >= float(right or 0)
        elif "<=" in condition:
            parts = condition.split("<=")
            left = self._get_value(parts[0].strip(), context)
            right = self._get_value(parts[1].strip(), context)
            return float(left or 0) <= float(right or 0)
        elif ">" in condition:
            parts = condition.split(">")
            left = self._get_value(parts[0].strip(), context)
            right = self._get_value(parts[1].strip(), context)
            return float(left or 0) > float(right or 0)
        elif "<" in condition:
            parts = condition.split("<")
            left = self._get_value(parts[0].strip(), context)
            right = self._get_value(parts[1].strip(), context)
            return float(left or 0) < float(right or 0)
        elif "==" in condition:
            parts = condition.split("==")
            left = self._get_value(parts[0].strip(), context)
            right = self._get_value(parts[1].strip(), context)
            return left == right
        else:
            value = self._get_value(condition, context)
            return bool(value)
    
    def _get_value(self, path: str, context: Dict[str, Any]) -> Any:
        """Get a value from context using dot notation"""
        if path.isdigit():
            return int(path)
        if path.replace(".", "").replace("-", "").isdigit():
            return float(path)
        if path.startswith('"') or path.startswith("'"):
            return path[1:-1]
        
        parts = path.split(".")
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
            if value is None:
                return None
        return value
    
    def _render_variables(self, template: str, context: Dict[str, Any]) -> str:
        """Render {{variable}} and {{variable|filter}} expressions"""
        pattern = r'\{\{(.+?)\}\}'
        
        def replace_var(match):
            expression = match.group(1).strip()
            
            if "|" in expression:
                parts = expression.split("|")
                var_path = parts[0].strip()
                value = self._get_value(var_path, context)
                
                for filter_expr in parts[1:]:
                    filter_expr = filter_expr.strip()
                    if "(" in filter_expr:
                        filter_name = filter_expr.split("(")[0]
                        args_str = filter_expr.split("(")[1].rstrip(")")
                        args = [a.strip() for a in args_str.split(",")] if args_str else []
                        args = [int(a) if a.isdigit() else a for a in args]
                    else:
                        filter_name = filter_expr
                        args = []
                    
                    if filter_name in self.filters:
                        filter_func = self.filters[filter_name]
                        try:
                            value = filter_func(value, *args) if args else filter_func(value)
                        except Exception:
                            pass
            else:
                value = self._get_value(expression, context)
            
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False, default=str)
            return str(value)
        
        return re.sub(pattern, replace_var, template)


class DocumentEngine:
    """Main document generation engine"""
    
    def __init__(self, llm_base_url: str = "http://localhost:11434"):
        self.data_registry = get_data_registry()
        self.template_registry = get_template_registry()
        self.renderer = TemplateRenderer()
        self.llm_base_url = llm_base_url
    
    async def list_templates(self) -> List[Dict[str, Any]]:
        """List all available document templates"""
        return self.template_registry.list_templates()
    
    async def list_data_sources(self) -> List[Dict[str, Any]]:
        """List all available data sources"""
        return self.data_registry.list_sources()
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template details"""
        template = self.template_registry.get(template_id)
        if template:
            return {
                **template.to_dict(),
                "template_content": template.template_content,
                "demo_content": template.demo_content,
                "llm_prompt": template.llm_prompt,
                "data_requirements": [
                    {
                        "source_name": req.source_name,
                        "required_params": req.required_params,
                        "optional_params": req.optional_params,
                        "description": req.description
                    }
                    for req in template.data_requirements
                ]
            }
        return None
    
    async def fetch_template_data(
        self, 
        template_id: str, 
        params: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Fetch all data required by a template"""
        template = self.template_registry.get(template_id)
        if not template:
            return {"error": f"Template not found: {template_id}"}
        
        results = {}
        errors = []
        
        for req in template.data_requirements:
            source = self.data_registry.get(req.source_name)
            if not source:
                errors.append(f"Data source not found: {req.source_name}")
                continue
            
            source_params = {k: params.get(k) for k in req.required_params + req.optional_params}
            
            from .data_sources import SQLDataSource
            if isinstance(source, SQLDataSource):
                result = await source.fetch(source_params, db)
            else:
                result = await source.fetch(source_params)
            
            if result.error:
                errors.append(f"{req.source_name}: {result.error}")
            else:
                results[req.source_name] = result.data
        
        return {
            "data": results,
            "params": params,
            "errors": errors if errors else None,
            "fetched_at": datetime.now().isoformat()
        }
    
    async def generate_document(
        self,
        template_id: str,
        params: Dict[str, Any],
        db: AsyncSession,
        use_llm: bool = False,
        llm_model: str = "llama3.2"
    ) -> Dict[str, Any]:
        """Generate a document from a template"""
        template = self.template_registry.get(template_id)
        if not template:
            return {"error": f"Template not found: {template_id}"}
        
        data_result = await self.fetch_template_data(template_id, params, db)
        if "error" in data_result:
            return data_result
        
        context = self._build_context(template, params, data_result["data"])
        
        if use_llm and template.llm_prompt:
            content = await self._generate_with_llm(template, context, llm_model)
        else:
            content = self.renderer.render(template.template_content, context)
        
        return {
            "template_id": template_id,
            "template_name": template.name,
            "content": content,
            "format": template.output_format,
            "generated_at": datetime.now().isoformat(),
            "params": params,
            "data_sources": list(data_result["data"].keys()),
            "errors": data_result.get("errors")
        }
    
    async def get_demo_document(self, template_id: str) -> Dict[str, Any]:
        """Get demo version of a document"""
        template = self.template_registry.get(template_id)
        if not template:
            return {"error": f"Template not found: {template_id}"}
        
        content = template.demo_content or f"# {template.name}\n\n*Demo content not available for this template.*"
        
        return {
            "template_id": template_id,
            "template_name": template.name,
            "content": content,
            "format": template.output_format,
            "is_demo": True
        }
    
    def _build_context(
        self, 
        template: DocumentTemplate, 
        params: Dict[str, Any], 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build the rendering context from fetched data"""
        context = {
            "generated_date": datetime.now().strftime("%Y-%m-%d"),
            "generated_datetime": datetime.now().isoformat(),
            **params
        }
        
        if params.get("month"):
            context["month_name"] = MONTH_NAMES_PL.get(int(params["month"]), "")
        
        project_data = data.get("project_info", [])
        if project_data and len(project_data) > 0:
            context["project"] = project_data[0]
        
        if "expenses_summary" in data:
            expenses = data["expenses_summary"]
            context["expenses"] = expenses
            context["total_gross"] = sum(e.get("gross_amount", 0) or 0 for e in expenses)
            context["total_net"] = sum(e.get("net_amount", 0) or 0 for e in expenses)
            context["total_qualified"] = sum(
                (e.get("gross_amount", 0) or 0) for e in expenses if e.get("br_qualified")
            )
        
        if "expenses_by_category" in data:
            cats = data["expenses_by_category"]
            context["expenses_by_category"] = cats
            context["total_expenses"] = sum(c.get("total_gross", 0) or 0 for c in cats)
            context["total_qualified"] = sum(c.get("qualified_amount", 0) or 0 for c in cats)
        
        if "timesheet_summary" in data:
            ts = data["timesheet_summary"]
            context["timesheet"] = ts
            context["total_hours"] = sum(t.get("total_hours", 0) or 0 for t in ts)
            context["worker_count"] = len(set(t.get("worker_name") for t in ts))
            if context["worker_count"] > 0:
                context["avg_hours"] = round(context["total_hours"] / context["worker_count"], 1)
            else:
                context["avg_hours"] = 0
        
        if "timesheet_monthly_breakdown" in data:
            breakdown = data["timesheet_monthly_breakdown"]
            workers = sorted(set(t.get("worker_name", "") for t in breakdown))
            context["workers"] = workers
            
            months_data = {}
            for entry in breakdown:
                month_key = (entry.get("year"), entry.get("month"))
                if month_key not in months_data:
                    months_data[month_key] = {"hours": {w: 0 for w in workers}, "total": 0}
                worker = entry.get("worker_name", "")
                hours = entry.get("hours", 0) or 0
                months_data[month_key]["hours"][worker] = hours
                months_data[month_key]["total"] += hours
            
            months = []
            for (year, month), mdata in sorted(months_data.items()):
                months.append({
                    "name": f"{MONTH_NAMES_PL.get(int(month), month)} {year}",
                    "hours": [mdata["hours"].get(w, 0) for w in workers],
                    "total": mdata["total"]
                })
            context["months"] = months
            context["worker_totals"] = [
                sum(m["hours"][i] for m in months) for i in range(len(workers))
            ]
            context["grand_total_hours"] = sum(context["worker_totals"])
        
        if "revenues" in data:
            revs = data["revenues"]
            context["revenues"] = revs
            context["total_revenue"] = sum(r.get("amount", 0) or 0 for r in revs)
        
        if "contractors" in data:
            context["contractors"] = data["contractors"]
        
        if "nexus_calculation" in data:
            nexus_data = data["nexus_calculation"]
            if nexus_data and len(nexus_data) > 0:
                context["nexus"] = nexus_data[0]
                nexus_val = nexus_data[0].get("nexus", 1)
                if context.get("total_revenue") and context.get("total_qualified"):
                    ip_income = context["total_revenue"] - context["total_qualified"]
                    context["ip_income"] = ip_income
                    context["qualified_income"] = ip_income * min(1, nexus_val)
                    context["ip_tax"] = context["qualified_income"] * 0.05
                    standard_tax = ip_income * 0.19
                    context["ip_box_savings"] = standard_tax - context["ip_tax"]
                else:
                    context["ip_income"] = 0
                    context["qualified_income"] = 0
                    context["ip_tax"] = 0
                    context["ip_box_savings"] = 0
        
        if "documents_list" in data:
            context["documents"] = data["documents_list"]
        
        return context
    
    async def _generate_with_llm(
        self, 
        template: DocumentTemplate, 
        context: Dict[str, Any],
        model: str
    ) -> str:
        """Generate document content using LLM"""
        context_summary = self._summarize_context(context)
        
        prompt = f"""{template.llm_prompt}

## Dostępne dane:

{context_summary}

## Szablon dokumentu (użyj jako bazę):

{template.template_content[:2000]}

## Wygeneruj dokument:
"""
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.llm_base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 4000
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            logger.error("llm_generation_error", error=str(e))
            return self.renderer.render(template.template_content, context)
    
    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """Create a text summary of context for LLM"""
        lines = []
        
        if "project" in context:
            p = context["project"]
            lines.append(f"### Projekt: {p.get('name', 'N/A')}")
            lines.append(f"- Kod: {p.get('code', 'N/A')}")
            lines.append(f"- Opis: {p.get('description', 'N/A')[:500]}")
        
        if "expenses_by_category" in context:
            lines.append("\n### Koszty według kategorii:")
            for cat in context["expenses_by_category"]:
                lines.append(f"- {cat.get('category')}: {format_currency(cat.get('total_gross'))}")
        
        if "total_qualified" in context:
            lines.append(f"\n**Koszty kwalifikowane B+R:** {format_currency(context['total_qualified'])}")
        
        if "timesheet" in context:
            lines.append(f"\n### Czas pracy: {context.get('total_hours', 0)} godzin")
        
        if "revenues" in context:
            lines.append(f"\n### Przychody: {format_currency(context.get('total_revenue', 0))}")
        
        if "nexus" in context:
            n = context["nexus"]
            lines.append(f"\n### Wskaźnik Nexus: {n.get('nexus', 1)}")
        
        # Include document annotations for richer context
        if "document_annotations" in context:
            annotations = context["document_annotations"]
            if annotations:
                lines.append("\n### Adnotacje dokumentów (kontekst B+R):")
                for ann in annotations[:10]:  # Limit to 10 annotations
                    filename = ann.get('filename', 'Dokument')
                    note = ann.get('annotation', '')[:300]
                    if note:
                        lines.append(f"- **{filename}**: {note}")
        
        # Include expenses with annotations
        if "expenses_with_docs" in context:
            expenses = context["expenses_with_docs"]
            annotated = [e for e in expenses if e.get('document_annotation')]
            if annotated:
                lines.append("\n### Wydatki z adnotacjami kontekstowymi:")
                for exp in annotated[:5]:
                    lines.append(f"- {exp.get('description', 'N/A')}: {exp.get('document_annotation', '')[:200]}")
        
        return "\n".join(lines)


def get_doc_engine(llm_url: str = "http://localhost:11434") -> DocumentEngine:
    """Get document engine instance"""
    return DocumentEngine(llm_base_url=llm_url)
