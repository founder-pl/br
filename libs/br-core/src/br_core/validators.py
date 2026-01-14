"""
Core validation utilities for B+R documentation.
"""
import re
from datetime import date, datetime
from typing import Optional, Tuple, Union

from .types import ValidationIssue, ValidationSeverity


def validate_nip(nip: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Polish NIP (Tax Identification Number).
    
    Validates:
    - 10 digit format
    - Checksum according to Polish algorithm
    
    Args:
        nip: NIP string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Remove separators
    clean = re.sub(r"[-\s]", "", nip)
    
    if not clean:
        return False, "NIP jest pusty"
    
    if len(clean) != 10:
        return False, f"NIP musi mieć 10 cyfr, podano {len(clean)}"
    
    if not clean.isdigit():
        return False, "NIP może zawierać tylko cyfry"
    
    # Validate checksum
    weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    checksum = sum(int(clean[i]) * weights[i] for i in range(9))
    control = checksum % 11
    
    if control == 10:
        return False, "Nieprawidłowa suma kontrolna NIP"
    
    if control != int(clean[9]):
        return False, f"Nieprawidłowa suma kontrolna NIP (oczekiwano {control}, jest {clean[9]})"
    
    return True, None


def validate_nip_issue(nip: str) -> Optional[ValidationIssue]:
    """
    Validate NIP and return ValidationIssue if invalid.
    
    Args:
        nip: NIP string to validate
        
    Returns:
        ValidationIssue if invalid, None if valid
    """
    valid, error = validate_nip(nip)
    if not valid:
        return ValidationIssue(
            severity=ValidationSeverity.ERROR,
            message=error or "Nieprawidłowy NIP",
            code="INVALID_NIP",
            suggestion="Sprawdź poprawność numeru NIP"
        )
    return None


def validate_date_range(
    start_date: Union[str, date, datetime],
    end_date: Union[str, date, datetime]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that start_date is before end_date.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    def parse_date(d: Union[str, date, datetime]) -> date:
        if isinstance(d, datetime):
            return d.date()
        if isinstance(d, date):
            return d
        if isinstance(d, str):
            return datetime.strptime(d, "%Y-%m-%d").date()
        raise ValueError(f"Invalid date type: {type(d)}")
    
    try:
        start = parse_date(start_date)
        end = parse_date(end_date)
        
        if start > end:
            return False, f"Data początkowa ({start}) jest późniejsza niż końcowa ({end})"
        
        return True, None
    except Exception as e:
        return False, f"Błąd parsowania dat: {e}"


def validate_fiscal_year(
    year: int,
    allow_future: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate fiscal year.
    
    Args:
        year: Year to validate
        allow_future: Whether to allow future years
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    current_year = datetime.now().year
    
    if year < 2004:
        return False, "Rok fiskalny nie może być wcześniejszy niż 2004 (wprowadzenie ulgi B+R)"
    
    if not allow_future and year > current_year:
        return False, f"Rok fiskalny ({year}) nie może być z przyszłości"
    
    if year > current_year + 1:
        return False, f"Rok fiskalny ({year}) jest zbyt daleko w przyszłości"
    
    return True, None


def validate_amount(
    amount: Union[int, float, str],
    min_value: float = 0,
    max_value: Optional[float] = None,
    field_name: str = "Kwota"
) -> Tuple[bool, Optional[str]]:
    """
    Validate monetary amount.
    
    Args:
        amount: Amount to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Field name for error messages
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        value = float(amount)
    except (ValueError, TypeError):
        return False, f"{field_name} musi być liczbą"
    
    if value < min_value:
        return False, f"{field_name} nie może być mniejsza niż {min_value}"
    
    if max_value is not None and value > max_value:
        return False, f"{field_name} nie może przekraczać {max_value}"
    
    return True, None


def validate_percentage(
    value: Union[int, float, str],
    field_name: str = "Wartość procentowa"
) -> Tuple[bool, Optional[str]]:
    """
    Validate percentage value (0-100 or 0-1).
    
    Args:
        value: Percentage value
        field_name: Field name for error messages
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        num = float(value)
    except (ValueError, TypeError):
        return False, f"{field_name} musi być liczbą"
    
    # Accept both 0-1 and 0-100 ranges
    if num < 0:
        return False, f"{field_name} nie może być ujemna"
    
    if num > 100:
        return False, f"{field_name} nie może przekraczać 100%"
    
    return True, None


def validate_nexus(nexus: Union[float, str]) -> Tuple[bool, Optional[str]]:
    """
    Validate Nexus indicator value.
    
    Args:
        nexus: Nexus value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        value = float(nexus)
    except (ValueError, TypeError):
        return False, "Wskaźnik Nexus musi być liczbą"
    
    if value < 0:
        return False, "Wskaźnik Nexus nie może być ujemny"
    
    if value > 1:
        return False, f"Wskaźnik Nexus nie może przekraczać 1.0 (jest {value})"
    
    return True, None
