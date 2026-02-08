"""
Flight Search Service — Travel Agent via Kiwi.com Tequila API

Searches for flights (direct only, including low-cost carriers)
and formats results for WhatsApp.

Usage:
    from app.services.flight_search_service import flight_search_service

    results = flight_search_service.search_flights("קפריסין", max_price_eur=100)
    message = flight_search_service.format_results(results)

Environment:
    KIWI_API_KEY — API key from https://tequila.kiwi.com
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import requests

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# DESTINATION MAP — Hebrew trigger → airport/city code
# ═══════════════════════════════════════════════════════════════════════
DESTINATION_MAP = {
    "קפריסין": {"code": "PFO", "name": "פאפוס, קפריסין", "country": "CY", "preferred": "PFO"},
    "פאפוס": {"code": "PFO", "name": "פאפוס, קפריסין", "country": "CY"},
    "לרנקה": {"code": "LCA", "name": "לרנקה, קפריסין", "country": "CY"},
    "יוון": {"code": "ATH", "name": "אתונה, יוון", "country": "GR"},
    "אתונה": {"code": "ATH", "name": "אתונה, יוון", "country": "GR"},
    "רומא": {"code": "FCO", "name": "רומא, איטליה", "country": "IT"},
    "מילאנו": {"code": "MXP", "name": "מילאנו, איטליה", "country": "IT"},
    "ברצלונה": {"code": "BCN", "name": "ברצלונה, ספרד", "country": "ES"},
    "פראג": {"code": "PRG", "name": "פראג, צ'כיה", "country": "CZ"},
    "בודפשט": {"code": "BUD", "name": "בודפשט, הונגריה", "country": "HU"},
    "וינה": {"code": "VIE", "name": "וינה, אוסטריה", "country": "AT"},
    "קרקוב": {"code": "KRK", "name": "קרקוב, פולין", "country": "PL"},
    "ורשה": {"code": "WAW", "name": "ורשה, פולין", "country": "PL"},
    "איסטנבול": {"code": "IST", "name": "איסטנבול, טורקיה", "country": "TR"},
    "אנטליה": {"code": "AYT", "name": "אנטליה, טורקיה", "country": "TR"},
    "תאילנד": {"code": "BKK", "name": "בנגקוק, תאילנד", "country": "TH"},
    "לונדון": {"code": "LON", "name": "לונדון, אנגליה", "country": "GB"},
    "פריז": {"code": "CDG", "name": "פריז, צרפת", "country": "FR"},
    "ברלין": {"code": "BER", "name": "ברלין, גרמניה", "country": "DE"},
    "אמסטרדם": {"code": "AMS", "name": "אמסטרדם, הולנד", "country": "NL"},
}

ORIGIN_AIRPORT = "TLV"  # Tel Aviv Ben Gurion
TEQUILA_API_URL = "https://api.tequila.kiwi.com/v2/search"


class FlightSearchService:
    """Search flights using Kiwi.com Tequila API."""

    def __init__(self):
        self.api_key = os.environ.get("KIWI_API_KEY", "")
        self.is_configured = bool(self.api_key)
        if self.is_configured:
            print("✅ Flight Search Service configured (Kiwi Tequila API)")
        else:
            print("ℹ️  Flight Search Service not configured (KIWI_API_KEY not set)")

    def search_flights(
        self,
        destination_key: str,
        max_price_eur: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        return_from: Optional[str] = None,
        return_to: Optional[str] = None,
        nights_from: int = 2,
        nights_to: int = 7,
        adults: int = 1,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Search for round-trip direct flights.

        Args:
            destination_key: Hebrew destination name (e.g., "קפריסין")
            max_price_eur: Maximum price per person in EUR (round-trip)
            date_from: Search start date (DD/MM/YYYY). Default: tomorrow
            date_to: Search end date (DD/MM/YYYY). Default: +60 days
            return_from: Return date start. If None, uses nights_from/nights_to
            return_to: Return date end
            nights_from: Min nights at destination (default 2)
            nights_to: Max nights at destination (default 7)
            adults: Number of adults (default 1)
            limit: Max results (default 5)

        Returns:
            Dict with 'success', 'flights', 'destination', 'error'
        """
        if not self.is_configured:
            return {"success": False, "flights": [], "error": "KIWI_API_KEY not configured"}

        # Resolve destination
        dest_key = destination_key.strip().lower()
        dest_info = None
        for key, info in DESTINATION_MAP.items():
            if key in dest_key or dest_key in key:
                dest_info = info
                break

        if not dest_info:
            return {
                "success": False,
                "flights": [],
                "error": f"לא מכיר את היעד '{destination_key}'. יעדים זמינים: {', '.join(DESTINATION_MAP.keys())}",
            }

        # Build date ranges
        today = datetime.now()
        if not date_from:
            date_from = (today + timedelta(days=1)).strftime("%d/%m/%Y")
        if not date_to:
            date_to = (today + timedelta(days=60)).strftime("%d/%m/%Y")

        # API parameters
        params = {
            "fly_from": ORIGIN_AIRPORT,
            "fly_to": dest_info["code"],
            "date_from": date_from,
            "date_to": date_to,
            "flight_type": "round",
            "nights_in_dst_from": nights_from,
            "nights_in_dst_to": nights_to,
            "max_stopovers": 0,  # DIRECT FLIGHTS ONLY
            "curr": "EUR",
            "sort": "price",
            "asc": 1,
            "adults": adults,
            "limit": limit,
            "locale": "he",
        }

        if max_price_eur:
            params["price_to"] = max_price_eur

        if return_from:
            params["return_from"] = return_from
            params.pop("nights_in_dst_from", None)
            params.pop("nights_in_dst_to", None)
        if return_to:
            params["return_to"] = return_to

        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            print(f"✈️  Searching flights: {ORIGIN_AIRPORT} → {dest_info['code']} "
                  f"(max €{max_price_eur or 'unlimited'}, {date_from}–{date_to})")

            resp = requests.get(TEQUILA_API_URL, params=params, headers=headers, timeout=30)

            if resp.status_code != 200:
                error_body = resp.text[:500]
                print(f"❌ Kiwi API error {resp.status_code}: {error_body}")
                return {"success": False, "flights": [], "error": f"API error: {resp.status_code}"}

            data = resp.json()
            flights = data.get("data", [])

            print(f"✅ Found {len(flights)} flights (total available: {data.get('_results', 0)})")

            parsed_flights = []
            for f in flights:
                # Parse outbound and return legs
                outbound_legs = [r for r in f.get("route", []) if r.get("return") == 0]
                return_legs = [r for r in f.get("route", []) if r.get("return") == 1]

                outbound_info = outbound_legs[0] if outbound_legs else {}
                return_info = return_legs[0] if return_legs else {}

                parsed_flights.append({
                    "price_eur": f.get("price"),
                    "airline": ", ".join(f.get("airlines", [])),
                    "deep_link": f.get("deep_link", ""),
                    # Outbound
                    "depart_date": _format_datetime(outbound_info.get("local_departure", "")),
                    "depart_time": _format_time(outbound_info.get("local_departure", "")),
                    "arrive_time": _format_time(outbound_info.get("local_arrival", "")),
                    "depart_airport": outbound_info.get("flyFrom", ""),
                    "arrive_airport": outbound_info.get("flyTo", ""),
                    # Return
                    "return_date": _format_datetime(return_info.get("local_departure", "")),
                    "return_depart_time": _format_time(return_info.get("local_departure", "")),
                    "return_arrive_time": _format_time(return_info.get("local_arrival", "")),
                    # Duration
                    "duration_outbound": _format_duration(f.get("duration", {}).get("departure", 0)),
                    "duration_return": _format_duration(f.get("duration", {}).get("return", 0)),
                    "nights": f.get("nightsInDest", "?"),
                })

            return {
                "success": True,
                "flights": parsed_flights,
                "destination": dest_info,
                "total_results": data.get("_results", len(parsed_flights)),
            }

        except requests.Timeout:
            return {"success": False, "flights": [], "error": "Timeout — try again"}
        except Exception as e:
            logger.error(f"Flight search error: {e}")
            print(f"❌ Flight search error: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "flights": [], "error": str(e)}

    def format_results(self, results: Dict[str, Any], query_text: str = "") -> str:
        """Format flight search results for WhatsApp."""
        if not results.get("success"):
            return f"❌ שגיאה בחיפוש טיסות: {results.get('error', 'Unknown error')}"

        flights = results.get("flights", [])
        dest = results.get("destination", {})
        dest_name = dest.get("name", "?")

        if not flights:
            return f"✈️ לא נמצאו טיסות ישירות ל{dest_name} בטווח המחיר המבוקש."

        lines = [f"✈️ *טיסות ישירות ל{dest_name}*"]
        if query_text:
            lines.append(f"🔍 _{query_text}_")
        lines.append(f"📊 נמצאו {results.get('total_results', len(flights))} תוצאות\n")

        for i, f in enumerate(flights, 1):
            lines.append(f"{'─' * 30}")
            lines.append(f"*{i}. €{f['price_eur']}* לאדם (הלוך-חזור)")
            lines.append(f"🛫 חברת תעופה: *{f['airline']}*")
            lines.append(
                f"📅 הלוך: {f['depart_date']} "
                f"({f['depart_time']}→{f['arrive_time']}) "
                f"⏱ {f['duration_outbound']}"
            )
            lines.append(
                f"📅 חזור: {f['return_date']} "
                f"({f['return_depart_time']}→{f['return_arrive_time']}) "
                f"⏱ {f['duration_return']}"
            )
            lines.append(f"🌙 {f['nights']} לילות")
            if f.get("deep_link"):
                lines.append(f"🔗 {f['deep_link']}")
            lines.append("")

        lines.append("_מחירים עשויים להשתנות. מומלץ להזמין מהר!_")
        return "\n".join(lines)

    def search_daily_deals(self) -> Optional[str]:
        """
        Daily deal search: Paphos under €50/person, next 14 days.
        Returns formatted message if deals found, None otherwise.
        """
        today = datetime.now()
        date_from = (today + timedelta(days=1)).strftime("%d/%m/%Y")
        date_to = (today + timedelta(days=14)).strftime("%d/%m/%Y")

        results = self.search_flights(
            destination_key="פאפוס",
            max_price_eur=50,
            date_from=date_from,
            date_to=date_to,
            nights_from=2,
            nights_to=5,
            limit=3,
        )

        if results.get("success") and results.get("flights"):
            msg = self.format_results(results, query_text="דיל יומי — פאפוס מתחת ל-€50")
            return f"🌅 *בוקר טוב! מצאתי דילים:*\n\n{msg}"

        return None


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _format_datetime(iso_str: str) -> str:
    """'2026-03-15T06:30:00.000Z' → '15/03 (ראשון)'"""
    if not iso_str:
        return "?"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        day_names = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
        day_name = day_names[dt.weekday()]
        return f"{dt.strftime('%d/%m')} ({day_name})"
    except Exception:
        return iso_str[:10] if len(iso_str) >= 10 else iso_str


def _format_time(iso_str: str) -> str:
    """'2026-03-15T06:30:00.000Z' → '06:30'"""
    if not iso_str:
        return "?"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception:
        return iso_str[11:16] if len(iso_str) >= 16 else iso_str


def _format_duration(seconds: int) -> str:
    """Duration in seconds → '2h 30m'"""
    if not seconds:
        return "?"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    elif hours:
        return f"{hours}h"
    else:
        return f"{minutes}m"


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════
flight_search_service = FlightSearchService()
