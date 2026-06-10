"""
Flight prices — Travelpayouts / Aviasales cached Data API + a live-search link.

Why this provider: genuinely free (no card, no per-call billing), and unlike
Amadeus it is not being deprecated. The data API only needs a token from your
Travelpayouts profile; no minimum-traffic gate (that applies only to the
real-time search API, which we deliberately don't use).

Honesty model:
  * Prices are CACHED from recent user searches, each carrying a timestamp
    (`found_at`, when the fare was last seen; some endpoints use `expires_at`).
  * We compute each fare's AGE from that real timestamp and label it
    "seen N days ago" so the fan knows how stale it is — never invented.
  * Every result is paired with a link to LIVE search (Google Flights /
    Skyscanner) to confirm the current fare.
  * No token -> configured: False. No data -> honest empty message.

Informational only — no affiliate markers are added.
"""
import os
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone


TP_BASE = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


def _http_get(url, headers, timeout=10):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _parse_iso(ts):
    """Parse an ISO-8601 timestamp (handles trailing 'Z'). None on failure."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _freshness(found_at, expires_at):
    """Return a human label + numeric age from a real cache timestamp.

    Prefers `found_at` (when the fare was last seen). Falls back to estimating
    from `expires_at` (caches typically live ~7 days, so seen ≈ expires - 7d).
    Returns {"label": str, "days": int|None, "seen_at": iso|None} or None.
    """
    seen = _parse_iso(found_at)
    source = found_at
    if seen is None:
        exp = _parse_iso(expires_at)
        if exp is not None:
            # rough: assume a ~7-day cache window
            from datetime import timedelta
            seen = exp - timedelta(days=7)
            source = seen.isoformat()
    if seen is None:
        return None
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - seen
    days = delta.days
    hours = int(delta.total_seconds() // 3600)
    if days <= 0:
        label = "seen today" if hours < 24 else "seen <1 day ago"
        if hours <= 1:
            label = "seen just now"
    elif days == 1:
        label = "seen 1 day ago"
    else:
        label = f"seen {days} days ago"
    return {"label": label, "days": max(days, 0), "seen_at": source}


def live_search_links(origin_iata, dest_iata, depart_date):
    """Deep-links to live flight search so the fan can verify the current fare."""
    g = (f"https://www.google.com/travel/flights"
         f"?q=Flights%20from%20{origin_iata}%20to%20{dest_iata}%20on%20{depart_date}")
    s = (f"https://www.skyscanner.com/transport/flights/"
         f"{origin_iata.lower()}/{dest_iata.lower()}/{depart_date.replace('-', '')[2:]}/")
    return [
        {"site": "Google Flights", "url": g},
        {"site": "Skyscanner", "url": s},
    ]


def search_flights(origin_iata, dest_iata, depart_date, adults=1):
    """Cheapest cached fares for the route/date + live-search links.

    depart_date: 'YYYY-MM-DD' (or 'YYYY-MM' for a whole month).
    """
    links = live_search_links(origin_iata, dest_iata, depart_date)
    token = os.environ.get("TRAVELPAYOUTS_TOKEN")
    if not token:
        return {"configured": False, "provider": "travelpayouts",
                "live_links": links,
                "message": "Add TRAVELPAYOUTS_TOKEN for cached price estimates. "
                           "Live-search links work without it."}
    try:
        params = {
            "origin": origin_iata,
            "destination": dest_iata,
            "departure_at": depart_date,
            "currency": "usd",
            "sorting": "price",
            "limit": 5,
            "one_way": "true",
            # Cache is partitioned by "market"; for US/CA/MX routes we want the
            # US market. Override with TRAVELPAYOUTS_MARKET if needed.
            "market": os.environ.get("TRAVELPAYOUTS_MARKET", "us"),
            "token": token,
        }
        url = TP_BASE + "?" + urllib.parse.urlencode(params)
        res = _http_get(url, {"X-Access-Token": token})
        if not res.get("success", False):
            return {"configured": True, "provider": "travelpayouts",
                    "live_links": links, "offers": [],
                    "message": "No cached prices for that route/date. Try the live search."}
        offers = []
        for o in res.get("data", []) or []:
            fresh = _freshness(o.get("found_at"), o.get("expires_at"))
            offers.append({
                "price": o.get("price"),
                "currency": "USD",
                "airline": o.get("airline", ""),
                "departure_at": (o.get("departure_at", "") or "")[:10],
                "transfers": o.get("transfers", 0),
                "link": ("https://www.aviasales.com" + o["link"]) if o.get("link") else None,
                "cached": True,
                "freshness": fresh,           # {"label","days","seen_at"} or None
            })
        offers = [o for o in offers if o["price"] is not None]
        offers.sort(key=lambda x: x["price"])
        if not offers:
            return {"configured": True, "provider": "travelpayouts",
                    "live_links": links, "offers": [],
                    "message": "No cached prices right now. Use the live search."}
        return {"configured": True, "provider": "travelpayouts",
                "live_links": links, "offers": offers,
                "cheapest": offers[0],
                "note": "Cached estimates from recent searches — confirm via live search."}
    except Exception as e:
        return {"configured": True, "provider": "travelpayouts", "live_links": links,
                "error": str(e),
                "message": "Cached price lookup failed; use the live-search links instead."}
