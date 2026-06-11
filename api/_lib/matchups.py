"""
Possible-opponents engine, built from the OFFICIAL WC26 draw (Dec 5, 2025)
and FIFA's fixed knockout bracket.

Integrity rules:
  * Group-stage opponents are KNOWN (the other three teams in the group), so we
    name them. A few groups still have a playoff "TBD" slot — shown as TBD.
  * Knockout opponents are expressed by BRACKET POSITION (e.g. "Winner Group E",
    "Runner-up Group B", "Best 3rd from C/D/F/G/H"), because which nation fills
    each slot depends on results not yet played. We DO resolve each position to
    the set of teams that could fill it, so fans see real candidate countries —
    but always framed as "could be", never as a fixed fixture.
  * Nothing here predicts results. We only follow the structure of the bracket.
"""

# Final 48-team field from the Dec 5 2025 draw + March 2026 playoffs (all
# placeholder slots now resolved).
GROUPS = {
    "A": ["Mexico", "South Korea", "South Africa", "Czechia"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Scotland", "Haiti"],
    "D": ["United States", "Paraguay", "Australia", "Türkiye"],
    "E": ["Germany", "Ecuador", "Ivory Coast", "Curacao"],
    "F": ["Netherlands", "Japan", "Tunisia", "Sweden"],
    "G": ["Belgium", "Iran", "Egypt", "New Zealand"],
    "H": ["Spain", "Uruguay", "Saudi Arabia", "Cabo Verde"],
    "I": ["France", "Senegal", "Norway", "Iraq"],
    "J": ["Argentina", "Austria", "Algeria", "Jordan"],
    "K": ["Portugal", "Colombia", "Uzbekistan", "DR Congo"],
    "L": ["England", "Croatia", "Panama", "Ghana"],
}

# Official Round of 32 pairings (match number -> the two bracket slots).
# Slots: ("W", "E")=winner Group E, ("R", "C")=runner-up Group C,
# ("3", "C/D/F/G/H")=best third from one of those groups.
R32 = {
    73: [("R", "A"), ("R", "B")],
    74: [("W", "E"), ("3", "A/B/C/D/F")],
    75: [("W", "F"), ("R", "C")],
    76: [("W", "C"), ("R", "F")],
    77: [("W", "I"), ("3", "C/D/F/G/H")],
    78: [("R", "E"), ("R", "I")],
    79: [("W", "A"), ("3", "C/E/F/H/I")],
    80: [("W", "L"), ("3", "E/H/I/J/K")],
    81: [("W", "D"), ("3", "B/E/F/I/J")],
    82: [("W", "G"), ("3", "A/E/H/I/J")],
    83: [("R", "K"), ("R", "L")],
    84: [("W", "H"), ("R", "J")],
    85: [("W", "B"), ("3", "E/F/G/I/J")],
    86: [("W", "J"), ("R", "H")],
    87: [("W", "K"), ("3", "D/E/I/J/L")],
    88: [("R", "D"), ("R", "G")],
}

# Knockout progression: match -> (feeder_match_1, feeder_match_2)
R16 = {
    89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
    93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87),
}
QF = {97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96)}
SF = {101: (97, 98), 102: (99, 100)}
FINAL = {103: (101, 102)}


def _slot_label(slot):
    kind, grp = slot
    if kind == "W":
        return f"Winner Group {grp}"
    if kind == "R":
        return f"Runner-up Group {grp}"
    return f"Best 3rd ({grp})"


def _slot_teams(slot):
    """Resolve a bracket slot to the real candidate nations."""
    kind, grp = slot
    if kind in ("W", "R"):
        return [t for t in GROUPS.get(grp, []) if not t.startswith("TBD")]
    # third-place slot: grp is like "C/D/F/G/H"
    teams = []
    for g in grp.split("/"):
        teams += [t for t in GROUPS.get(g, []) if not t.startswith("TBD")]
    return teams


def _find_r32_match(group, finish):
    """Which R32 match a team is in, and which slot is the OPPONENT."""
    want = {"win": "W", "runner": "R", "third": "3"}[finish]
    for match, slots in R32.items():
        for i, (kind, grp) in enumerate(slots):
            mine = (kind == want and (group in grp.split("/") if kind == "3"
                    else grp == group))
            if mine:
                opp = slots[1 - i]
                return match, opp
    return None, None


def _round_opponents(feeder_matches):
    """All bracket slots that could come out of the given feeder matches."""
    slots = []
    for m in feeder_matches:
        slots += R32.get(m, [])
    return slots


def _expand(matches):
    """Walk feeder matches down to their R32 slots (recursively)."""
    r32_reached = []
    stack = list(matches)
    while stack:
        m = stack.pop()
        if m in R32:
            r32_reached.append(m)
        elif m in R16:
            stack += list(R16[m])
        elif m in QF:
            stack += list(QF[m])
        elif m in SF:
            stack += list(SF[m])
        elif m in FINAL:
            stack += list(FINAL[m])
    return r32_reached


def opponents_for(group, finish):
    """Return possible opponents at each stage for a team finishing `finish`
    in `group`. Group stage = known nations; knockouts = bracket slots resolved
    to candidate nations.
    """
    out = {}

    # --- Group stage: the four teams in the group (the fan's team is one) ---
    mates = GROUPS.get(group, [])
    out["group"] = {
        "known": True,
        "teams": list(mates),
        "note": "The four teams in your group — you'll play the other three.",
    }

    # --- Round of 32: exact single opponent slot ---
    r32_match, opp_slot = _find_r32_match(group, finish)
    if not r32_match:
        return out
    out["r32"] = {
        "known": False,
        "match": r32_match,
        "slot_label": _slot_label(opp_slot),
        "teams": _slot_teams(opp_slot),
        "note": "One specific bracket slot — these are the nations that could fill it.",
    }

    # --- Later rounds: collect all slots feeding that part of the bracket ---
    def r16_match_for(r32_match):
        for m, feeders in R16.items():
            if r32_match in feeders:
                return m
        return None

    r16_m = r16_match_for(r32_match)
    if r16_m:
        other = [f for f in R16[r16_m] if f != r32_match]
        slots = _round_opponents(_expand(other))
        out["r16"] = _round_block(r16_m, slots, R16)

        qf_m = next((m for m, f in QF.items() if r16_m in f), None)
        if qf_m:
            other = [f for f in QF[qf_m] if f != r16_m]
            slots = _round_opponents(_expand(other))
            out["qf"] = _round_block(qf_m, slots, QF)

            sf_m = next((m for m, f in SF.items() if qf_m in f), None)
            if sf_m:
                other = [f for f in SF[sf_m] if f != qf_m]
                slots = _round_opponents(_expand(other))
                out["sf"] = _round_block(sf_m, slots, SF)

                # Final: the entire other half of the bracket
                other = [f for f in FINAL[103] if f != sf_m]
                slots = _round_opponents(_expand(other))
                out["final"] = _round_block(103, slots, FINAL)

    return out


def _round_block(match, slots, _table):
    # Deduplicate teams across all feeding slots
    teams, seen = [], set()
    for s in slots:
        for t in _slot_teams(s):
            if t not in seen:
                seen.add(t)
                teams.append(t)
    return {
        "known": False,
        "match": match,
        "possible_count": len(teams),
        "teams": teams,
        "note": "Any of these nations could reach this stage in your half of the bracket.",
    }


# Which match each city hosts, per round. From the official WC26 schedule.
# Venue keys match venues.py. R32: each city -> its match number(s).
VENUE_MATCH = {
    "r32": {
        "la": [73, 84], "boston": [74], "guadalajara": [75], "houston": [76],
        "nyc": [77], "dallas": [78, 88], "mexicocity": [79], "atlanta": [80],
        "bayarea": [81], "seattle": [82], "toronto": [83], "vancouver": [85],
        "miami": [86], "kansascity": [87],
    },
    "r16": {
        "philly": [89], "houston": [90], "nyc": [91], "mexicocity": [92],
        "dallas": [93], "seattle": [94], "atlanta": [95], "vancouver": [96],
    },
    "qf": {"boston": [97], "la": [98], "miami": [99], "kansascity": [100]},
    "sf": {"dallas": [101], "atlanta": [102]},
    "final": {"nyc": [103]},
}


# Group-stage fixtures actually scheduled at each venue (from the official
# WC26 schedule, teams resolved). Each entry: (date, "Team A vs Team B", group).
GROUP_FIXTURES = {
    "mexicocity": [("Jun 11", "Mexico vs South Africa", "A"),
                   ("Jun 17", "Uzbekistan vs Colombia", "K"),
                   ("Jun 24", "Mexico vs Czechia", "A")],
    "guadalajara": [("Jun 11", "South Korea vs Czechia", "A"),
                    ("Jun 18", "Mexico vs South Korea", "A"),
                    ("Jun 23", "Colombia vs DR Congo", "K"),
                    ("Jun 26", "Uruguay vs Spain", "H")],
    "toronto": [("Jun 12", "Canada vs Bosnia and Herzegovina", "B"),
                ("Jun 17", "Ghana vs Panama", "L"),
                ("Jun 20", "Germany vs Ivory Coast", "E"),
                ("Jun 23", "Panama vs Croatia", "L"),
                ("Jun 26", "Senegal vs Iraq", "I")],
    "la": [("Jun 12", "USA vs Paraguay", "D"),
           ("Jun 15", "Iran vs New Zealand", "G"),
           ("Jun 18", "Switzerland vs Bosnia and Herzegovina", "B"),
           ("Jun 21", "Belgium vs Iran", "G"),
           ("Jun 25", "USA vs Türkiye", "D")],
    "nyc": [("Jun 13", "Brazil vs Morocco", "C"),
            ("Jun 16", "France vs Senegal", "I"),
            ("Jun 22", "Norway vs Senegal", "I"),
            ("Jun 25", "Ecuador vs Germany", "E"),
            ("Jun 27", "Panama vs England", "L")],
    "vancouver": [("Jun 13", "Australia vs Türkiye", "D"),
                  ("Jun 18", "Canada vs Qatar", "B"),
                  ("Jun 21", "New Zealand vs Egypt", "G"),
                  ("Jun 24", "Canada vs Switzerland", "B"),
                  ("Jun 26", "New Zealand vs Belgium", "G")],
    "boston": [("Jun 13", "Haiti vs Scotland", "C"),
               ("Jun 16", "Iraq vs Norway", "I"),
               ("Jun 19", "Scotland vs Morocco", "C"),
               ("Jun 23", "England vs Ghana", "L"),
               ("Jun 26", "Norway vs France", "I")],
    "bayarea": [("Jun 13", "Qatar vs Switzerland", "B"),
                ("Jun 16", "Austria vs Jordan", "J"),
                ("Jun 19", "Türkiye vs Paraguay", "D"),
                ("Jun 22", "Jordan vs Algeria", "J"),
                ("Jun 25", "Paraguay vs Australia", "D")],
    "houston": [("Jun 14", "Germany vs Curacao", "E"),
                ("Jun 17", "Portugal vs DR Congo", "K"),
                ("Jun 20", "Netherlands vs Sweden", "F"),
                ("Jun 23", "Portugal vs Uzbekistan", "K"),
                ("Jun 26", "Cabo Verde vs Saudi Arabia", "H")],
    "philly": [("Jun 14", "Ivory Coast vs Ecuador", "E"),
               ("Jun 19", "Brazil vs Haiti", "C"),
               ("Jun 22", "France vs Iraq", "I"),
               ("Jun 25", "Curacao vs Ivory Coast", "E"),
               ("Jun 27", "Croatia vs Ghana", "L")],
    "dallas": [("Jun 14", "Netherlands vs Japan", "F"),
               ("Jun 17", "England vs Croatia", "L"),
               ("Jun 22", "Argentina vs Austria", "J"),
               ("Jun 25", "Japan vs Sweden", "F"),
               ("Jun 27", "Jordan vs Argentina", "J")],
    "monterrey": [("Jun 14", "Sweden vs Tunisia", "F"),
                  ("Jun 20", "Tunisia vs Japan", "F"),
                  ("Jun 24", "South Korea vs South Africa", "A")],
    "atlanta": [("Jun 15", "Spain vs Cabo Verde", "H"),
                ("Jun 18", "Czechia vs South Africa", "A"),
                ("Jun 21", "Spain vs Saudi Arabia", "H"),
                ("Jun 24", "Morocco vs Haiti", "C"),
                ("Jun 27", "DR Congo vs Uzbekistan", "K")],
    "seattle": [("Jun 15", "Belgium vs Egypt", "G"),
                ("Jun 19", "USA vs Australia", "D"),
                ("Jun 24", "Bosnia and Herzegovina vs Qatar", "B"),
                ("Jun 26", "Egypt vs Iran", "G")],
    "miami": [("Jun 15", "Saudi Arabia vs Uruguay", "H"),
              ("Jun 21", "Uruguay vs Cabo Verde", "H"),
              ("Jun 24", "Scotland vs Brazil", "C"),
              ("Jun 27", "Colombia vs Portugal", "K")],
    "kansascity": [("Jun 16", "Argentina vs Algeria", "J"),
                   ("Jun 20", "Ecuador vs Curacao", "E"),
                   ("Jun 25", "Tunisia vs Netherlands", "F"),
                   ("Jun 27", "Algeria vs Austria", "J")],
}


def group_fixtures_at(city_key):
    """The scheduled group-stage matches at this venue, or None."""
    fx = GROUP_FIXTURES.get(city_key)
    if not fx:
        return None
    return {"fixtures": [{"date": d, "match": m, "group": g} for d, m, g in fx]}


def teams_at_venue(city_key, round_key):
    """Which nations could play at this specific venue in this round.

    Honest: derived from the fixed bracket. For R32 we know the exact slot
    pairing at each venue; for later rounds we resolve the feeder matches back
    to the set of nations that could reach that venue. Group stage is handled
    separately (specific group fixtures), so not included here.
    """
    matches = VENUE_MATCH.get(round_key, {}).get(city_key)
    if not matches:
        return None
    teams, seen, pairings = [], set(), []
    for match in matches:
        if round_key == "r32":
            slots = R32.get(match, [])
            pairings.append(" vs ".join(_slot_label(s) for s in slots))
            for s in slots:
                for t in _slot_teams(s):
                    if t not in seen:
                        seen.add(t); teams.append(t)
        else:
            # resolve feeders down to R32 slots
            r32s = _expand([match])
            slots = []
            for m in r32s:
                slots += R32.get(m, [])
            for s in slots:
                for t in _slot_teams(s):
                    if t not in seen:
                        seen.add(t); teams.append(t)
    return {
        "round": round_key, "matches": matches,
        "pairings": pairings,          # only meaningful for r32
        "teams": teams, "count": len(teams),
    }
