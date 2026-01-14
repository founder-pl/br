"""
Formatting utilities for B+R documentation.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Union

MONTH_NAMES_PL = {
    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień",
    5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień",
    9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
}


def format_currency(
    value: Optional[Union[int, float, Decimal, str]], 
    currency: str = "PLN",
    show_currency: bool = True
) -> str:
    """
    Format a number as Polish currency.
    
    Args:
        value: The numeric value to format
        currency: Currency code (default: PLN)
        show_currency: Whether to append currency symbol
        
    Returns:
        Formatted string like "1 234,56 zł"
    """
    if value is None:
        return "0,00 zł" if show_currency else "0,00"
    
    try:
        num = float(value) if not isinstance(value, (int, float, Decimal)) else value
        # Format with space as thousands separator and comma as decimal
        formatted = f"{float(num):,.2f}".replace(",", " ").replace(".", ",")
        
        if show_currency:
            if currency == "PLN":
                return f"{formatted} zł"
            return f"{formatted} {currency}"
        return formatted
    except (ValueError, TypeError):
        return str(value)


def format_date(
    value: Optional[Union[str, datetime, date]],
    format_str: str = "%Y-%m-%d"
) -> str:
    """
    Format a date value.
    
    Args:
        value: Date value to format
        format_str: strftime format string
        
    Returns:
        Formatted date string
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (datetime, date)):
        return value.strftime(format_str)
    return str(value)


def format_date_pl(value: Optional[Union[str, datetime, date]]) -> str:
    """Format date in Polish format (DD.MM.YYYY)"""
    return format_date(value, "%d.%m.%Y")


def format_month_pl(month: int, year: Optional[int] = None) -> str:
    """
    Format month name in Polish.
    
    Args:
        month: Month number (1-12)
        year: Optional year to append
        
    Returns:
        Polish month name, optionally with year
    """
    name = MONTH_NAMES_PL.get(month, str(month))
    if year:
        return f"{name} {year}"
    return name


def format_nip(nip: str) -> str:
    """
    Format NIP with standard separators.
    
    Args:
        nip: NIP number (10 digits)
        
    Returns:
        Formatted NIP like "588-191-86-62"
    """
    clean = "".join(c for c in nip if c.isdigit())
    if len(clean) != 10:
        return nip
    return f"{clean[:3]}-{clean[3:6]}-{clean[6:8]}-{clean[8:]}"


def format_percent(
    value: Optional[Union[int, float, Decimal]],
    decimals: int = 1
) -> str:
    """
    Format a decimal or fraction as percentage.
    
    Args:
        value: Value to format (0.5 = 50%, 50 = 50%)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    if value is None:
        return "0%"
    
    try:
        num = float(value)
        # If value is <= 1, treat as fraction (0.5 = 50%)
        if num <= 1:
            num = num * 100
        return f"{num:.{decimals}f}%"
    except (ValueError, TypeError):
        return str(value)


def format_hours(hours: Optional[Union[int, float]]) -> str:
    """
    Format hours with proper Polish declension.
    
    Args:
        hours: Number of hours
        
    Returns:
        Formatted string like "8 godzin"
    """
    if hours is None:
        return "0 godzin"
    
    h = float(hours)
    if h == 1:
        return "1 godzina"
    elif 2 <= h <= 4 or (h % 10 in (2, 3, 4) and h % 100 not in (12, 13, 14)):
        return f"{h:.1f} godziny"
    else:
        return f"{h:.1f} godzin"


def format_nexus(nexus: Optional[Union[float, Decimal]]) -> str:
    """
    Format Nexus indicator value.
    
    Args:
        nexus: Nexus value (0.0 - 1.0)
        
    Returns:
        Formatted string with 4 decimal places
    """
    if nexus is None:
        return "1.0000"
    return f"{float(nexus):.4f}"
