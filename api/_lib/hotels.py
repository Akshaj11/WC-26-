"""
Hotels — honest link-out, no fabricated rates.

Free real-time hotel pricing APIs effectively no longer exist for indie use:
Booking.com and Expedia are partner-only with commercial agreements, and the
one free option (Amadeus hotel search) is being deprecated in July 2026. Rather
than show a made-up or unavailable price, we deep-link to live hotel search on
Booking.com and Hotels.com for the venue city and the fan's dates. The fan lands
on real, current listings — no number is ever invented here.
"""
import urllib.parse


def search_hotels(city_label, country_name, check_in, check_out, adults=1):
    """Return live hotel-search deep-links for a venue city + date range.

    check_in / check_out: 'YYYY-MM-DD'. No API key required.
    """
    where = f"{city_label} {country_name}".strip()
    q = urllib.parse.quote_plus(where)

    booking = (
        "https://www.booking.com/searchresults.html?"
        + urllib.parse.urlencode({
            "ss": where,
            "checkin": check_in,
            "checkout": check_out,
            "group_adults": adults,
            "no_rooms": 1,
        })
    )
    hotels_com = f"https://www.hotels.com/search.do?q-destination={q}&q-check-in={check_in}&q-check-out={check_out}"
    google = (
        "https://www.google.com/travel/hotels/" + q
        + "?" + urllib.parse.urlencode({"checkin": check_in, "checkout": check_out})
    )

    return {
        "configured": True,           # links always work; nothing to configure
        "mode": "links",
        "links": [
            {"site": "Booking.com", "url": booking},
            {"site": "Hotels.com", "url": hotels_com},
            {"site": "Google Hotels", "url": google},
        ],
        "note": "Live hotel listings for your dates — opens on the booking site.",
    }
