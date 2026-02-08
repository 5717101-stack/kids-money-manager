"""
Flight Search Service — Travel Agent

Hybrid cascade strategy for best data quality:
  1. Amadeus (primary — returns BOTH legs with full times in a single response)
  2. SerpAPI Google Flights (fallback — broader coverage, low-cost carriers)
  3. Kiwi.com Tequila API (fallback)

Each provider is tried in order; if the first returns results, we use it.
If it returns no results or errors, we cascade to the next.

Searches for flights (direct only, including low-cost carriers like
Wizz Air, Ryanair, easyJet, Pegasus, etc.) and formats results for WhatsApp.

Usage:
    from app.services.flight_search_service import flight_search_service

    results = flight_search_service.search_flights("קפריסין", max_price_eur=100)
    message = flight_search_service.format_results(results)

Environment:
    AMADEUS_API_KEY + AMADEUS_API_SECRET — from https://developers.amadeus.com (primary)
    SERPAPI_KEY — from https://serpapi.com (fallback, Google Flights data)
    KIWI_API_KEY — from https://tequila.kiwi.com (fallback)
"""

import os
import logging
import time
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
    "רודוס": {"code": "RHO", "name": "רודוס, יוון", "country": "GR"},
    "כרתים": {"code": "HER", "name": "כרתים, יוון", "country": "GR"},
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

# ═══════════════════════════════════════════════════════════════════════
# AIRLINE CODE → NAME MAP (common airlines from TLV)
# ═══════════════════════════════════════════════════════════════════════
AIRLINE_NAMES = {
    "LY": "El Al", "6H": "Israir", "IZ": "Arkia",
    "W6": "Wizz Air", "FR": "Ryanair", "U2": "easyJet",
    "W4": "Wizz Air Malta", "5O": "ASL Airlines",
    "TK": "Turkish Airlines", "PC": "Pegasus",
    "A3": "Aegean", "CY": "Cyprus Airways",
    "LH": "Lufthansa", "AF": "Air France", "BA": "British Airways",
    "AZ": "ITA Airways", "VY": "Vueling", "OS": "Austrian",
    "LO": "LOT Polish", "OK": "Czech Airlines",
    "RO": "TAROM", "BT": "airBaltic",
}


class FlightSearchService:
    """Search flights using SerpAPI (Google Flights), Amadeus, or Kiwi (auto-detect)."""

    def __init__(self):
        self._amadeus_token = None
        self._amadeus_token_expiry = 0
        self._configure()

    def _configure(self):
        """(Re)read credentials from env vars. Called at init and lazily on first use."""
        # ── Amadeus config (PRIMARY — returns complete round-trip data) ──
        self.amadeus_key = os.environ.get("AMADEUS_API_KEY", "")
        self.amadeus_secret = os.environ.get("AMADEUS_API_SECRET", "")
        self.amadeus_configured = bool(self.amadeus_key and self.amadeus_secret)

        # ── SerpAPI config (fallback — Google Flights, broader low-cost coverage) ──
        self.serpapi_key = os.environ.get("SERPAPI_KEY", "")
        self.serpapi_configured = bool(self.serpapi_key)

        # ── Kiwi config (fallback) ──
        self.kiwi_key = os.environ.get("KIWI_API_KEY", "")
        self.kiwi_configured = bool(self.kiwi_key)

        # ── Overall status ──
        self.is_configured = self.amadeus_configured or self.serpapi_configured or self.kiwi_configured

        providers = []
        if self.amadeus_configured:
            providers.append("Amadeus (primary)")
        if self.serpapi_configured:
            providers.append("SerpAPI/Google Flights (fallback)")
        if self.kiwi_configured:
            providers.append("Kiwi (fallback)")

        if providers:
            print(f"✅ Flight Search Service: {', '.join(providers)}")
        else:
            print("ℹ️  Flight Search Service not configured (set AMADEUS_API_KEY+SECRET, SERPAPI_KEY, or KIWI_API_KEY)")

    # ═══════════════════════════════════════════════════════════════════
    # SERPAPI SEARCH (primary — Google Flights data, includes low-cost)
    # ═══════════════════════════════════════════════════════════════════
    def _search_serpapi(
        self, dest_info, max_price_eur, date_from, date_to,
        nights_from, nights_to, adults, limit
    ) -> Dict[str, Any]:
        """
        Search flights via SerpAPI Google Flights API.
        Includes ALL carriers (low-cost: Wizz Air, Ryanair, easyJet, etc.)
        """
        today = datetime.now()

        # Parse date range
        if date_from:
            try:
                start_date = datetime.strptime(date_from, "%d/%m/%Y")
            except ValueError:
                start_date = today + timedelta(days=1)
        else:
            start_date = today + timedelta(days=1)

        if date_to:
            try:
                end_date = datetime.strptime(date_to, "%d/%m/%Y")
            except ValueError:
                end_date = today + timedelta(days=60)
        else:
            end_date = today + timedelta(days=60)

        all_flights = []
        api_calls = 0
        max_api_calls = 8  # SerpAPI costs per call, be efficient

        # Search every 4th day in the range
        search_date = start_date
        while search_date <= end_date and api_calls < max_api_calls:
            for stay_nights in range(nights_from, min(nights_to + 1, nights_from + 3)):
                if api_calls >= max_api_calls:
                    break

                return_date = search_date + timedelta(days=stay_nights)

                params = {
                    "engine": "google_flights",
                    "departure_id": ORIGIN_AIRPORT,
                    "arrival_id": dest_info["code"],
                    "outbound_date": search_date.strftime("%Y-%m-%d"),
                    "return_date": return_date.strftime("%Y-%m-%d"),
                    "currency": "EUR",
                    "hl": "he",
                    "gl": "il",
                    "type": "1",  # Round trip
                    "stops": "1",  # Nonstop only
                    "sort_by": "2",  # Sort by price
                    "adults": adults,
                    "api_key": self.serpapi_key,
                }

                if max_price_eur:
                    params["max_price"] = max_price_eur

                try:
                    print(f"  ✈️  SerpAPI: {ORIGIN_AIRPORT}→{dest_info['code']} "
                          f"{search_date.strftime('%d/%m')} ({stay_nights}n)")

                    resp = requests.get(
                        "https://serpapi.com/search",
                        params=params, timeout=30,
                    )
                    api_calls += 1

                    if resp.status_code == 200:
                        data = resp.json()

                        # Check for API errors
                        if "error" in data:
                            print(f"  ⚠️  SerpAPI error: {data['error']}")
                            continue

                        # Parse best_flights and other_flights
                        for flight_group in data.get("best_flights", []):
                            parsed = self._parse_serpapi_flight(flight_group, stay_nights)
                            if parsed:
                                all_flights.append(parsed)

                        for flight_group in data.get("other_flights", []):
                            parsed = self._parse_serpapi_flight(flight_group, stay_nights)
                            if parsed:
                                all_flights.append(parsed)
                    elif resp.status_code == 429:
                        print(f"  ⚠️  SerpAPI rate limit — stopping")
                        break
                    else:
                        print(f"  ⚠️  SerpAPI {resp.status_code}: {resp.text[:200]}")

                except requests.Timeout:
                    print(f"  ⚠️  SerpAPI timeout for {search_date.strftime('%d/%m')}")
                except Exception as e:
                    print(f"  ⚠️  SerpAPI error: {e}")

            search_date += timedelta(days=4)

        # Sort by price and deduplicate
        all_flights.sort(key=lambda x: x.get("price_eur", 9999))

        seen = set()
        unique_flights = []
        for f in all_flights:
            key = (f["price_eur"], f["depart_date"], f["return_date"], f["airline"])
            if key not in seen:
                seen.add(key)
                unique_flights.append(f)

        final_flights = unique_flights[:limit]

        # ── Step 2: Fetch return flight details using departure_token ──
        # SerpAPI Google Flights requires a 2nd call to get return leg info.
        # CRITICAL: Only pass engine + departure_token + api_key. Extra params cause 400.
        for flight in final_flights:
            dep_token = flight.pop("_departure_token", None)
            if not dep_token:
                continue

            # Skip if we already have return times (from same-response parsing)
            if flight.get("return_depart_time") and flight["return_depart_time"] != "—":
                continue

            try:
                print(f"  🔄 Fetching return details for €{flight['price_eur']} {flight['depart_date']}...")

                # MINIMAL params only — departure_token encodes the full context
                ret_resp = requests.get(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google_flights",
                        "departure_token": dep_token,
                        "api_key": self.serpapi_key,
                    },
                    timeout=20,
                )
                api_calls += 1

                if ret_resp.status_code == 200:
                    ret_data = ret_resp.json()

                    if "error" in ret_data:
                        print(f"    ⚠️  Return API error: {ret_data['error'][:100]}")
                        continue

                    # The response contains return flight options
                    ret_options = ret_data.get("best_flights", []) + ret_data.get("other_flights", [])
                    if ret_options:
                        best_return = ret_options[0]
                        ret_flights = best_return.get("flights", [])
                        if ret_flights:
                            ret_seg = ret_flights[0]
                            ret_dep = ret_seg.get("departure_airport", {})
                            ret_arr = ret_seg.get("arrival_airport", {})
                            ret_duration = best_return.get("total_duration", 0)

                            flight["return_date"] = _format_serpapi_datetime(ret_dep.get("time", ""))
                            flight["return_depart_time"] = _format_serpapi_time(ret_dep.get("time", ""))
                            flight["return_arrive_time"] = _format_serpapi_time(ret_arr.get("time", ""))
                            flight["duration_return"] = _format_duration(ret_duration * 60) if ret_duration else "?"
                            print(f"    ✅ Return: {flight['return_date']} "
                                  f"({flight['return_depart_time']}→{flight['return_arrive_time']})")
                    else:
                        print(f"    ⚠️  No return flights in response")
                else:
                    print(f"    ⚠️  Return details HTTP {ret_resp.status_code}: {ret_resp.text[:150]}")

            except Exception as ret_err:
                print(f"    ⚠️  Return details error: {ret_err}")

        print(f"✅ SerpAPI (Google Flights): found {len(final_flights)} unique flights "
              f"(from {len(all_flights)} total, {api_calls} API calls)")

        return {
            "success": True,
            "flights": final_flights,
            "destination": dest_info,
            "total_results": len(unique_flights),
            "provider": "Google Flights",
        }

    def _parse_serpapi_flight(self, flight_group: Dict, nights: int) -> Optional[Dict]:
        """Parse a single SerpAPI Google Flights result into our standard format."""
        try:
            price = flight_group.get("price")
            if not price:
                return None

            flights = flight_group.get("flights", [])
            if not flights:
                return None

            # For nonstop, there's exactly 1 flight segment
            out_seg = flights[0]
            total_duration = flight_group.get("total_duration", 0)

            dep_airport = out_seg.get("departure_airport", {})
            arr_airport = out_seg.get("arrival_airport", {})

            dep_time_str = dep_airport.get("time", "")  # "2026-03-15 06:30"
            arr_time_str = arr_airport.get("time", "")

            # Extract airline name
            airline = out_seg.get("airline", "")
            flight_number = out_seg.get("flight_number", "")

            # Check if there's a return leg in the same flights array
            # (SerpAPI sometimes includes both legs for round-trip)
            ret_seg = None
            ret_duration = 0
            if len(flights) >= 2:
                # Second segment might be return leg
                possible_ret = flights[-1]
                ret_dep = possible_ret.get("departure_airport", {})
                # Verify it's actually a return (departs from destination)
                if ret_dep.get("id") == arr_airport.get("id"):
                    ret_seg = possible_ret
                    print(f"  ✅ Found return leg in same response: {ret_dep.get('time', '?')}")

            # Also check for "return_flights" key (some SerpAPI responses)
            if not ret_seg:
                return_flights = flight_group.get("return_flights", [])
                if return_flights:
                    ret_seg = return_flights[0]
                    print(f"  ✅ Found return_flights key")

            # Build dates
            dep_date_raw = dep_time_str[:10] if len(dep_time_str) >= 10 else ""
            ret_date_raw = ""
            ret_dep_time = ""
            ret_arr_time = ""

            if ret_seg:
                ret_dep_airport = ret_seg.get("departure_airport", {})
                ret_arr_airport = ret_seg.get("arrival_airport", {})
                ret_dep_time = ret_dep_airport.get("time", "")
                ret_arr_time = ret_arr_airport.get("time", "")
                ret_date_raw = ret_dep_time[:10] if len(ret_dep_time) >= 10 else ""
                ret_airline = ret_seg.get("airline", "")
                if ret_airline and ret_airline != airline:
                    airline = f"{airline} / {ret_airline}"
            
            # If no return info, calculate return date from departure + nights
            if not ret_date_raw and dep_date_raw:
                try:
                    dep_dt = datetime.strptime(dep_date_raw, "%Y-%m-%d")
                    ret_dt = dep_dt + timedelta(days=nights)
                    ret_date_raw = ret_dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass

            dest_code = arr_airport.get("id", "")
            google_flights_link = (
                f"https://www.google.com/travel/flights?"
                f"q=flights+{ORIGIN_AIRPORT}+to+{dest_code}+"
                f"on+{dep_date_raw}+return+{ret_date_raw}"
            ) if dep_date_raw and ret_date_raw else ""

            # Format return info
            has_ret_times = bool(ret_dep_time and ret_arr_time)

            return {
                "price_eur": int(price),
                "airline": airline,
                "deep_link": google_flights_link,
                # Outbound
                "depart_date": _format_serpapi_datetime(dep_time_str),
                "depart_time": _format_serpapi_time(dep_time_str),
                "arrive_time": _format_serpapi_time(arr_time_str),
                "depart_airport": dep_airport.get("id", ORIGIN_AIRPORT),
                "arrive_airport": dest_code,
                # Return
                "return_date": _format_serpapi_datetime(ret_dep_time) if has_ret_times else (
                    _format_serpapi_datetime(f"{ret_date_raw} 00:00") if ret_date_raw else "?"
                ),
                "return_depart_time": _format_serpapi_time(ret_dep_time) if has_ret_times else "—",
                "return_arrive_time": _format_serpapi_time(ret_arr_time) if has_ret_times else "—",
                # Duration
                "duration_outbound": _format_duration(total_duration * 60) if total_duration else "?",
                "duration_return": _format_duration(ret_duration * 60) if ret_duration else "—",
                "nights": nights,
                # Extra
                "flight_number": flight_number,
                # Internal token (cleaned before output)
                "_departure_token": flight_group.get("departure_token", ""),
            }
        except Exception as e:
            print(f"  ⚠️  SerpAPI parse error: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════
    # AMADEUS AUTH — OAuth2 token management
    # ═══════════════════════════════════════════════════════════════════
    def _get_amadeus_token(self) -> Optional[str]:
        """Get or refresh Amadeus OAuth2 access token."""
        if self._amadeus_token and time.time() < self._amadeus_token_expiry - 60:
            return self._amadeus_token

        try:
            resp = requests.post(
                "https://test.api.amadeus.com/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.amadeus_key,
                    "client_secret": self.amadeus_secret,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                print(f"❌ Amadeus auth failed: {resp.status_code} — {resp.text[:300]}")
                return None

            data = resp.json()
            self._amadeus_token = data["access_token"]
            self._amadeus_token_expiry = time.time() + data.get("expires_in", 1799)
            print(f"🔑 Amadeus token refreshed (expires in {data.get('expires_in', '?')}s)")
            return self._amadeus_token
        except Exception as e:
            print(f"❌ Amadeus auth error: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════
    # RESOLVE DESTINATION
    # ═══════════════════════════════════════════════════════════════════
    def _resolve_destination(self, destination_key: str) -> Optional[Dict]:
        """Resolve Hebrew destination name to airport info."""
        dest_key = destination_key.strip()
        for key, info in DESTINATION_MAP.items():
            if key == dest_key or key in dest_key or dest_key in key:
                return info
        return None

    # ═══════════════════════════════════════════════════════════════════
    # UNIFIED SEARCH — routes to active provider
    # ═══════════════════════════════════════════════════════════════════
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
        Uses HYBRID CASCADE: Amadeus → SerpAPI → Kiwi.
        Amadeus is preferred because it returns complete round-trip data
        (both legs with full timestamps) in a single API response.
        """
        # Lazy re-check: if not configured at init, try again (env vars may have been added)
        self._configure()
        if not self.is_configured:
            return {
                "success": False, "flights": [],
                "error": "שירות חיפוש טיסות לא מוגדר. הגדר AMADEUS_API_KEY+SECRET, SERPAPI_KEY, או KIWI_API_KEY."
            }

        # Resolve destination
        dest_info = self._resolve_destination(destination_key)
        if not dest_info:
            return {
                "success": False, "flights": [],
                "error": f"לא מכיר את היעד '{destination_key}'. יעדים זמינים: {', '.join(DESTINATION_MAP.keys())}",
            }

        # ── CASCADE: Try providers in order of data quality ──

        # 1. Amadeus (BEST: returns both legs with full times in one response)
        if self.amadeus_configured:
            print(f"  🔍 Trying Amadeus (primary — complete round-trip data)...")
            result = self._search_amadeus(dest_info, max_price_eur, date_from, date_to,
                                          nights_from, nights_to, adults, limit)
            if result.get("success") and result.get("flights"):
                print(f"  ✅ Amadeus returned {len(result['flights'])} flights with full return details")
                return result
            print(f"  ℹ️  Amadeus returned no results, cascading to next provider...")

        # 2. SerpAPI / Google Flights (GOOD: broad coverage, but return times need 2nd call)
        if self.serpapi_configured:
            print(f"  🔍 Trying SerpAPI/Google Flights (fallback — includes low-cost)...")
            result = self._search_serpapi(dest_info, max_price_eur, date_from, date_to,
                                          nights_from, nights_to, adults, limit)
            if result.get("success") and result.get("flights"):
                return result
            print(f"  ℹ️  SerpAPI returned no results, cascading to next provider...")

        # 3. Kiwi (FALLBACK: when available)
        if self.kiwi_configured:
            print(f"  🔍 Trying Kiwi (last fallback)...")
            return self._search_kiwi(dest_info, max_price_eur, date_from, date_to,
                                     return_from, return_to, nights_from, nights_to, adults, limit)

        return {"success": False, "flights": [], "error": "No flight providers returned results."}

    # ═══════════════════════════════════════════════════════════════════
    # AMADEUS SEARCH
    # ═══════════════════════════════════════════════════════════════════
    def _search_amadeus(
        self, dest_info, max_price_eur, date_from, date_to,
        nights_from, nights_to, adults, limit
    ) -> Dict[str, Any]:
        """Search flights via Amadeus Flight Offers Search API."""
        token = self._get_amadeus_token()
        if not token:
            return {"success": False, "flights": [], "error": "Amadeus authentication failed"}

        today = datetime.now()
        # Amadeus needs specific departure dates, so we search multiple dates
        # and collect the cheapest results
        if date_from:
            try:
                start_date = datetime.strptime(date_from, "%d/%m/%Y")
            except ValueError:
                start_date = today + timedelta(days=1)
        else:
            start_date = today + timedelta(days=1)

        if date_to:
            try:
                end_date = datetime.strptime(date_to, "%d/%m/%Y")
            except ValueError:
                end_date = today + timedelta(days=60)
        else:
            end_date = today + timedelta(days=60)

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        all_flights = []

        # Search every 3rd day in the range to cover options efficiently
        search_date = start_date
        api_calls = 0
        max_api_calls = 10  # Limit API calls per search

        while search_date <= end_date and api_calls < max_api_calls:
            for stay_nights in range(nights_from, min(nights_to + 1, nights_from + 3)):
                return_date = search_date + timedelta(days=stay_nights)

                params = {
                    "originLocationCode": ORIGIN_AIRPORT,
                    "destinationLocationCode": dest_info["code"],
                    "departureDate": search_date.strftime("%Y-%m-%d"),
                    "returnDate": return_date.strftime("%Y-%m-%d"),
                    "adults": adults,
                    "nonStop": "true",  # DIRECT FLIGHTS ONLY
                    "currencyCode": "EUR",
                    "max": 3,
                }

                if max_price_eur:
                    params["maxPrice"] = max_price_eur

                try:
                    print(f"  ✈️  Amadeus: {ORIGIN_AIRPORT}→{dest_info['code']} "
                          f"{search_date.strftime('%d/%m')} ({stay_nights}n)")

                    resp = requests.get(
                        "https://test.api.amadeus.com/v2/shopping/flight-offers",
                        params=params, headers=headers, timeout=20,
                    )
                    api_calls += 1

                    if resp.status_code == 200:
                        data = resp.json()
                        offers = data.get("data", [])
                        dictionaries = data.get("dictionaries", {})
                        carriers = dictionaries.get("carriers", {})

                        for offer in offers:
                            parsed = self._parse_amadeus_offer(offer, carriers, stay_nights)
                            if parsed:
                                all_flights.append(parsed)
                    elif resp.status_code == 429:
                        print(f"  ⚠️  Amadeus rate limit — pausing")
                        time.sleep(1)
                    else:
                        print(f"  ⚠️  Amadeus {resp.status_code}: {resp.text[:200]}")

                except requests.Timeout:
                    print(f"  ⚠️  Amadeus timeout for {search_date.strftime('%d/%m')}")
                except Exception as e:
                    print(f"  ⚠️  Amadeus error: {e}")

            search_date += timedelta(days=3)

        # Sort by price and deduplicate
        all_flights.sort(key=lambda x: x.get("price_eur", 9999))

        # Remove near-duplicates (same price + same dates)
        seen = set()
        unique_flights = []
        for f in all_flights:
            key = (f["price_eur"], f["depart_date"], f["return_date"], f["airline"])
            if key not in seen:
                seen.add(key)
                unique_flights.append(f)

        final_flights = unique_flights[:limit]

        print(f"✅ Amadeus: found {len(final_flights)} unique flights "
              f"(from {len(all_flights)} total, {api_calls} API calls)")

        return {
            "success": True,
            "flights": final_flights,
            "destination": dest_info,
            "total_results": len(unique_flights),
            "provider": "Amadeus",
        }

    def _parse_amadeus_offer(self, offer: Dict, carriers: Dict, nights: int) -> Optional[Dict]:
        """Parse a single Amadeus flight offer into our standard format."""
        try:
            price = float(offer.get("price", {}).get("grandTotal", 0))
            itineraries = offer.get("itineraries", [])

            print(f"  📋 Amadeus offer: €{price}, {len(itineraries)} itineraries")

            if len(itineraries) < 2:
                print(f"  ⚠️  Skipping: only {len(itineraries)} itinerary (need 2 for round-trip)")
                return None

            # Outbound
            out_segments = itineraries[0].get("segments", [])
            ret_segments = itineraries[1].get("segments", [])

            print(f"  📋 Outbound segments: {len(out_segments)}, Return segments: {len(ret_segments)}")

            if not out_segments or not ret_segments:
                print(f"  ⚠️  Skipping: empty segments")
                return None

            out_seg = out_segments[0]  # Direct flight = 1 segment
            ret_seg = ret_segments[0]

            # Debug: print raw segment data
            out_dep_at = out_seg.get("departure", {}).get("at", "")
            out_arr_at = out_seg.get("arrival", {}).get("at", "")
            ret_dep_at = ret_seg.get("departure", {}).get("at", "")
            ret_arr_at = ret_seg.get("arrival", {}).get("at", "")
            
            print(f"  🛫 OUT: dep={out_dep_at} arr={out_arr_at}")
            print(f"  🛬 RET: dep={ret_dep_at} arr={ret_arr_at}")
            print(f"  ⏱  OUT dur={itineraries[0].get('duration', '?')} RET dur={itineraries[1].get('duration', '?')}")

            # Resolve airline name
            carrier_code = out_seg.get("carrierCode", "")
            ret_carrier_code = ret_seg.get("carrierCode", "")
            airline_name = carriers.get(carrier_code, AIRLINE_NAMES.get(carrier_code, carrier_code))
            ret_airline_name = carriers.get(ret_carrier_code, AIRLINE_NAMES.get(ret_carrier_code, ret_carrier_code))
            
            # Show both airlines if different
            if ret_airline_name and ret_airline_name != airline_name:
                combined_airline = f"{airline_name} / {ret_airline_name}"
            else:
                combined_airline = airline_name

            # Build Google Flights link
            out_date = out_dep_at[:10] if len(out_dep_at) >= 10 else ""
            ret_date = ret_dep_at[:10] if len(ret_dep_at) >= 10 else ""
            dest_code = out_seg.get("arrival", {}).get("iataCode", "")
            google_flights_link = (
                f"https://www.google.com/travel/flights?"
                f"q=flights+{ORIGIN_AIRPORT}+to+{dest_code}+"
                f"on+{out_date}+return+{ret_date}"
            )

            return {
                "price_eur": int(price),
                "airline": combined_airline,
                "deep_link": google_flights_link,
                # Outbound
                "depart_date": _format_datetime(out_dep_at),
                "depart_time": _format_time(out_dep_at),
                "arrive_time": _format_time(out_arr_at),
                "depart_airport": out_seg.get("departure", {}).get("iataCode", ""),
                "arrive_airport": dest_code,
                # Return
                "return_date": _format_datetime(ret_dep_at),
                "return_depart_time": _format_time(ret_dep_at),
                "return_arrive_time": _format_time(ret_arr_at),
                # Duration
                "duration_outbound": _parse_iso_duration(itineraries[0].get("duration", "")),
                "duration_return": _parse_iso_duration(itineraries[1].get("duration", "")),
                "nights": nights,
            }
        except Exception as e:
            print(f"  ⚠️  Parse error: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════
    # KIWI SEARCH (fallback)
    # ═══════════════════════════════════════════════════════════════════
    def _search_kiwi(
        self, dest_info, max_price_eur, date_from, date_to,
        return_from, return_to, nights_from, nights_to, adults, limit
    ) -> Dict[str, Any]:
        """Search flights via Kiwi.com Tequila API."""
        today = datetime.now()
        if not date_from:
            date_from = (today + timedelta(days=1)).strftime("%d/%m/%Y")
        if not date_to:
            date_to = (today + timedelta(days=60)).strftime("%d/%m/%Y")

        params = {
            "fly_from": ORIGIN_AIRPORT,
            "fly_to": dest_info["code"],
            "date_from": date_from,
            "date_to": date_to,
            "flight_type": "round",
            "nights_in_dst_from": nights_from,
            "nights_in_dst_to": nights_to,
            "max_stopovers": 0,
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

        headers = {"apikey": self.kiwi_key, "Content-Type": "application/json"}

        try:
            print(f"✈️  Kiwi: {ORIGIN_AIRPORT} → {dest_info['code']} "
                  f"(max €{max_price_eur or 'unlimited'}, {date_from}–{date_to})")

            resp = requests.get(
                "https://api.tequila.kiwi.com/v2/search",
                params=params, headers=headers, timeout=30,
            )
            if resp.status_code != 200:
                print(f"❌ Kiwi API error {resp.status_code}: {resp.text[:500]}")
                return {"success": False, "flights": [], "error": f"Kiwi API error: {resp.status_code}"}

            data = resp.json()
            flights = data.get("data", [])
            print(f"✅ Kiwi: found {len(flights)} flights")

            parsed_flights = []
            for f in flights:
                outbound_legs = [r for r in f.get("route", []) if r.get("return") == 0]
                return_legs = [r for r in f.get("route", []) if r.get("return") == 1]
                out = outbound_legs[0] if outbound_legs else {}
                ret = return_legs[0] if return_legs else {}

                parsed_flights.append({
                    "price_eur": f.get("price"),
                    "airline": ", ".join(f.get("airlines", [])),
                    "deep_link": f.get("deep_link", ""),
                    "depart_date": _format_datetime(out.get("local_departure", "")),
                    "depart_time": _format_time(out.get("local_departure", "")),
                    "arrive_time": _format_time(out.get("local_arrival", "")),
                    "depart_airport": out.get("flyFrom", ""),
                    "arrive_airport": out.get("flyTo", ""),
                    "return_date": _format_datetime(ret.get("local_departure", "")),
                    "return_depart_time": _format_time(ret.get("local_departure", "")),
                    "return_arrive_time": _format_time(ret.get("local_arrival", "")),
                    "duration_outbound": _format_duration(f.get("duration", {}).get("departure", 0)),
                    "duration_return": _format_duration(f.get("duration", {}).get("return", 0)),
                    "nights": f.get("nightsInDest", "?"),
                })

            return {
                "success": True,
                "flights": parsed_flights,
                "destination": dest_info,
                "total_results": data.get("_results", len(parsed_flights)),
                "provider": "Kiwi",
            }
        except requests.Timeout:
            return {"success": False, "flights": [], "error": "Timeout — try again"}
        except Exception as e:
            logger.error(f"Kiwi search error: {e}")
            print(f"❌ Kiwi search error: {e}")
            return {"success": False, "flights": [], "error": str(e)}

    # ═══════════════════════════════════════════════════════════════════
    # FORMAT RESULTS
    # ═══════════════════════════════════════════════════════════════════
    def format_results(self, results: Dict[str, Any], query_text: str = "") -> str:
        """Format flight search results for WhatsApp."""
        if not results.get("success"):
            return f"❌ שגיאה בחיפוש טיסות: {results.get('error', 'Unknown error')}"

        flights = results.get("flights", [])
        dest = results.get("destination", {})
        dest_name = dest.get("name", "?")
        provider = results.get("provider", "")

        if not flights:
            return f"✈️ לא נמצאו טיסות ישירות ל{dest_name} בטווח המחיר המבוקש."

        lines = [f"✈️ *טיסות ישירות ל{dest_name}*"]
        if query_text:
            lines.append(f"🔍 _{query_text}_")
        lines.append(f"📊 נמצאו {results.get('total_results', len(flights))} תוצאות")
        if provider:
            lines.append(f"_מקור: {provider}_\n")
        else:
            lines.append("")

        for i, f in enumerate(flights, 1):
            lines.append(f"{'─' * 30}")
            lines.append(f"*{i}. €{f['price_eur']}* לאדם (הלוך-חזור)")
            lines.append(f"🛫 חברת תעופה: *{f['airline']}*")
            
            # Flight number (if available)
            if f.get("flight_number"):
                lines.append(f"✈️ טיסה: {f['flight_number']}")
            
            # Outbound flight
            lines.append(
                f"📅 הלוך: {f['depart_date']} "
                f"({f['depart_time']}→{f['arrive_time']}) "
                f"⏱ {f['duration_outbound']}"
            )
            
            # Return flight — show times only if available
            has_return_times = (
                f.get('return_depart_time') and f['return_depart_time'] != '—'
                and f.get('return_arrive_time') and f['return_arrive_time'] != '—'
            )
            has_return_duration = f.get('duration_return') and f['duration_return'] != '—'
            
            if has_return_times:
                return_line = f"📅 חזור: {f['return_date']} ({f['return_depart_time']}→{f['return_arrive_time']})"
                if has_return_duration:
                    return_line += f" ⏱ {f['duration_return']}"
                lines.append(return_line)
            else:
                lines.append(f"📅 חזור: {f['return_date']}")
            
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

def _format_serpapi_datetime(time_str: str) -> str:
    """'2026-03-15 06:30' → '15/03 (ראשון)'"""
    if not time_str or len(time_str) < 10:
        return "?"
    try:
        dt = datetime.strptime(time_str[:16], "%Y-%m-%d %H:%M")
        day_names = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
        day_name = day_names[dt.weekday()]
        return f"{dt.strftime('%d/%m')} ({day_name})"
    except Exception:
        return time_str[:10]


def _format_serpapi_time(time_str: str) -> str:
    """'2026-03-15 06:30' → '06:30'"""
    if not time_str or len(time_str) < 16:
        return "?"
    try:
        return time_str[11:16]
    except Exception:
        return "?"


def _format_datetime(iso_str: str) -> str:
    """'2026-03-15T06:30:00.000Z' → '15/03 (ראשון)'"""
    if not iso_str:
        return "?"
    try:
        clean = iso_str.replace("Z", "+00:00") if "T" in iso_str else iso_str
        dt = datetime.fromisoformat(clean)
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
        clean = iso_str.replace("Z", "+00:00") if "T" in iso_str else iso_str
        dt = datetime.fromisoformat(clean)
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


def _parse_iso_duration(iso_dur: str) -> str:
    """ISO 8601 duration 'PT2H30M' → '2h 30m'"""
    if not iso_dur:
        return "?"
    try:
        dur = iso_dur.replace("PT", "")
        hours = 0
        minutes = 0
        if "H" in dur:
            h_part, dur = dur.split("H")
            hours = int(h_part)
        if "M" in dur:
            m_part = dur.replace("M", "")
            minutes = int(m_part) if m_part else 0
        if hours and minutes:
            return f"{hours}h {minutes}m"
        elif hours:
            return f"{hours}h"
        else:
            return f"{minutes}m"
    except Exception:
        return iso_dur


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════
flight_search_service = FlightSearchService()
