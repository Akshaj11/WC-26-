"""
Flight prices — real data via Amadeus Self-Service API.

Why Amadeus: it has a genuine free self-serve tier (test + production keys you
sign up for at developers.amadeus.com), unlike Skyscanner/Google Flights which
are partner-only or have no public API. Swappable: the function returns a
normalized shape, so a Duffel/Kiwi provider could drop in behind the same
interface.

CONTRACT: never fabricate prices. If the key is missing, return
{"configured": False, ...}. If the API errors or has no offers, say so
explicitly. Every price on screen is a real Amadeus offer or nothing.
"""
import os
import json
import time
import urllib.parse
import urllib.request

AMADEUS_BASE = os.environ.get("AMADEUS_BASE", "https://test.api.amadeus.com")
_token_cache = {"token": None, "exp": 0}


def _http(method, url, *, headers=None, data=None, timeout=10):
    req = urllib.request.Request(url, method=method, headers=headers or {})
    if data is not None:
        if isinstance(data, dict):
            data = urllib.parse.urlencode(data).encode()
        req.data = data
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _get_token():
    """OAuth2 client-credentials token, cached until ~30s before expiry."""
    cid = os.environ.get("AMADEUS_CLIENT_ID")
    secret = os.environ.get("AMADEUS_CLIENT_SECRET")
    if not cid or not secret:
        return None
    now = time.time()
    if _token_cache["token"] and now < _token_cache["exp"] - 30:
        return _token_cache["token"]
    body = {"grant_type": "client_credentials", "client_id": cid, "client_secret": secret}
    res = _http("POST", f"{AMADEUS_BASE}/v1/security/oauth2/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"}, data=body)
    _token_cache["token"] = res["access_token"]
    _token_cache["exp"] = now + int(res.get("expires_in", 1799))
    return _token_cache["token"]


def search_flights(origin_iata, dest_iata, depart_date, adults=1):
    """Return cheapest real offers, or an honest unconfigured/empty result.

    depart_date: 'YYYY-MM-DD'
    """
    if not os.environ.get("AMADEUS_CLIENT_ID"):
        return {"configured": False, "provider": "amadeus",
                "message": "Add AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET to enable live flight prices."}
    try:
        token = _get_token()
        params = {
            "originLocationCode": origin_iata,
            "destinationLocationCode": dest_iata,
            "departureDate": depart_date,
            "adults": adults,
            "currencyCode": "USD",
            "max": 5,
        }
        url = f"{AMADEUS_BASE}/v2/shopping/flight-offers?" + urllib.parse.urlencode(params)
        res = _http("GET", url, headers={"Authorization": f"Bearer {token}"})
        offers = res.get("data", [])
        if not offers:
            return {"configured": True, "provider": "amadeus", "offers": [],
                    "message": "No flight offers found for that route and date."}
        norm = []
        for o in offers[:5]:
            price = o.get("price", {})
            itin = o.get("itineraries", [{}])[0]
            segs = itin.get("segments", [])
            norm.append({
                "price": float(price.get("grandTotal", price.get("total", 0))),
                "currency": price.get("currency", "USD"),
                "duration": itin.get("duration", ""),
                "stops": max(0, len(segs) - 1),
                "carrier": segs[0].get("carrierCode", "") if segs else "",
            })
        norm.sort(key=lambda x: x["price"])
        return {"configured": True, "provider": "amadeus", "offers": norm,
                "cheapest": norm[0] if norm else None}
    except Exception as e:
        return {"configured": True, "provider": "amadeus", "error": str(e),
                "message": "Live flight lookup failed; no estimate shown rather than a fabricated one."}
