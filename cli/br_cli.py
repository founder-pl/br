#!/usr/bin/env python3
"""
BR System CLI - Command line interface for B+R documentation system.
Uses the same API as the web GUI.
"""
import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system("pip install requests")
    import requests

API_BASE = os.environ.get("BR_API_URL", "http://localhost:8020")


def api_call(method: str, endpoint: str, data=None, files=None):
    """Make API call and return JSON response."""
    url = f"{API_BASE}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, timeout=30)
        elif method == "POST":
            if files:
                resp = requests.post(url, files=files, timeout=300)
            else:
                resp = requests.post(url, json=data, timeout=30)
        elif method == "PUT":
            resp = requests.put(url, json=data, timeout=30)
        elif method == "DELETE":
            resp = requests.delete(url, timeout=30)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        resp.raise_for_status()
        return resp.json() if resp.text else {}
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        sys.exit(1)


def cmd_health(args):
    """Check API health."""
    result = api_call("GET", "/health")
    print(f"✅ Status: {result.get('status')}")
    print(f"   Service: {result.get('service')}")
    print(f"   Company: {result.get('company_nip')}")
    print(f"   Project: {result.get('project')}")


def cmd_projects_list(args):
    """List all projects."""
    result = api_call("GET", "/projects/")
    print(f"\n{'ID':<40} {'Name':<30} {'Year':<6} {'Expenses':<12}")
    print("-" * 90)
    for p in result:
        print(f"{p['id']:<40} {p['name'][:28]:<30} {p.get('fiscal_year', 'N/A'):<6} {p.get('total_expenses', 0):.2f} PLN")


def cmd_expenses_list(args):
    """List expenses for a project."""
    endpoint = f"/expenses/?project_id={args.project_id}"
    result = api_call("GET", endpoint)
    
    print(f"\n{'Date':<12} {'Invoice':<20} {'Vendor':<25} {'Amount':<12} {'B+R':<5}")
    print("-" * 80)
    for e in result:
        br = "✅" if e.get('br_qualified') else "⏳"
        print(f"{str(e.get('invoice_date', 'N/A')):<12} {str(e.get('invoice_number', 'N/A'))[:18]:<20} {str(e.get('vendor_name', 'N/A'))[:23]:<25} {e.get('gross_amount', 0):.2f} PLN  {br}")
    
    print(f"\nTotal: {len(result)} expenses")


def cmd_revenues_list(args):
    """List revenues for a project."""
    endpoint = f"/reports/annual/ip-box-summary?fiscal_year={args.year}&project_id={args.project_id}"
    result = api_call("GET", endpoint)
    
    print(f"\n📊 IP Box Summary for {args.year}")
    print("-" * 50)
    print(f"IP Revenues: {result.get('ip_revenues', 0):.2f} PLN")
    print(f"Nexus Ratio: {result.get('nexus_ratio', 0):.2%}")
    print(f"Qualified Income: {result.get('qualified_income', 0):.2f} PLN")
    print(f"Tax (5%): {result.get('tax_5_percent', 0):.2f} PLN")


def cmd_upload(args):
    """Upload a document for OCR processing."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    with open(file_path, 'rb') as f:
        files = {'file': (file_path.name, f, 'application/pdf')}
        endpoint = f"/documents/upload?project_id={args.project_id}&document_type={args.type}"
        result = api_call("POST", endpoint, files=files)
    
    print(f"✅ Document uploaded")
    print(f"   ID: {result.get('document_id')}")
    print(f"   Status: {result.get('status')}")
    print(f"   Message: {result.get('message')}")


def cmd_docs_list(args):
    """List generated documentation files."""
    endpoint = f"/expenses/project/{args.project_id}/docs"
    result = api_call("GET", endpoint)
    
    print(f"\n📄 Documentation files for project {args.project_id[:8]}...")
    print("-" * 60)
    for doc in result.get('files', []):
        if isinstance(doc, dict):
            print(f"  - {doc.get('filename', 'unknown')} ({doc.get('size', 0)} bytes)")
        else:
            print(f"  - {doc}")


def cmd_docs_generate(args):
    """Generate project summary documentation."""
    endpoint = f"/expenses/project/{args.project_id}/generate-summary"
    result = api_call("POST", endpoint)
    
    print(f"✅ Documentation generated")
    print(f"   Status: {result.get('status')}")
    print(f"   Expenses: {result.get('total_expenses')}")
    print(f"   B+R Qualified: {result.get('br_qualified_count')}")
    print(f"   Deduction: {result.get('total_deduction', 0):.2f} PLN")
    print(f"   File: {result.get('file_path')}")


def cmd_docs_view(args):
    """View documentation content."""
    endpoint = f"/expenses/project/{args.project_id}/docs/{args.filename}"
    result = api_call("GET", endpoint)
    
    print(result.get('content', 'No content'))


def cmd_docs_history(args):
    """View documentation version history."""
    endpoint = f"/expenses/project/{args.project_id}/docs/{args.filename}/history"
    result = api_call("GET", endpoint)
    
    print(f"\n📜 Version history for {args.filename}")
    print("-" * 60)
    for h in result.get('history', []):
        print(f"  {h['commit']}  {h['date'][:19]}  {h['message']}")


def cmd_expense_qualify(args):
    """Mark expense as B+R qualified."""
    endpoint = f"/expenses/{args.expense_id}"
    data = {
        "br_qualified": True,
        "br_category": args.category,
        "br_deduction_rate": float(args.rate)
    }
    result = api_call("PUT", endpoint, data=data)
    
    print(f"✅ Expense updated")
    print(f"   B+R Qualified: {result.get('br_qualified')}")
    print(f"   Category: {result.get('br_category')}")


def cmd_timesheet_list(args):
    """List timesheet entries."""
    endpoint = f"/timesheet/entries?project_id={args.project_id}&month={args.month}"
    result = api_call("GET", endpoint)
    
    print(f"\n⏰ Timesheet entries for {args.month}")
    print("-" * 60)
    for e in result:
        print(f"  {e.get('date')} | {e.get('worker_name', 'N/A')} | {e.get('hours', 0)}h | {e.get('time_slot', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(
        description="BR System CLI - Command line interface for B+R documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  br_cli.py health                          Check API status
  br_cli.py projects                        List all projects
  br_cli.py expenses -p <project_id>        List expenses
  br_cli.py upload -f invoice.pdf           Upload document for OCR
  br_cli.py docs generate -p <project_id>   Generate documentation
  br_cli.py docs list -p <project_id>       List doc files
  br_cli.py docs view -p <project_id> -f BR_SUMMARY_20260113.md
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Health
    parser_health = subparsers.add_parser("health", help="Check API health")
    parser_health.set_defaults(func=cmd_health)
    
    # Projects
    parser_projects = subparsers.add_parser("projects", help="List projects")
    parser_projects.set_defaults(func=cmd_projects_list)
    
    # Expenses
    parser_expenses = subparsers.add_parser("expenses", help="List expenses")
    parser_expenses.add_argument("-p", "--project-id", default="00000000-0000-0000-0000-000000000001")
    parser_expenses.set_defaults(func=cmd_expenses_list)
    
    # Revenues
    parser_revenues = subparsers.add_parser("revenues", help="Show revenue summary")
    parser_revenues.add_argument("-p", "--project-id", default="00000000-0000-0000-0000-000000000001")
    parser_revenues.add_argument("-y", "--year", type=int, default=2025)
    parser_revenues.set_defaults(func=cmd_revenues_list)
    
    # Upload
    parser_upload = subparsers.add_parser("upload", help="Upload document")
    parser_upload.add_argument("-f", "--file", required=True, help="File to upload")
    parser_upload.add_argument("-p", "--project-id", default="00000000-0000-0000-0000-000000000001")
    parser_upload.add_argument("-t", "--type", default="invoice", help="Document type")
    parser_upload.set_defaults(func=cmd_upload)
    
    # Docs subcommands
    parser_docs = subparsers.add_parser("docs", help="Documentation commands")
    docs_sub = parser_docs.add_subparsers(dest="docs_cmd")
    
    docs_list = docs_sub.add_parser("list", help="List documentation files")
    docs_list.add_argument("-p", "--project-id", default="00000000-0000-0000-0000-000000000001")
    docs_list.set_defaults(func=cmd_docs_list)
    
    docs_gen = docs_sub.add_parser("generate", help="Generate documentation")
    docs_gen.add_argument("-p", "--project-id", default="00000000-0000-0000-0000-000000000001")
    docs_gen.set_defaults(func=cmd_docs_generate)
    
    docs_view = docs_sub.add_parser("view", help="View documentation")
    docs_view.add_argument("-p", "--project-id", default="00000000-0000-0000-0000-000000000001")
    docs_view.add_argument("-f", "--filename", required=True)
    docs_view.set_defaults(func=cmd_docs_view)
    
    docs_history = docs_sub.add_parser("history", help="View version history")
    docs_history.add_argument("-p", "--project-id", default="00000000-0000-0000-0000-000000000001")
    docs_history.add_argument("-f", "--filename", required=True)
    docs_history.set_defaults(func=cmd_docs_history)
    
    # Expense qualify
    parser_qualify = subparsers.add_parser("qualify", help="Mark expense as B+R qualified")
    parser_qualify.add_argument("-e", "--expense-id", required=True)
    parser_qualify.add_argument("-c", "--category", default="materials", 
                                choices=["personnel_employment", "personnel_civil", "materials", 
                                        "equipment", "depreciation", "expertise", "external_services"])
    parser_qualify.add_argument("-r", "--rate", default="1.0", help="Deduction rate (1.0 or 2.0)")
    parser_qualify.set_defaults(func=cmd_expense_qualify)
    
    # Timesheet
    parser_timesheet = subparsers.add_parser("timesheet", help="Timesheet entries")
    parser_timesheet.add_argument("-p", "--project-id", default="00000000-0000-0000-0000-000000000001")
    parser_timesheet.add_argument("-m", "--month", default=datetime.now().strftime("%Y-%m"))
    parser_timesheet.set_defaults(func=cmd_timesheet_list)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    if args.command == "docs" and not hasattr(args, 'func'):
        parser_docs.print_help()
        sys.exit(0)
    
    args.func(args)


if __name__ == "__main__":
    main()
