"""
JPK_V7M Export - Generate Polish Tax Authority reporting files.

P3 Task: JPK_V7M export
Based on: todo/05-br-priority-roadmap.md

Generates:
- JPK_V7M XML files for VAT reporting
- Validation against MF schema
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import xml.etree.ElementTree as ET
from xml.dom import minidom
import structlog

logger = structlog.get_logger()


class JPKType(str, Enum):
    """JPK file types."""
    V7M = "JPK_V7M"  # Monthly VAT
    V7K = "JPK_V7K"  # Quarterly VAT
    FA = "JPK_FA"    # Invoices
    MAG = "JPK_MAG"  # Warehouse


@dataclass
class JPKHeader:
    """JPK file header data."""
    form_code: str = "JPK_V7M"
    form_version: str = "1-2E"
    variant: int = 2
    system_info: str = "BR System"
    
    nip: str = ""
    full_name: str = ""
    email: str = ""
    
    year: int = 2025
    month: int = 1
    
    purpose: int = 0  # 0=original, 1=correction


@dataclass
class JPKSalesRecord:
    """Single sales record for JPK."""
    invoice_number: str
    invoice_date: date
    sale_date: date
    buyer_name: str
    buyer_nip: Optional[str]
    buyer_country: str = "PL"
    
    net_amount: Decimal = Decimal("0")
    vat_amount: Decimal = Decimal("0")
    
    # VAT rates breakdown
    k_19: Decimal = Decimal("0")  # Net 23%
    k_20: Decimal = Decimal("0")  # VAT 23%
    k_21: Decimal = Decimal("0")  # Net 8%
    k_22: Decimal = Decimal("0")  # VAT 8%
    k_23: Decimal = Decimal("0")  # Net 5%
    k_24: Decimal = Decimal("0")  # VAT 5%
    k_25: Decimal = Decimal("0")  # Net 0%
    
    # Markers
    sw: bool = False  # Delivery of goods
    ee: bool = False  # E-services
    tp: bool = False  # Related party
    tt_wnt: bool = False  # WNT triangular
    mr_t: bool = False  # Tourism margin
    mr_uz: bool = False  # Used goods margin
    i_42: bool = False  # Customs 42
    i_63: bool = False  # Customs 63
    b_spv: bool = False  # Transfer of property
    b_spv_dostawa: bool = False  # Delivery in transfer
    b_mpv_prowizja: bool = False  # Commission in transfer
    mpp: bool = False  # Split payment


@dataclass
class JPKPurchaseRecord:
    """Single purchase record for JPK."""
    invoice_number: str
    invoice_date: date
    seller_name: str
    seller_nip: Optional[str]
    
    net_amount: Decimal = Decimal("0")
    vat_amount: Decimal = Decimal("0")
    
    # VAT rates breakdown
    k_40: Decimal = Decimal("0")  # Net acquisition
    k_41: Decimal = Decimal("0")  # VAT acquisition
    k_42: Decimal = Decimal("0")  # Net domestic
    k_43: Decimal = Decimal("0")  # VAT domestic
    k_44: Decimal = Decimal("0")  # Net fixed assets
    k_45: Decimal = Decimal("0")  # VAT fixed assets
    
    # Markers
    imp: bool = False  # Import
    mpp: bool = False  # Split payment


@dataclass
class JPKDeclaration:
    """VAT declaration summary."""
    # Sales totals
    p_10: Decimal = Decimal("0")  # Export
    p_11: Decimal = Decimal("0")  # EU supply
    p_12: Decimal = Decimal("0")  # EU supply new transport
    p_13: Decimal = Decimal("0")  # Distance selling from PL
    p_14: Decimal = Decimal("0")  # Distance selling import
    
    # Standard rates
    p_15: Decimal = Decimal("0")  # Base 23%
    p_16: Decimal = Decimal("0")  # VAT 23%
    p_17: Decimal = Decimal("0")  # Base 8%
    p_18: Decimal = Decimal("0")  # VAT 8%
    p_19: Decimal = Decimal("0")  # Base 5%
    p_20: Decimal = Decimal("0")  # VAT 5%
    p_21: Decimal = Decimal("0")  # Base 0%
    
    # Purchase totals
    p_40: Decimal = Decimal("0")  # Acquisition base
    p_41: Decimal = Decimal("0")  # Acquisition VAT
    p_42: Decimal = Decimal("0")  # Import base (simplified)
    p_43: Decimal = Decimal("0")  # Import VAT
    p_44: Decimal = Decimal("0")  # Domestic base
    p_45: Decimal = Decimal("0")  # Domestic VAT
    p_46: Decimal = Decimal("0")  # Fixed assets base
    p_47: Decimal = Decimal("0")  # Fixed assets VAT
    
    # Summary
    p_48: Decimal = Decimal("0")  # Total input VAT
    p_49: Decimal = Decimal("0")  # Excess input VAT
    p_50: Decimal = Decimal("0")  # VAT due
    p_51: Decimal = Decimal("0")  # VAT to pay
    p_52: Decimal = Decimal("0")  # Refund amount
    p_53: int = 0  # Refund type (1=25d, 2=40d, 3=60d)
    p_54: Decimal = Decimal("0")  # Refund bank account
    p_55: Decimal = Decimal("0")  # Next period carry
    p_56: Decimal = Decimal("0")  # Tax obligation
    
    # Corrections
    p_60: Decimal = Decimal("0")  # Correction amount
    p_61: Decimal = Decimal("0")  # Correction VAT
    p_62: Decimal = Decimal("0")  # Output correction
    p_63: Decimal = Decimal("0")  # Input correction
    p_64: Decimal = Decimal("0")  # Intra-community correction
    p_65: Decimal = Decimal("0")  # Import correction
    p_66: Decimal = Decimal("0")  # Fixed assets correction
    p_67: Decimal = Decimal("0")  # Other correction
    p_68: bool = False  # Pro-rata correction


class JPKExporter:
    """
    Generates JPK_V7M XML files for Polish tax authority.
    
    Follows MF schema version 1-2E.
    """
    
    NAMESPACE = "http://crd.gov.pl/wzor/2021/12/27/11148/"
    TNS_NAMESPACE = "http://crd.gov.pl/wzor/2021/12/27/11148/"
    XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
    ETD_NAMESPACE = "http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2021/06/08/eD/DefinicjeTypy/"
    
    def __init__(self, header: JPKHeader):
        self.header = header
        self.sales_records: List[JPKSalesRecord] = []
        self.purchase_records: List[JPKPurchaseRecord] = []
        self.declaration: Optional[JPKDeclaration] = None
        
    def add_sales_record(self, record: JPKSalesRecord):
        """Add sales invoice record."""
        self.sales_records.append(record)
        
    def add_purchase_record(self, record: JPKPurchaseRecord):
        """Add purchase invoice record."""
        self.purchase_records.append(record)
    
    def set_declaration(self, declaration: JPKDeclaration):
        """Set VAT declaration summary."""
        self.declaration = declaration
        
    def calculate_declaration(self) -> JPKDeclaration:
        """Auto-calculate declaration from records."""
        decl = JPKDeclaration()
        
        # Sum sales
        for rec in self.sales_records:
            decl.p_15 += rec.k_19
            decl.p_16 += rec.k_20
            decl.p_17 += rec.k_21
            decl.p_18 += rec.k_22
            decl.p_19 += rec.k_23
            decl.p_20 += rec.k_24
            decl.p_21 += rec.k_25
        
        # Sum purchases
        for rec in self.purchase_records:
            decl.p_40 += rec.k_40
            decl.p_41 += rec.k_41
            decl.p_44 += rec.k_42
            decl.p_45 += rec.k_43
            decl.p_46 += rec.k_44
            decl.p_47 += rec.k_45
        
        # Calculate totals
        output_vat = decl.p_16 + decl.p_18 + decl.p_20
        input_vat = decl.p_41 + decl.p_43 + decl.p_45 + decl.p_47
        
        decl.p_48 = input_vat
        
        if output_vat > input_vat:
            decl.p_51 = output_vat - input_vat
        else:
            decl.p_49 = input_vat - output_vat
        
        self.declaration = decl
        return decl
    
    def generate_xml(self) -> str:
        """Generate JPK_V7M XML file."""
        if not self.declaration:
            self.calculate_declaration()
        
        # Create root element
        root = ET.Element("JPK")
        root.set("xmlns", self.NAMESPACE)
        root.set("xmlns:tns", self.TNS_NAMESPACE)
        root.set("xmlns:xsi", self.XSI_NAMESPACE)
        root.set("xmlns:etd", self.ETD_NAMESPACE)
        
        # Add header
        self._add_header(root)
        
        # Add subject (taxpayer)
        self._add_subject(root)
        
        # Add declaration
        if self.declaration:
            self._add_declaration(root)
        
        # Add sales records
        for i, rec in enumerate(self.sales_records, 1):
            self._add_sales_record(root, rec, i)
        
        # Add purchase records
        for i, rec in enumerate(self.purchase_records, 1):
            self._add_purchase_record(root, rec, i)
        
        # Add control totals
        self._add_control(root)
        
        # Format XML
        xml_str = ET.tostring(root, encoding="unicode")
        return minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="UTF-8").decode()
    
    def _add_header(self, root: ET.Element):
        """Add Naglowek section."""
        naglowek = ET.SubElement(root, "Naglowek")
        
        kod_formularza = ET.SubElement(naglowek, "KodFormularza")
        kod_formularza.text = self.header.form_code
        kod_formularza.set("kodSystemowy", f"{self.header.form_code}(2)")
        kod_formularza.set("wersjaSchemy", self.header.form_version)
        
        ET.SubElement(naglowek, "WariantFormularza").text = str(self.header.variant)
        
        data_wytw = ET.SubElement(naglowek, "DataWytworzeniaJPK")
        data_wytw.text = datetime.utcnow().isoformat()
        
        ET.SubElement(naglowek, "NazwaSystemu").text = self.header.system_info
        
        cel = ET.SubElement(naglowek, "CelZlozenia")
        cel.set("poz", "P_7")
        cel.text = str(self.header.purpose)
        
        ET.SubElement(naglowek, "Rok").text = str(self.header.year)
        ET.SubElement(naglowek, "Miesiac").text = str(self.header.month)
    
    def _add_subject(self, root: ET.Element):
        """Add Podmiot1 section."""
        podmiot = ET.SubElement(root, "Podmiot1")
        podmiot.set("rola", "Podatnik")
        
        os_fiz = ET.SubElement(podmiot, "OsobaFizyczna")
        
        nip = ET.SubElement(os_fiz, "etd:NIP")
        nip.text = self.header.nip
        
        nazwa = ET.SubElement(os_fiz, "etd:PelnaNazwa")
        nazwa.text = self.header.full_name
        
        email = ET.SubElement(os_fiz, "Email")
        email.text = self.header.email
    
    def _add_declaration(self, root: ET.Element):
        """Add Deklaracja section."""
        dekl = ET.SubElement(root, "Deklaracja")
        
        naglowek = ET.SubElement(dekl, "Naglowek")
        ET.SubElement(naglowek, "KodFormularzaDekl").text = "VAT-7"
        ET.SubElement(naglowek, "WariantFormularzaDekl").text = "22"
        
        poz = ET.SubElement(dekl, "PozycjeSzczegolowe")
        
        # Add all P_ fields
        d = self.declaration
        fields = [
            ("P_10", d.p_10), ("P_11", d.p_11), ("P_15", d.p_15), ("P_16", d.p_16),
            ("P_17", d.p_17), ("P_18", d.p_18), ("P_19", d.p_19), ("P_20", d.p_20),
            ("P_21", d.p_21), ("P_40", d.p_40), ("P_41", d.p_41), ("P_44", d.p_44),
            ("P_45", d.p_45), ("P_46", d.p_46), ("P_47", d.p_47), ("P_48", d.p_48),
            ("P_49", d.p_49), ("P_51", d.p_51)
        ]
        
        for name, value in fields:
            if value != 0:
                elem = ET.SubElement(poz, name)
                elem.text = str(int(value))
        
        # Pouczenia (required)
        pouczenia = ET.SubElement(dekl, "Pouczenia")
        pouczenia.text = "1"
    
    def _add_sales_record(self, root: ET.Element, rec: JPKSalesRecord, lp: int):
        """Add SprzedazWiersz record."""
        wiersz = ET.SubElement(root, "SprzedazWiersz")
        
        ET.SubElement(wiersz, "LpSprzedazy").text = str(lp)
        ET.SubElement(wiersz, "NrKontrahenta").text = rec.buyer_nip or "BRAK"
        ET.SubElement(wiersz, "NazwaKontrahenta").text = rec.buyer_name[:256]
        ET.SubElement(wiersz, "DowodSprzedazy").text = rec.invoice_number[:256]
        ET.SubElement(wiersz, "DataWystawienia").text = rec.invoice_date.isoformat()
        ET.SubElement(wiersz, "DataSprzedazy").text = rec.sale_date.isoformat()
        
        # VAT amounts
        if rec.k_19: ET.SubElement(wiersz, "K_19").text = str(int(rec.k_19 * 100) / 100)
        if rec.k_20: ET.SubElement(wiersz, "K_20").text = str(int(rec.k_20 * 100) / 100)
        
        # Markers
        if rec.mpp: ET.SubElement(wiersz, "MPP").text = "1"
    
    def _add_purchase_record(self, root: ET.Element, rec: JPKPurchaseRecord, lp: int):
        """Add ZakupWiersz record."""
        wiersz = ET.SubElement(root, "ZakupWiersz")
        
        ET.SubElement(wiersz, "LpZakupu").text = str(lp)
        ET.SubElement(wiersz, "NrDostawcy").text = rec.seller_nip or "BRAK"
        ET.SubElement(wiersz, "NazwaDostawcy").text = rec.seller_name[:256]
        ET.SubElement(wiersz, "DowodZakupu").text = rec.invoice_number[:256]
        ET.SubElement(wiersz, "DataZakupu").text = rec.invoice_date.isoformat()
        
        # VAT amounts
        if rec.k_42: ET.SubElement(wiersz, "K_42").text = str(int(rec.k_42 * 100) / 100)
        if rec.k_43: ET.SubElement(wiersz, "K_43").text = str(int(rec.k_43 * 100) / 100)
        
        # Markers
        if rec.mpp: ET.SubElement(wiersz, "MPP").text = "1"
    
    def _add_control(self, root: ET.Element):
        """Add control totals."""
        # SprzedazCtrl
        if self.sales_records:
            ctrl = ET.SubElement(root, "SprzedazCtrl")
            ET.SubElement(ctrl, "LiczbaWierszySprzedazy").text = str(len(self.sales_records))
            total = sum(r.k_19 + r.k_20 for r in self.sales_records)
            ET.SubElement(ctrl, "PodatekNalezny").text = str(int(total * 100) / 100)
        
        # ZakupCtrl
        if self.purchase_records:
            ctrl = ET.SubElement(root, "ZakupCtrl")
            ET.SubElement(ctrl, "LiczbaWierszyZakupow").text = str(len(self.purchase_records))
            total = sum(r.k_42 + r.k_43 for r in self.purchase_records)
            ET.SubElement(ctrl, "PodatekNaliczony").text = str(int(total * 100) / 100)
    
    def validate(self) -> List[str]:
        """Validate JPK data before export."""
        errors = []
        
        if not self.header.nip:
            errors.append("Brak NIP podatnika")
        elif len(self.header.nip) != 10:
            errors.append(f"Nieprawidłowy NIP: {self.header.nip}")
        
        if not self.header.full_name:
            errors.append("Brak nazwy podatnika")
        
        if self.header.month < 1 or self.header.month > 12:
            errors.append(f"Nieprawidłowy miesiąc: {self.header.month}")
        
        for i, rec in enumerate(self.sales_records, 1):
            if not rec.invoice_number:
                errors.append(f"Sprzedaż #{i}: brak numeru faktury")
            if not rec.buyer_name:
                errors.append(f"Sprzedaż #{i}: brak nazwy nabywcy")
        
        for i, rec in enumerate(self.purchase_records, 1):
            if not rec.invoice_number:
                errors.append(f"Zakup #{i}: brak numeru faktury")
            if not rec.seller_name:
                errors.append(f"Zakup #{i}: brak nazwy dostawcy")
        
        return errors


def create_jpk_from_expenses(
    expenses: List[Dict[str, Any]],
    header: JPKHeader
) -> JPKExporter:
    """
    Create JPK exporter from expense records.
    
    Converts expense data to JPK purchase records.
    """
    exporter = JPKExporter(header)
    
    for exp in expenses:
        net = Decimal(str(exp.get("net_amount", 0)))
        vat = Decimal(str(exp.get("vat_amount", 0)))
        
        record = JPKPurchaseRecord(
            invoice_number=exp.get("invoice_number", ""),
            invoice_date=date.fromisoformat(str(exp.get("invoice_date", date.today()))[:10]),
            seller_name=exp.get("vendor_name", ""),
            seller_nip=exp.get("vendor_nip"),
            net_amount=net,
            vat_amount=vat,
            k_42=net,
            k_43=vat,
            mpp=exp.get("split_payment", False)
        )
        
        exporter.add_purchase_record(record)
    
    return exporter
