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

# Real groups from the Dec 5 2025 draw. "TBD" = intercontinental playoff slot.
GROUPS = {
    "A": ["Mexico", "South Korea", "South Africa", "TBD (Euro playoff)"],
    "B": ["Canada", "TBD (Euro playoff)", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Scotland", "Haiti"],
    "D": ["United States", "Paraguay", "Australia", "TBD (Euro playoff)"],
    "E": ["Germany", "Ecuador", "Ivory Coast", "Curacao"],
    "F": ["Netherlands", "Japan", "Tunisia", "TBD (Euro playoff)"],
    "G": ["Belgium", "Iran", "Egypt", "New Zealand"],
    "H": ["Spain", "Uruguay", "Saudi Arabia", "Cabo Verde"],
    "I": ["France", "Senegal", "Norway", "TBD (playoff)"],
    "J": ["Argentina", "Austria", "Algeria", "Jordan"],
    "K": ["Portugal", "Colombia", "Uzbekistan", "TBD (playoff)"],
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
