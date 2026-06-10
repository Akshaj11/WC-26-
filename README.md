# Follow My Team — WC26 (live data)

A World Cup 2026 fan companion. Pick your team, see their route through the
tournament, and pull **live** flight prices, hotel rates, real ticket listings,
and live scores — in your own time zone.

**Core principle: no fabricated numbers.** Every price on screen is a real offer
from a configured provider, or it isn't shown. If a provider key is missing, the
app says how to enable it instead of inventing a figure.

---

## Deploy to Vercel

```bash
npm i -g vercel        # if you don't have it
vercel                 # from this folder; follow prompts
vercel --prod          # to ship
```

The structure is Vercel-native:
- `api/*.py` — Python serverless functions (one per endpoint)
- `public/index.html` — static frontend
- `vercel.json` — routing + Python runtime
- providers use only the Python standard library, so there's nothing to install

## Add your API keys (Vercel → Project → Settings → Environment Variables)

Nothing is hard-coded; keys live only in env vars. Add the ones you want live:

### Live scores — pick ONE (both free to start)
| Provider | Env var | Sign up |
|---|---|---|
| football-data.org | `FOOTBALLDATA_KEY` | https://www.football-data.org/client/register |
| API-Football | `APIFOOTBALL_KEY` | https://www.api-football.com/ (via RapidAPI or api-sports.io) |

### Flights + Hotels — Amadeus Self-Service (one account covers both)
| Env var | Where |
|---|---|
| `AMADEUS_CLIENT_ID` | https://developers.amadeus.com (create an app) |
| `AMADEUS_CLIENT_SECRET` | same app |
| `AMADEUS_BASE` (optional) | defaults to `https://test.api.amadeus.com`; set to `https://api.amadeus.com` for production data |

> Amadeus gives test keys instantly. Test data is real-shaped but limited to
> certain routes/markets; switch `AMADEUS_BASE` to production once approved for
> full coverage.

### Tickets — links work with no key
Ticket buttons always open live FIFA / SeatGeek / StubHub searches for the match.
Optionally add `SEATGEEK_CLIENT_ID` (https://seatgeek.com/account/develop) to also
surface matching SeatGeek events inline (prices shown only when SeatGeek exposes
them — never invented).

After adding vars, redeploy (`vercel --prod`) so the functions pick them up.

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/meta` | venues, groups, finish options |
| POST | `/api/path` | team route + per-leg distance + kickoff in your tz |
| GET | `/api/scores` | live/recent WC26 matches |
| GET | `/api/flights?origin=&dest=&date=&adults=` | live flight offers |
| GET | `/api/hotels?city=&check_in=&check_out=&adults=` | live hotel rates |
| GET | `/api/tickets?city=&round=` | resale deep-links (+ SeatGeek events if keyed) |

Each price endpoint returns `{"configured": false, "message": ...}` when its key
is absent — the contract that keeps fabricated numbers off the screen.

## How the "no fabrication" guarantee works

Every provider in `api/_lib/` follows the same contract:
1. No key → `configured: false` + a message telling you which env var to set.
2. Key present but API errors / returns nothing → explicit message, no number.
3. Real offers → normalized and shown.

The only numbers shown without any API are **great-circle distances**, which are
computed from coordinates (in `venues.py`) — real math, not market data.

## Known limits / honest notes

- WC26 ticket resale has no clean open live-price feed, so tickets are link-outs
  by design (your stated preference). SeatGeek inline events appear only if you
  add its key and only carry a price when SeatGeek itself exposes one.
- Early knockout cities depend on the bracket draw; those rounds list every
  possible venue rather than guessing a slot. Once FIFA fixes slot→city
  mappings, wire them in `api/_lib/bracket.py`.
- This sandbox can't reach external APIs, so live calls were validated by
  contract (unconfigured states) and logic, not by a live round-trip. Your first
  `vercel --prod` with keys set is where real offers will appear.

## Swapping flight/hotel providers

`api/_lib/flights.py` and `hotels.py` return a normalized shape. To use Duffel,
Kiwi/Tequila, or a hotel aggregator instead of Amadeus, implement the same
function signature and return shape; the frontend needs no changes.
