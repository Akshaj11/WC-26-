# Follow My Team — WC26 (live data)

A World Cup 2026 fan companion. Pick your team, see their route through the
tournament, and pull flight prices, hotel and ticket search, and live scores —
all in your own time zone.

---

## Deploy (GitHub → Vercel, no command line)

1. Create a GitHub repo and upload the **contents** of this folder (so `api/`,
   `public/`, and `vercel.json` sit at the repo root — not nested in a subfolder).
2. At vercel.com, **Add New → Project**, import the repo.
3. Before deploying, add your environment variables (below), then **Deploy**.
4. Every future commit on GitHub auto-redeploys. To apply new env vars, redeploy
   the latest deployment from the Vercel **Deployments** tab.

## Add your API keys (Vercel → Project → Settings → Environment Variables)

Nothing is hard-coded; keys live only in env vars. Add the ones you want live:

### Live scores — pick ONE (both free to start)
| Provider | Env var | Sign up |
|---|---|---|
| football-data.org | `FOOTBALLDATA_KEY` | https://www.football-data.org/client/register |
| API-Football | `APIFOOTBALL_KEY` | https://www.api-football.com/ (via RapidAPI or api-sports.io) |

### Flights — cached price estimates (Travelpayouts, free, no card)
| Env var | Where |
|---|---|
| `TRAVELPAYOUTS_TOKEN` | Sign up at https://www.travelpayouts.com, connect the Aviasales program, copy the token from Profile → API token |

The flight panel shows cached recent fares (real prices people saw in the last
few days, clearly labelled "not a live quote") plus always-on links to live
Google Flights / Skyscanner search. Without the token, you still get the live
links — only the cached estimates are hidden. This replaces Amadeus, which is
being **deprecated on July 17, 2026** (mid-tournament) and so is unsuitable here.

### Hotels — no key needed
Hotel buttons open live Booking.com / Hotels.com / Google Hotels searches for
the venue city and your dates. Free real-time hotel pricing APIs no longer exist
for indie use, so hotels are a search link-out to Booking.com and Hotels.com.

### Tickets — links work with no key
Ticket buttons always open live FIFA / SeatGeek / StubHub searches for the match.
Optionally add `SEATGEEK_CLIENT_ID` (https://seatgeek.com/account/develop) to also
surface matching SeatGeek events inline (prices shown only when SeatGeek exposes
them).

After adding vars, redeploy (`vercel --prod`) so the functions pick them up.

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/meta` | venues, groups, finish options |
| POST | `/api/path` | team route + per-leg distance + kickoff in your tz |
| GET | `/api/scores` | live/recent WC26 matches |
| GET | `/api/flights?origin=&dest=&date=&adults=` | cached fare estimates + live-search links |
| GET | `/api/hotels?city=&check_in=&check_out=&adults=` | Booking.com / Hotels.com search links |
| GET | `/api/tickets?city=&round=` | resale deep-links (+ SeatGeek events if keyed) |

Each price endpoint returns `{"configured": false, "message": ...}` when its key
is absent, so the UI can show a "connect this" state instead of an empty panel.

## How data sources behave

Every provider in `api/_lib/` follows the same pattern:
1. No key → `configured: false` + a message naming the env var to set.
2. Key present but the API errors or returns nothing → an explicit message.
3. Real results → normalized and shown.

Distances between venues are computed from coordinates (in `venues.py`).

## Notes

- WC26 ticket resale has no clean open live-price feed, so tickets are link-outs
  by design (your stated preference). SeatGeek inline events appear only if you
  add its key and only carry a price when SeatGeek itself exposes one.
- Early knockout cities depend on the bracket draw; those rounds list every
  possible venue rather than guessing a slot. Once FIFA fixes slot→city
  mappings, wire them in `api/_lib/bracket.py`.
- This sandbox can't reach external APIs, so live calls were validated by
  contract (unconfigured states) and logic, not by a live round-trip. Your first
  `vercel --prod` with keys set is where real offers will appear.

## Swapping flight providers

`api/_lib/flights.py` returns a normalized shape. To use Duffel, Kiwi/Tequila,
or another source instead of Travelpayouts, implement the same function
signature and return shape; the frontend needs no changes. Hotels and tickets
are link-out modules — adjust the URL builders in `hotels.py` / `tickets.py` to
add or change marketplaces.
