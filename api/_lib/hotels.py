"""
Cheapest hotels — real data via Amadeus Hotel Search (free self-serve tier).

Reuses the same Amadeus credentials as flights. Two-step API: resolve hotels by
city geocode, then fetch live offers. Never fabricates a rate.
"""
import os
import urllib.parse

from . import flights as _amadeus  # reuse token + _http helpers


def _hotels_by_geocode(token, lat, lon, radius_km=15):
    params = {"latitude": lat, "longitude": lon, "radius": radius_km, "radiusUnit": "KM"}
    url = f"{_amadeus.AMADEUS_BASE}/v1/reference-data/locations/hotels/by-geocode?" + urllib.parse.urlencode(params)
    res = _amadeus._http("GET", url, headers={"Authorization": f"Bearer {token}"})
    return [h["hotelId"] for h in res.get("data", [])][:20]


def search_hotels(lat, lon, check_in, check_out, adults=1):
    """Cheapest real hotel offers near a venue, or honest unconfigured/empty.

    check_in / check_out: 'YYYY-MM-DD'
    """
    if not os.environ.get("AMADEUS_CLIENT_ID"):
        return {"configured": False, "provider": "amadeus",
                "message": "Add AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET to enable live hotel prices."}
    try:
        token = _amadeus._get_token()
        hotel_ids = _hotels_by_geocode(token, lat, lon)
        if not hotel_ids:
            return {"configured": True, "provider": "amadeus", "offers": [],
                    "message": "No hotels found near this venue."}
        params = {
            "hotelIds": ",".join(hotel_ids),
            "checkInDate": check_in, "checkOutDate": check_out,
            "adults": adults, "currency": "USD", "bestRateOnly": "true",
        }
        url = f"{_amadeus.AMADEUS_BASE}/v3/shopping/hotel-offers?" + urllib.parse.urlencode(params)
        res = _amadeus._http("GET", url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        norm = []
        for item in res.get("data", []):
            hotel = item.get("hotel", {})
            offers = item.get("offers", [])
            if not offers:
                continue
            price = offers[0].get("price", {})
            norm.append({
                "name": hotel.get("name", "Hotel"),
                "price": float(price.get("total", 0)),
                "currency": price.get("currency", "USD"),
            })
        norm.sort(key=lambda x: x["price"])
        if not norm:
            return {"configured": True, "provider": "amadeus", "offers": [],
                    "message": "No available rates for those dates."}
        return {"configured": True, "provider": "amadeus", "offers": norm[:6],
                "cheapest": norm[0]}
    except Exception as e:
        return {"configured": True, "provider": "amadeus", "error": str(e),
                "message": "Live hotel lookup failed; no estimate shown rather than a fabricated one."}
