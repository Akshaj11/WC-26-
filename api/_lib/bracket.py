"""WC26 bracket-path engine. See venues.py for the data it references."""

R32_CITIES = ["la","boston","seattle","houston","dallas","atlanta","kansascity",
              "vancouver","mexicocity","guadalajara","monterrey","miami","philly",
              "nyc","toronto","bayarea"]
R16_CITIES = ["houston","philly","nyc","mexicocity","dallas","seattle","atlanta","vancouver"]
QF_CITIES  = ["la","miami","kansascity","boston"]
SF_CITIES  = ["dallas","atlanta"]
THIRD_CITY = "miami"
FINAL_CITY = "nyc"

GROUPS = list("ABCDEFGHIJKL")
ROUND_LABELS = {"group":"Group stage","r32":"Round of 32","r16":"Round of 16",
                "qf":"Quarter-final","sf":"Semi-final","final":"Final"}


def _step(rk, cities, certain):
    return {"round": rk, "round_label": ROUND_LABELS[rk], "cities": cities, "certain": certain}


def path_for_team(group, finish, group_city):
    """Forward path. Late rounds exact; early knockout rounds list candidate
    cities, since the exact slot depends on the bracket draw (not fabricated)."""
    path = [_step("group", [group_city], True)]
    path.append(_step("r32", R32_CITIES, False))
    path.append(_step("r16", R16_CITIES, False))
    path.append(_step("qf", QF_CITIES, False))
    path.append(_step("sf", SF_CITIES, False))
    path.append(_step("final", [FINAL_CITY], True))
    return path


def finishes():
    return [
        {"key": "win", "label": "Win the group (1st)"},
        {"key": "runner", "label": "Runner-up (2nd)"},
        {"key": "third", "label": "Best third-place"},
    ]
