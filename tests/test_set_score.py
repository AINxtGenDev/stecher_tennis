"""Regression tests for set-score parsing / winner determination.

This is a sensitive part of the logic: the winner is recomputed from the set
scores server-side (WR-07) and must reject any result that contradicts them.
The abbreviated tiebreak notation 7:6 / 6:7 (without the explicit tiebreak
points) must be accepted in addition to the explicit form 7:6(7:4).
"""
from app import _parse_set_score


# score -> True (left/challenger won set), False (right/opponent won), None (invalid)
CASES = {
    # abbreviated tiebreak set (the feature)
    "7:6": True,
    "6:7": False,
    # explicit tiebreak
    "7:6(7:4)": True,
    "7:6(8:6)": True,
    "6:7(4:7)": False,
    "6:7(6:8)": False,
    # standard valid sets
    "6:0": True,
    "6:4": True,
    "0:6": False,
    "4:6": False,
    "7:5": True,
    "5:7": False,
    # invalid
    "6:5": None,
    "5:6": None,
    "6:6": None,
    "7:7": None,
    "7:4": None,
    "7:0": None,
    "7:3": None,
    "8:6": None,
    "6:6(7:5)": None,   # parens but games are not 7:6 / 6:7
    "7:6(7:6)": None,   # tiebreak tie
    "7:6(6:4)": None,   # tiebreak did not reach 7
    "7:6(4:7)": None,   # games winner contradicts tiebreak winner
    "": None,
    "abc": None,
    "6": None,
    "6:": None,
}


def test_parse_set_score_truth_table():
    for score, expected in CASES.items():
        assert _parse_set_score(score) == expected, score


def test_abbreviated_tiebreak_match_2_0():
    # "7:6 7:6" must be a clean 2:0 challenger win
    sets = ["7:6", "7:6"]
    won = [_parse_set_score(s) for s in sets]
    assert won == [True, True]
    assert sum(1 for w in won if w) == 2  # challenger 2 sets
