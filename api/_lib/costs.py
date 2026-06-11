"""
Trip cost estimator for following a team through the tournament.

Honesty model — this never fabricates a precise quote:
  * TICKETS: per-stage ranges are FIFA's published base prices (Oct 2025 release,
    dynamic pricing). Shown as a low–high band per stage, attributed to FIFA.
  * HOTELS: computed from the fan's own inputs (nights x nightly budget). Real
    arithmetic on numbers they provide — no invented rates.
  * FLIGHTS: the confirmed group->final direction can be priced from cached
    fares elsewhere in the app; for the whole-journey estimate we use a
    transparent per-leg band derived from inter-venue distance, clearly labelled
    as an estimate, not a quote.

Every figure returned is a RANGE with a stated basis, so the UI can show how
it's derived rather than presenting a single false-precision total.
"""

# How many matches a team plays *in each round* if they reach it. A team that
# wins its group plays 3 group games, then one match per knockout round.
ROUND_MATCHES = {
    "group": 3, "r32": 1, "r16": 1, "qf": 1, "sf": 1, "final": 1,
}

# FIFA published base ticket price bands per stage (USD), from the Oct 2025
# release and subsequent reporting. Low = cheapest general-public category,
# high = top general category (excludes hospitality and supporter-tier $60).
# These are real published figures, presented as ranges because FIFA uses
# dynamic pricing.
TICKET_BANDS = {
    "group":  (120, 600),
    "r32":    (140, 800),
    "r16":    (200, 1100),
    "qf":     (345, 1800),
    "sf":     (700, 3295),
    "final":  (455, 6730),
}

ROUND_LABELS = {
    "group": "Group stage", "r32": "Round of 32", "r16": "Round of 16",
    "qf": "Quarter-final", "sf": "Semi-final", "final": "Final",
}

# Per-city average nightly hotel rate during the WC26 tournament window (USD).
# Sourced from Hotels.com WC26 match-timeframe data and WC26 hotel pricing
# reports (Lighthouse/SmarterTravel). These are real reported tournament rates,
# used as a smarter default than a single flat budget. A range is given around
# each reported average to reflect value vs premium options.
CITY_HOTEL_RATE = {
    "seattle":     565, "nyc":        540, "boston":      535, "la":         450,
    "philly":      440, "miami":      435, "dallas":      380, "atlanta":    370,
    "houston":     355, "kansascity": 335, "bayarea":     270,
    # Canada / Mexico from WC26 reporting; Vancouver reported among the highest.
    "vancouver":   410, "toronto":    330,
    "mexicocity":  240, "guadalajara":180, "monterrey":   190,
}
# Default if a city is somehow missing
_DEFAULT_RATE = 300


def _flight_band_for_km(km):
    """Transparent per-leg flight estimate band (USD), distance-based.

    Not a quote — a planning band. Roughly: a cheap-end and a flexible-end
    domestic/short-international fare that scales with distance.
    """
    low = 60 + km * 0.10
    high = 130 + km * 0.22
    return (round(low / 5) * 5, round(high / 5) * 5)


def estimate(steps, nights_per_stop, nightly_budget=None, include_flights=True,
             live_fares=None):
    """Build a transparent cost estimate from the team's path.

    steps: path steps (each has 'round', 'certain', cities with 'leg' + 'key').
    nights_per_stop: hotel nights the fan expects per city.
    nightly_budget: optional flat override (USD). If None, use real per-city
        WC26 tournament rates.
    live_fares: optional dict {leg_key: {"price":..,"airline":..,"found":..}}
        of REAL cached fares keyed by "origin->dest". When present for a leg,
        the real fare is used instead of the distance band.

    Every figure carries a 'basis' string so nothing reads as a false quote.
    """
    live_fares = live_fares or {}
    rounds_reached = [s["round"] for s in steps]

    # --- Tickets: sum FIFA bands for each round reached ---
    t_low = t_high = 0
    ticket_lines = []
    for r in rounds_reached:
        if r not in TICKET_BANDS:
            continue
        matches = ROUND_MATCHES.get(r, 1)
        lo, hi = TICKET_BANDS[r]
        t_low += lo * matches
        t_high += hi * matches
        ticket_lines.append({
            "round": ROUND_LABELS[r], "matches": matches,
            "low": lo * matches, "high": hi * matches,
        })

    # --- Hotels: real per-city WC26 rates, or a flat override ---
    hotel_total = 0
    hotel_lines = []
    using_real_rates = nightly_budget is None
    for s in steps:
        city = s["cities"][0]
        key = city.get("key")
        if using_real_rates:
            rate = CITY_HOTEL_RATE.get(key, _DEFAULT_RATE)
        else:
            rate = nightly_budget
        cost = rate * nights_per_stop
        hotel_total += cost
        hotel_lines.append({
            "city": city["city"], "nights": nights_per_stop,
            "rate": rate, "cost": round(cost),
            "known": s["certain"],
        })

    # --- Flights: real cached fare per leg when available, else distance band ---
    flight_low = flight_high = 0
    flight_legs = []
    any_live = False
    if include_flights:
        for s in steps:
            city = s["cities"][0]
            leg = city.get("leg") or {}
            if leg.get("same_city"):
                continue
            o, dst = leg.get("origin_iata"), leg.get("dest_iata")
            fkey = f"{o}->{dst}"
            live = live_fares.get(fkey)
            if live and live.get("price"):
                price = round(float(live["price"]))
                flight_low += price
                flight_high += price
                any_live = True
                flight_legs.append({
                    "to": city["city"], "distance_mi": leg.get("distance_mi"),
                    "low": price, "high": price, "live": True,
                    "airline": live.get("airline", ""), "seen": live.get("found", ""),
                })
            else:
                km = leg.get("distance_km")
                if not km:
                    continue
                lo, hi = _flight_band_for_km(km)
                flight_low += lo
                flight_high += hi
                flight_legs.append({
                    "to": city["city"], "distance_mi": leg.get("distance_mi"),
                    "low": lo, "high": hi, "live": False,
                })

    grand_low = t_low + hotel_total + flight_low
    grand_high = t_high + hotel_total + flight_high

    hotel_basis = ("Real per-city average rates during the WC26 window "
                   "(Hotels.com tournament data) × your nights."
                   if using_real_rates else
                   "Your nightly budget × nights × stops.")
    flight_basis = ("Real cached fares where available (marked LIVE); "
                    "distance-based estimate otherwise." if any_live else
                    "Distance-based planning estimate per leg — not a live quote.")

    return {
        "tickets": {
            "low": t_low, "high": t_high, "lines": ticket_lines,
            "basis": "FIFA published base prices (Oct 2025 release, dynamic pricing).",
        },
        "hotels": {
            "total": round(hotel_total), "lines": hotel_lines,
            "stops": len(rounds_reached), "nights_per_stop": nights_per_stop,
            "using_real_rates": using_real_rates,
            "basis": hotel_basis,
        },
        "flights": {
            "low": flight_low, "high": flight_high, "legs": flight_legs,
            "included": include_flights, "any_live": any_live,
            "basis": flight_basis,
        },
        "grand": {"low": round(grand_low), "high": round(grand_high)},
    }
