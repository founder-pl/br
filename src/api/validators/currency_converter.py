"""
Currency Converter - Converts foreign currencies to PLN using NBP exchange rates.

Uses the National Bank of Poland (NBP) API to fetch exchange rates.
Includes caching and fallback mechanisms for non-business days.
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict
import httpx
import structlog

logger = structlog.get_logger()


class CurrencyConverter:
    """Konwerter walut z cache'owaniem kursów NBP."""
    
    NBP_API = "https://api.nbp.pl/api/exchangerates/rates/a"
    
    # In-memory cache for exchange rates
    _rate_cache: Dict[str, Decimal] = {}
    
    # Fallback rates (last known rates as of 2026-01)
    FALLBACK_RATES = {
        "USD": Decimal("4.05"),
        "EUR": Decimal("4.35"),
        "GBP": Decimal("5.10"),
        "CHF": Decimal("4.55"),
    }
    
    async def convert_to_pln(
        self,
        amount: Decimal,
        currency: str,
        expense_date: date
    ) -> Decimal:
        """
        Przelicza kwotę na PLN według kursu NBP z dnia wydatku.
        
        Args:
            amount: Kwota do przeliczenia
            currency: Kod waluty ISO (np. USD, EUR)
            expense_date: Data wydatku (do pobrania kursu)
            
        Returns:
            Kwota w PLN zaokrąglona do 2 miejsc po przecinku
        """
        currency = currency.upper().strip()
        
        if currency == "PLN":
            return amount
        
        try:
            rate = await self._get_nbp_rate(currency, expense_date)
            return (amount * rate).quantize(Decimal("0.01"))
        except Exception as e:
            logger.warning(
                "Failed to get NBP rate, using fallback",
                currency=currency,
                date=expense_date,
                error=str(e)
            )
            # Use fallback rate
            fallback = self.FALLBACK_RATES.get(currency)
            if fallback:
                return (amount * fallback).quantize(Decimal("0.01"))
            raise ValueError(f"Nieznana waluta: {currency}")
    
    async def _get_nbp_rate(
        self,
        currency: str,
        target_date: date
    ) -> Decimal:
        """
        Pobiera kurs z API NBP (z fallback na poprzedni dzień roboczy).
        
        NBP nie publikuje kursów w weekendy i święta, więc próbujemy
        do 7 dni wstecz aby znaleźć ostatni dostępny kurs.
        """
        # Check cache first
        cache_key = f"{currency}_{target_date.isoformat()}"
        if cache_key in self._rate_cache:
            return self._rate_cache[cache_key]
        
        # Try to fetch from NBP API (up to 7 days back for weekends/holidays)
        for days_back in range(7):
            check_date = target_date - timedelta(days=days_back)
            url = f"{self.NBP_API}/{currency}/{check_date.isoformat()}/"
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        rate = Decimal(str(data["rates"][0]["mid"]))
                        
                        # Cache the rate
                        self._rate_cache[cache_key] = rate
                        
                        logger.info(
                            "Fetched NBP exchange rate",
                            currency=currency,
                            date=check_date.isoformat(),
                            rate=float(rate)
                        )
                        return rate
                        
                    elif response.status_code == 404:
                        # No rate for this date, try previous day
                        continue
                        
            except httpx.TimeoutException:
                logger.warning("NBP API timeout", currency=currency, date=check_date)
                continue
            except Exception as e:
                logger.warning("NBP API error", currency=currency, error=str(e))
                continue
        
        raise ValueError(
            f"Nie znaleziono kursu {currency} dla daty {target_date} "
            f"(sprawdzono 7 dni wstecz)"
        )
    
    def get_supported_currencies(self) -> list:
        """Returns list of supported currency codes."""
        return ["PLN", "USD", "EUR", "GBP", "CHF", "CZK", "DKK", "NOK", "SEK"]
    
    @classmethod
    def clear_cache(cls):
        """Clears the rate cache."""
        cls._rate_cache.clear()
