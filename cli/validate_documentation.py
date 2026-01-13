#!/usr/bin/env python3
"""
CLI tool to validate B+R documentation against brgenerator requirements.

Usage:
    python validate_documentation.py --project-id <id>
    python validate_documentation.py --file <path.md>
    python validate_documentation.py --url <api_url>
"""
import argparse
import json
import sys
import os
from datetime import datetime

try:
    import requests
    import yaml
except ImportError:
    print("Installing dependencies...")
    os.system("pip install requests pyyaml")
    import requests
    import yaml

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_documentation_validation import BRDocumentationValidator, Severity

API_BASE = os.environ.get("BR_API_URL", "http://localhost:8020")


def fetch_documentation(project_id: str, filename: str = None) -> str:
    """Fetch documentation from API."""
    # Get list of docs
    resp = requests.get(f"{API_BASE}/expenses/project/{project_id}/docs")
    resp.raise_for_status()
    files = resp.json().get('files', [])
    
    if not files:
        raise ValueError(f"No documentation found for project {project_id}")
    
    # Get latest or specified file
    if filename:
        target = filename
    else:
        # Get latest
        if isinstance(files[0], dict):
            target = files[0].get('filename')
        else:
            target = files[0]
    
    # Fetch content
    resp = requests.get(f"{API_BASE}/expenses/project/{project_id}/docs/{target}")
    resp.raise_for_status()
    return resp.json().get('content', '')


def validate_and_report(content: str, output_format: str = 'text') -> dict:
    """Run validation and generate report."""
    validator = BRDocumentationValidator(content)
    results = validator.validate_all()
    report = validator.get_full_report()
    
    return report


def print_report(report: dict, output_format: str = 'text'):
    """Print validation report."""
    summary = report['validation_summary']
    
    if output_format == 'json':
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    
    if output_format == 'yaml':
        print(yaml.dump(report, allow_unicode=True, default_flow_style=False))
        return
    
    # Text format
    print("\n" + "=" * 70)
    print("📋 RAPORT WALIDACJI DOKUMENTACJI B+R")
    print("=" * 70)
    print(f"\n📅 Data: {summary['timestamp'][:19]}")
    print(f"📊 Wynik ogólny: {summary['overall_score']:.1%}")
    print(f"📌 Status: {_status_icon(summary['overall_status'])} {summary['overall_status'].upper()}")
    print(f"🔢 Etapów: {summary['stages_completed']}")
    print(f"⚠️  Problemów: {report['total_issues']} (krytycznych: {report['critical_issues']})")
    
    print("\n" + "-" * 70)
    print("WYNIKI POSZCZEGÓLNYCH ETAPÓW WALIDACJI")
    print("-" * 70)
    
    for stage in report['stage_reports']:
        status_icon = _status_icon(stage['status'])
        print(f"\n{status_icon} {stage['validation_stage'].replace('_', ' ').title()}")
        print(f"   Score: {stage['score']:.1%} | Status: {stage['status']}")
        
        if stage['issues']:
            print("   Problemy:")
            for issue in stage['issues']:
                severity_icon = _severity_icon(issue['severity'])
                print(f"   {severity_icon} [{issue['severity'].upper()}] {issue['message']}")
                if issue['suggestion']:
                    print(f"      💡 {issue['suggestion']}")
    
    print("\n" + "=" * 70)
    
    # Recommendations
    if report['critical_issues'] > 0:
        print("\n🚨 WYMAGANE DZIAŁANIA:")
        print("   Dokumentacja zawiera błędy krytyczne, które należy poprawić")
        print("   przed złożeniem do urzędu skarbowego.")
    elif summary['overall_score'] < 0.8:
        print("\n⚠️  ZALECANE DZIAŁANIA:")
        print("   Dokumentacja wymaga uzupełnień. Przejrzyj ostrzeżenia powyżej.")
    else:
        print("\n✅ DOKUMENTACJA ZGODNA Z WYMAGANIAMI")
        print("   Dokument spełnia podstawowe wymogi dokumentacji B+R.")


def _status_icon(status: str) -> str:
    return {"passed": "✅", "warning": "⚠️", "failed": "❌"}.get(status, "❓")


def _severity_icon(severity: str) -> str:
    return {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")


def main():
    parser = argparse.ArgumentParser(
        description="Validate B+R documentation against brgenerator requirements"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--project-id", help="Project ID to validate")
    group.add_argument("-f", "--file", help="Local markdown file to validate")
    
    parser.add_argument("--filename", help="Specific doc filename (default: latest)")
    parser.add_argument("-o", "--output", choices=['text', 'json', 'yaml'], 
                        default='text', help="Output format")
    parser.add_argument("--save", help="Save report to file")
    
    args = parser.parse_args()
    
    try:
        if args.file:
            # Read local file
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"📄 Validating local file: {args.file}")
        else:
            # Fetch from API
            content = fetch_documentation(args.project_id, args.filename)
            print(f"📄 Validating project: {args.project_id}")
        
        report = validate_and_report(content, args.output)
        print_report(report, args.output)
        
        if args.save:
            with open(args.save, 'w', encoding='utf-8') as f:
                if args.save.endswith('.yaml') or args.save.endswith('.yml'):
                    yaml.dump(report, f, allow_unicode=True, default_flow_style=False)
                else:
                    json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n📁 Raport zapisany do: {args.save}")
        
        # Exit code based on status
        if report['critical_issues'] > 0:
            sys.exit(2)
        elif report['validation_summary']['overall_score'] < 0.7:
            sys.exit(1)
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Błąd: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
