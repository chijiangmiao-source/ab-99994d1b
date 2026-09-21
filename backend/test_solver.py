"""Sanity checks for the exact solver (not part of the shipped app)."""
import itertools
import math
import sys

sys.path.insert(0, "/workspace/backend")

from app import qsqrt
from app.solver import find_hall_witness, resultant, solve, validate_input


def brute_force(tubes):
    """Independent enumeration with exact resultant pairs, lex key."""
    n = len(tubes)
    masses = [t["mass"] for t in tubes]
    currents = [t["current_slot"] for t in tubes]
    allowed = [set(t["allowed_slots"]) for t in tubes]
    best = None
    for perm in itertools.permutations(range(8), n):
        if all(perm[i] in allowed[i] for i in range(n)):
            f2 = resultant(perm, masses)[2]
            moves = sum(p != c for p, c in zip(perm, currents))
            key = (f2, moves)
            if best is None:
                best = (key, perm)
            elif qsqrt.less(f2, best[0][0]) or (f2 == best[0][0] and moves < best[0][1]):
                best = (key, perm)
    return best


def check_case(tubes, name):
    valid = validate_input({"tubes": tubes})
    res = solve(valid)
    if not res["feasible"]:
        bf = brute_force(valid)
        assert bf is None, f"{name}: solver says infeasible but float ref found a loading"
        w = res["conflict_witness"]
        assert w["tube_count"] > w["union_size"], name
        print(f"  {name}: infeasible as expected, witness {w['tubes']} union {w['allowed_union']}")
        return
    bf = brute_force(valid)
    assert bf is not None, f"{name}: float ref found nothing?"
    (bf2, bm), bperm = bf
    got_perm = tuple(p["slot"] for p in sorted(res["placement"], key=lambda p: [t["label"] for t in valid].index(p["tube"])))
    sx, sy, f4 = resultant(got_perm, [t["mass"] for t in valid])
    assert f4 == bf2, f"{name}: force mismatch {f4} vs {bf2}"
    assert res["objective"]["moves"] == bm, f"{name}: moves {res['objective']['moves']} vs {bm}"

    # Verify relation classification by independent counting.
    n = len(valid)
    masses = [t["mass"] for t in valid]
    currents = [t["current_slot"] for t in valid]
    allowed = [set(t["allowed_slots"]) for t in valid]
    labels = [t["label"] for t in valid]
    optimal = []
    bestf = None
    for perm in itertools.permutations(range(8), n):
        if all(perm[i] in allowed[i] for i in range(n)):
            fx = sum(m * math.cos(s * math.pi / 4) for m, s in zip(masses, perm))
            fy = sum(m * math.sin(s * math.pi / 4) for m, s in zip(masses, perm))
            # 4|F|^2 lies in Z[sqrt2] (sqrt2 part may be nonzero); compare
            # exactly via the solver's own resultant.
            f2 = resultant(perm, masses)[2]
            moves = sum(p != c for p, c in zip(perm, currents))
            better = (
                bestf is None
                or qsqrt.less(f2, bestf[0])
                or (f2 == bestf[0] and moves < bestf[1])
            )
            if better:
                bestf = (f2, moves)
                optimal = [perm]
            elif f2 == bestf[0] and moves == bestf[1]:
                optimal.append(perm)
    assert res["optimal_solution_count"] == len(optimal), (
        f"{name}: opt count {res['optimal_solution_count']} vs {len(optimal)}")
    for i, label in enumerate(labels):
        for s in range(8):
            cnt = sum(1 for p in optimal if p[i] == s)
            status = res["relations"][label][s]["status"]
            occ = res["relations"][label][s]["occurrences"]
            assert occ == cnt, f"{name}: occurrences {label}/{s}"
            want = "mandatory" if cnt == len(optimal) else ("possible" if cnt else "impossible")
            assert status == want, f"{name}: {label} slot {s} {status} != {want}"
    print(f"  {name}: OK force^2={res['objective']['force_squared']['exact']}, "
          f"moves={res['objective']['moves']}, {len(optimal)} opt solution(s)")


def main():
    # Exact ring checks
    assert qsqrt.sign((3, -2)) == 1   # 3 - 2√2 > 0
    assert qsqrt.sign((2, -2)) < 0    # 2 - 2√2 < 0
    assert qsqrt.sign((0, 5)) == 1
    assert qsqrt.mul((0, 1), (0, 1)) == (2, 0)  # √2*√2

    cases = [
        # two equal opposite tubes: perfectly balanced
        ([{"label": "A", "mass": 10, "current_slot": 0, "allowed_slots": [0, 1, 2, 3, 4, 5, 6, 7]},
          {"label": "B", "mass": 10, "current_slot": 2, "allowed_slots": [0, 1, 2, 3, 4, 5, 6, 7]}], "equal-pair"),
        # asymmetric, all slots allowed
        ([{"label": "A", "mass": 3, "current_slot": 0, "allowed_slots": list(range(8))},
          {"label": "B", "mass": 5, "current_slot": 1, "allowed_slots": list(range(8))},
          {"label": "C", "mass": 2, "current_slot": 4, "allowed_slots": list(range(8))}], "triple-free"),
        # restricted slots
        ([{"label": "A", "mass": 4, "current_slot": 0, "allowed_slots": [0, 4]},
          {"label": "B", "mass": 4, "current_slot": 4, "allowed_slots": [0, 4]}], "restricted-balanced"),
        ([{"label": "A", "mass": 4, "current_slot": 0, "allowed_slots": [0, 1]},
          {"label": "B", "mass": 4, "current_slot": 4, "allowed_slots": [0, 1]}], "infeasible-pair"),
        # current slot outside allowed -> at least one move needed
        ([{"label": "A", "mass": 7, "current_slot": 2, "allowed_slots": [0, 4]},
          {"label": "B", "mass": 7, "current_slot": 3, "allowed_slots": [0, 4]}], "must-move"),
        # 8 tubes full rotor permutation
        ([{"label": f"T{i}", "mass": (i % 3) + 1, "current_slot": i, "allowed_slots": list(range(8))}
          for i in range(8)], "full-rotor"),
        # random-ish 5 tubes
        ([{"label": "P", "mass": 1, "current_slot": 0, "allowed_slots": [0, 1, 2]},
          {"label": "Q", "mass": 2, "current_slot": 3, "allowed_slots": [2, 3, 4]},
          {"label": "R", "mass": 3, "current_slot": 5, "allowed_slots": [4, 5, 6]},
          {"label": "S", "mass": 4, "current_slot": 6, "allowed_slots": [6, 7, 0]},
          {"label": "U", "mass": 5, "current_slot": 7, "allowed_slots": [7, 1, 3]}], "restricted-5"),
        # infeasible: 3 tubes into a 2-slot union
        ([{"label": "X", "mass": 1, "current_slot": 0, "allowed_slots": [0, 1]},
          {"label": "Y", "mass": 1, "current_slot": 1, "allowed_slots": [0, 1]},
          {"label": "Z", "mass": 1, "current_slot": 2, "allowed_slots": [0]}], "hall-3"),
    ]
    for tubes, name in cases:
        check_case(tubes, name)
    print("all solver tests passed")


if __name__ == "__main__":
    main()
