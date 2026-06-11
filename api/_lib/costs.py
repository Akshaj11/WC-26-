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


def _flight_band_for_km(km):
    """Transparent per-leg flight estimate band (USD), distance-based.

    Not a quote — a planning band. Roughly: a cheap-end and a flexible-end
    domestic/short-international fare that scales with distance.
    """
    low = 60 + km * 0.10
    high = 130 + km * 0.22
    return (round(low / 5) * 5, round(high / 5) * 5)


def estimate(steps, nights_per_stop, nightly_budget, include_flights=True):
    """Build a transparent cost estimate from the team's path.

    steps: the path steps (each has 'round', 'certain', and cities with 'leg').
    nights_per_stop: int, hotel nights the fan expects per city.
    nightly_budget: float, fan's own nightly hotel budget (USD).

    Returns a dict with per-category breakdowns, each carrying low/high and a
    'basis' string the UI shows so nothing looks like a fabricated quote.
    """
    rounds_reached = [s["round"] for s in steps]

    # --- Tickets: sum FIFA bands for each round the team reaches ---
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

    # --- Hotels: fan's own numbers. One stop per round reached. ---
    stops = len(rounds_reached)
    hotel_total = stops * nights_per_stop * nightly_budget

    # --- Flights: estimate each travel leg between known/representative cities ---
    flight_low = flight_high = 0
    flight_legs = []
    if include_flights:
        for s in steps:
            # Use the first city's leg as representative for that round.
            city = s["cities"][0]
            leg = city.get("leg") or {}
            if leg.get("same_city"):
                continue
            km = leg.get("distance_km")
            if not km:
                continue
            lo, hi = _flight_band_for_km(km)
            flight_low += lo
            flight_high += hi
            flight_legs.append({
                "to": city["city"], "distance_mi": leg.get("distance_mi"),
                "low": lo, "high": hi,
            })

    grand_low = t_low + hotel_total + flight_low
    grand_high = t_high + hotel_total + flight_high

    return {
        "tickets": {
            "low": t_low, "high": t_high, "lines": ticket_lines,
            "basis": "FIFA published base prices (Oct 2025 release, dynamic pricing).",
        },
        "hotels": {
            "total": round(hotel_total),
            "stops": stops, "nights_per_stop": nights_per_stop,
            "nightly_budget": nightly_budget,
            "basis": "Your nightly budget x nights x stops.",
        },
        "flights": {
            "low": flight_low, "high": flight_high, "legs": flight_legs,
            "included": include_flights,
            "basis": "Distance-based planning estimate per leg — not a live quote.",
        },
        "grand": {"low": round(grand_low), "high": round(grand_high)},
    }
