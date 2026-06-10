"""
Match tickets — link-out, not fabricated prices.

WC26 primary tickets sell through FIFA's official platform, and there's no clean
open live-price feed for resale. Per the product decision, we do NOT invent
ticket prices. Instead we build real search deep-links to official + resale
marketplaces for the specific city/round, so a fan lands on live listings.

If a SEATGEEK_CLIENT_ID is provided, we additionally return real SeatGeek event
matches via their public API (event links + listing counts), still without
fabricating a price when none is exposed.
"""
import os
import json
import urllib.parse
import urllib.request


def _links_for(city_label, round_label):
    q = urllib.parse.quote_plus(f"FIFA World Cup 2026 {city_label} {round_label}")
    return [
        {"site": "FIFA Official", "url": "https://www.fifa.com/en/tickets"},
        {"site": "SeatGeek", "url": f"https://seatgeek.com/search?q={q}"},
        {"site": "StubHub", "url": f"https://www.stubhub.com/find/s/?q={q}"},
    ]


def _seatgeek_events(city_label, round_label):
    cid = os.environ.get("SEATGEEK_CLIENT_ID")
    if not cid:
        return None
    q = f"World Cup {city_label}"
    params = {"client_id": cid, "q": q, "per_page": 5}
    url = "https://api.seatgeek.com/2/events?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            res = json.loads(r.read().decode())
        events = []
        for e in res.get("events", []):
            stats = e.get("stats", {})
            events.append({
                "title": e.get("title", ""),
                "url": e.get("url", ""),
                "datetime": e.get("datetime_local", ""),
                # lowest_price may be null — pass through as-is, never invent it
                "lowest_price": stats.get("lowest_price"),
                "listing_count": stats.get("listing_count"),
            })
        return events
    except Exception:
        return None


def tickets_for(city_label, round_label):
    out = {"links": _links_for(city_label, round_label), "events": None}
    ev = _seatgeek_events(city_label, round_label)
    if ev is not None:
        out["events"] = ev
        out["events_provider"] = "seatgeek"
    return out
