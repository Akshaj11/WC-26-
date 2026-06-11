"""
Live scores + fixtures — real data.

Supports two real providers behind one interface, picked by which key is set:
  - API-Football (api-sports.io)  -> APIFOOTBALL_KEY
  - football-data.org             -> FOOTBALLDATA_KEY  (free tier)

Returns live/recent WC26 matches normalized to a common shape. Never invents
a score; if no key is set, returns configured: False.
"""
import os
import json
import urllib.parse
import urllib.request

# football-data.org competition code for the FIFA World Cup
FD_WC_COMPETITION = "WC"


def _http_get(url, headers, timeout=10):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _via_footballdata():
    key = os.environ.get("FOOTBALLDATA_KEY")
    if not key:
        return None
    url = f"https://api.football-data.org/v4/competitions/{FD_WC_COMPETITION}/matches"
    res = _http_get(url, {"X-Auth-Token": key})
    out = []
    for m in res.get("matches", []):
        score = m.get("score", {}).get("fullTime", {})
        out.append({
            "home": m["homeTeam"].get("name") or "TBD",
            "away": m["awayTeam"].get("name") or "TBD",
            "home_score": score.get("home"),
            "away_score": score.get("away"),
            "status": m.get("status", ""),
            "minute": m.get("minute"),       # live minute if in play
            "utc": m.get("utcDate", ""),
            "stage": m.get("stage", ""),
        })
    return {"configured": True, "provider": "football-data.org", "matches": out}


def _via_apifootball():
    key = os.environ.get("APIFOOTBALL_KEY")
    if not key:
        return None
    season = os.environ.get("APIFOOTBALL_WC_SEASON", "2026")
    league = os.environ.get("APIFOOTBALL_WC_LEAGUE", "1")  # 1 = World Cup in API-Football
    params = {"league": league, "season": season}
    url = "https://v3.football.api-sports.io/fixtures?" + urllib.parse.urlencode(params)
    res = _http_get(url, {"x-apisports-key": key})
    out = []
    for f in res.get("response", []):
        teams = f.get("teams", {}); goals = f.get("goals", {}); fx = f.get("fixture", {})
        st = fx.get("status", {})
        out.append({
            "home": teams.get("home", {}).get("name", "TBD"),
            "away": teams.get("away", {}).get("name", "TBD"),
            "home_score": goals.get("home"),
            "away_score": goals.get("away"),
            "status": st.get("short", ""),
            "minute": st.get("elapsed"),     # live minute if in play
            "utc": fx.get("date", ""),
            "stage": (f.get("league", {}) or {}).get("round", ""),
        })
    return {"configured": True, "provider": "api-football", "matches": out}


def live_scores():
    """Real WC26 matches from whichever provider is configured."""
    for fn in (_via_apifootball, _via_footballdata):
        try:
            res = fn()
            if res is not None:
                return res
        except Exception as e:
            return {"configured": True, "error": str(e),
                    "message": "Live score lookup failed; showing no scores rather than fabricating them."}
    return {"configured": False,
            "message": "Add APIFOOTBALL_KEY or FOOTBALLDATA_KEY to enable live scores."}
