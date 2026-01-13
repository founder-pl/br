#!/usr/bin/env python3
"""
Generate sample PDF invoices for testing invoice type detection.
Creates both cost (expense) and revenue invoices.
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Try to use reportlab for PDF generation, fallback to HTML
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("Note: reportlab not installed, generating HTML invoices instead")

OUTPUT_DIR = Path(__file__).parent / "sample_invoices"
OUTPUT_DIR.mkdir(exist_ok=True)

# Our company data
OUR_COMPANY = {
    "name": "Tomasz Sapletta",
    "nip": "5881918662",
    "address": "ul. Testowa 1, 00-001 Warszawa"
}

# Sample vendors (for cost invoices)
VENDORS = [
    {"name": "InsERT S.A.", "nip": "5542926469", "address": "ul. Programistów 10, 50-001 Wrocław"},
    {"name": "CloudTech Sp. z o.o.", "nip": "1234567890", "address": "ul. Chmurowa 5, 30-001 Kraków"},
    {"name": "DataLab Sp. z o.o.", "nip": "9876543210", "address": "ul. Naukowa 15, 60-001 Poznań"},
]

# Sample clients (for revenue invoices)
CLIENTS = [
    {"name": "Klient ABC Sp. z o.o.", "nip": "1111111111", "address": "ul. Biznesowa 20, 00-002 Warszawa"},
    {"name": "TechCorp S.A.", "nip": "2222222222", "address": "ul. Korporacyjna 30, 40-001 Katowice"},
]


def generate_html_invoice(invoice_data: dict, output_path: Path):
    """Generate invoice as HTML file."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Faktura {invoice_data['number']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .parties {{ display: flex; justify-content: space-between; margin: 20px 0; }}
        .party {{ width: 45%; }}
        .totals {{ text-align: right; margin-top: 20px; }}
        .nip {{ font-weight: bold; color: #0066cc; }}
    </style>
</head>
<body>
    <h1>FAKTURA VAT {invoice_data['number']}</h1>
    <p>Data wystawienia: {invoice_data['date']}</p>
    
    <div class="parties">
        <div class="party">
            <h3>Sprzedawca:</h3>
            <p><strong>{invoice_data['seller']['name']}</strong></p>
            <p>NIP: <span class="nip">{invoice_data['seller']['nip']}</span></p>
            <p>{invoice_data['seller']['address']}</p>
        </div>
        <div class="party">
            <h3>Nabywca:</h3>
            <p><strong>{invoice_data['buyer']['name']}</strong></p>
            <p>NIP: <span class="nip">{invoice_data['buyer']['nip']}</span></p>
            <p>{invoice_data['buyer']['address']}</p>
        </div>
    </div>
    
    <table>
        <tr>
            <th>Lp.</th>
            <th>Nazwa</th>
            <th>Ilość</th>
            <th>Cena netto</th>
            <th>VAT</th>
            <th>Wartość brutto</th>
        </tr>
        <tr>
            <td>1</td>
            <td>{invoice_data['description']}</td>
            <td>1</td>
            <td>{invoice_data['net']:.2f} PLN</td>
            <td>23%</td>
            <td>{invoice_data['gross']:.2f} PLN</td>
        </tr>
    </table>
    
    <div class="totals">
        <p><strong>Suma netto:</strong> {invoice_data['net']:.2f} PLN</p>
        <p><strong>VAT 23%:</strong> {invoice_data['vat']:.2f} PLN</p>
        <p><strong>RAZEM BRUTTO:</strong> {invoice_data['gross']:.2f} PLN</p>
    </div>
</body>
</html>"""
    
    output_path.write_text(html, encoding='utf-8')
    print(f"  ✅ Generated: {output_path}")


def generate_pdf_invoice(invoice_data: dict, output_path: Path):
    """Generate invoice as PDF file using reportlab."""
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    
    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2*cm, height - 2*cm, f"FAKTURA VAT {invoice_data['number']}")
    
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, height - 2.8*cm, f"Data wystawienia: {invoice_data['date']}")
    
    # Seller
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, height - 4*cm, "Sprzedawca:")
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, height - 4.6*cm, invoice_data['seller']['name'])
    c.drawString(2*cm, height - 5.1*cm, f"NIP: {invoice_data['seller']['nip']}")
    c.drawString(2*cm, height - 5.6*cm, invoice_data['seller']['address'])
    
    # Buyer
    c.setFont("Helvetica-Bold", 12)
    c.drawString(11*cm, height - 4*cm, "Nabywca:")
    c.setFont("Helvetica", 10)
    c.drawString(11*cm, height - 4.6*cm, invoice_data['buyer']['name'])
    c.drawString(11*cm, height - 5.1*cm, f"NIP: {invoice_data['buyer']['nip']}")
    c.drawString(11*cm, height - 5.6*cm, invoice_data['buyer']['address'])
    
    # Table header
    y = height - 7.5*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2*cm, y, "Nazwa")
    c.drawString(10*cm, y, "Netto")
    c.drawString(13*cm, y, "VAT")
    c.drawString(16*cm, y, "Brutto")
    
    # Table row
    y -= 0.6*cm
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, y, invoice_data['description'][:40])
    c.drawString(10*cm, y, f"{invoice_data['net']:.2f} PLN")
    c.drawString(13*cm, y, "23%")
    c.drawString(16*cm, y, f"{invoice_data['gross']:.2f} PLN")
    
    # Totals
    y -= 1.5*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(13*cm, y, f"Suma netto: {invoice_data['net']:.2f} PLN")
    y -= 0.5*cm
    c.drawString(13*cm, y, f"VAT 23%: {invoice_data['vat']:.2f} PLN")
    y -= 0.5*cm
    c.drawString(13*cm, y, f"RAZEM: {invoice_data['gross']:.2f} PLN")
    
    c.save()
    print(f"  ✅ Generated: {output_path}")


def generate_invoice(invoice_data: dict, output_path: Path):
    """Generate invoice in best available format."""
    if HAS_REPORTLAB:
        generate_pdf_invoice(invoice_data, output_path.with_suffix('.pdf'))
    else:
        generate_html_invoice(invoice_data, output_path.with_suffix('.html'))


def main():
    print("\n🧾 Generating sample invoices for testing...\n")
    
    # Generate COST invoices (we are the buyer)
    print("📥 COST INVOICES (faktury kosztowe):")
    for i, vendor in enumerate(VENDORS, 1):
        net = 1000.0 * i
        vat = net * 0.23
        gross = net + vat
        
        invoice_data = {
            "number": f"FV/COST/2025/{i:03d}",
            "date": f"2025-12-{10+i:02d}",
            "seller": vendor,
            "buyer": OUR_COMPANY,
            "description": f"Usługi B+R - iteracja {i}",
            "net": net,
            "vat": vat,
            "gross": gross
        }
        
        output_path = OUTPUT_DIR / f"cost_invoice_{i:03d}"
        generate_invoice(invoice_data, output_path)
    
    print()
    
    # Generate REVENUE invoices (we are the seller)
    print("📤 REVENUE INVOICES (faktury przychodowe):")
    for i, client in enumerate(CLIENTS, 1):
        net = 5000.0 * i
        vat = net * 0.23
        gross = net + vat
        
        invoice_data = {
            "number": f"FV/REV/2025/{i:03d}",
            "date": f"2025-12-{20+i:02d}",
            "seller": OUR_COMPANY,  # WE are the seller
            "buyer": client,
            "description": f"Licencja oprogramowania B+R v{i}.0",
            "net": net,
            "vat": vat,
            "gross": gross
        }
        
        output_path = OUTPUT_DIR / f"revenue_invoice_{i:03d}"
        generate_invoice(invoice_data, output_path)
    
    print(f"\n✅ Sample invoices saved to: {OUTPUT_DIR}")
    print("\nTo test invoice detection:")
    print(f"  python cli/br_cli.py upload -f {OUTPUT_DIR}/cost_invoice_001.html")
    print(f"  python cli/br_cli.py upload -f {OUTPUT_DIR}/revenue_invoice_001.html")


if __name__ == "__main__":
    main()
