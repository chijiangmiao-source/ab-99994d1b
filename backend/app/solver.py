"""Exact global rotor-balancing solver.

Rotor: 8 equally spaced slots numbered 0..7.  Slot k sits at angle k*pi/4,
so its unit vector, multiplied by 2 to keep integer coefficients, is

    2*v_k = (2 cos(k pi/4), 2 sin(k pi/4)) in Z[sqrt(2)]^2

A placement's resultant is sum of masses times 2*v_k.  The true resultant
is half of that sum; squaring introduces a factor 1/4 which is a strictly
positive constant shared by every candidate, so comparing squared sums of
the doubled vectors gives the exact same ordering.

Objective, lexicographic:
  1. minimise the exact squared resultant force;
  2. minimise the number of tubes moved away from their current slots;
  3. among ties, take the canonical solution: sequence of tube labels read
     slot by slot (slot 0 first), empty slots ordered after every label.

For all solutions tied on (1) and (2) we classify every tube/slot pair:
  mandatory  - the tube occupies that slot in every optimal solution;
  possible   - it occupies it in some but not all optimal solutions;
  impossible - it never occupies it in an optimal solution.

When no legal loading exists we return a Hall-style conflict witness: a set
of tubes whose union of allowed slots is smaller than the set itself.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from . import qsqrt
from .qsqrt import Pair

SLOT_COUNT = 8

# Doubled unit vectors 2*(cos, sin) at angle k*pi/4, as Q(sqrt2) pairs.
# x coefficient: (a, b) meaning a + b*sqrt(2); same for y.
_SLOT_VECTORS: Tuple[Tuple[Pair, Pair], ...] = (
    ((2, 0), (0, 0)),   # 0: (2, 0)
    ((0, 1), (0, 1)),   # 1: (sqrt2, sqrt2)
    ((0, 0), (2, 0)),   # 2: (0, 2)
    ((0, -1), (0, 1)),  # 3: (-sqrt2, sqrt2)
    ((-2, 0), (0, 0)),  # 4: (-2, 0)
    ((0, -1), (0, -1)), # 5: (-sqrt2, -sqrt2)
    ((0, 0), (-2, 0)),  # 6: (0, -2)
    ((0, 1), (0, -1)),  # 7: (sqrt2, -sqrt2)
)


class ValidationError(Exception):
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.field = field


def validate_input(payload: dict) -> List[dict]:
    tubes = payload.get("tubes")
    if not isinstance(tubes, list):
        raise ValidationError("样管列表必须是数组", "tubes")
    if not (2 <= len(tubes) <= SLOT_COUNT):
        raise ValidationError(
            f"每批须含 2 至 {SLOT_COUNT} 个样管，当前为 {len(tubes) if isinstance(tubes, list) else '?'} 个",
            "tubes",
        )

    labels: set[str] = set()
    currents: set[int] = set()
    normalised: List[dict] = []
    for i, raw in enumerate(tubes):
        where = f"tubes[{i}]"
        if not isinstance(raw, dict):
            raise ValidationError("每个样管必须是对象", where)
        label = raw.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValidationError("样管标识必须为非空字符串", f"{where}.label")
        label = label.strip()
        if label in labels:
            raise ValidationError(f"样管标识 {label!r} 重复，标识必须唯一", f"{where}.label")
        labels.add(label)

        mass = raw.get("mass")
        if not isinstance(mass, int) or isinstance(mass, bool) or mass <= 0:
            raise ValidationError(f"样管 {label} 的质量必须为正整数", f"{where}.mass")

        current = raw.get("current_slot")
        if not isinstance(current, int) or isinstance(current, bool) or not (0 <= current < SLOT_COUNT):
            raise ValidationError(
                f"样管 {label} 的当前槽位必须为 0..{SLOT_COUNT - 1} 的整数",
                f"{where}.current_slot",
            )
        if current in currents:
            raise ValidationError(
                f"槽位 {current} 同时是样管 {label} 与其他样管的当前槽位，当前槽位必须互异",
                f"{where}.current_slot",
            )
        currents.add(current)

        allowed = raw.get("allowed_slots")
        if not isinstance(allowed, list) or not allowed:
            raise ValidationError(f"样管 {label} 必须指定至少一个允许槽位", f"{where}.allowed_slots")
        norm_allowed: List[int] = []
        seen_slots: set[int] = set()
        for s in allowed:
            if not isinstance(s, int) or isinstance(s, bool) or not (0 <= s < SLOT_COUNT):
                raise ValidationError(
                    f"样管 {label} 的允许槽位只能取 0..{SLOT_COUNT - 1}",
                    f"{where}.allowed_slots",
                )
            if s not in seen_slots:
                seen_slots.add(s)
                norm_allowed.append(s)
        norm_allowed.sort()
        normalised.append(
            {
                "label": label,
                "mass": mass,
                "current_slot": current,
                "allowed_slots": norm_allowed,
            }
        )
    return normalised


# --------------------------------------------------------------------------- #
# Resultant force
# --------------------------------------------------------------------------- #

def resultant(assignment: Sequence[int], masses: Sequence[int]) -> Tuple[Pair, Pair, Pair]:
    """Return (sx, sy, force_sq) for doubled vectors, exactly.

    force_sq is |sum m * 2 v|^2 = 4 * |true resultant|^2.
    """
    sx = qsqrt.zero()
    sy = qsqrt.zero()
    for tube_idx, slot in enumerate(assignment):
        vx, vy = _SLOT_VECTORS[slot]
        m = masses[tube_idx]
        sx = qsqrt.add(sx, qsqrt.scale(vx, m))
        sy = qsqrt.add(sy, qsqrt.scale(vy, m))
    # Squaring a real Q(sqrt2) number: (a + b√2)^2 = (a^2 + 2b^2) + 2ab√2.
    # The √2 coefficient is generally nonzero, which is precisely why the
    # comparison must live in Q(sqrt2) rather than in the integers.
    fx = qsqrt.mul(sx, sx)
    fy = qsqrt.mul(sy, sy)
    force_sq = qsqrt.add(fx, fy)
    return sx, sy, force_sq


# --------------------------------------------------------------------------- #
# Hall conflict witness
# --------------------------------------------------------------------------- #

def find_hall_witness(tubes: List[dict]) -> Optional[dict]:
    """Return a subset of tubes whose allowed-slot union is smaller.

    Uses Hall's marriage theorem via Kuhn's augmenting-path matching.
    When a maximum matching leaves a tube unmatched, the tubes reachable
    from that tube through alternating edges (tube -> allowed slot ->
    currently matched tube) form a Hall-violating set: every slot in
    their allowed union is matched back into the set, hence the union
    contains strictly fewer slots than tubes.
    """
    n = len(tubes)
    allowed = [set(t["allowed_slots"]) for t in tubes]

    match_slot: Dict[int, int] = {}  # slot -> tube

    def augment(t: int, seen_slots: set[int]) -> bool:
        for s in allowed[t]:
            if s in seen_slots:
                continue
            seen_slots.add(s)
            other = match_slot.get(s)
            if other is None or augment(other, seen_slots):
                match_slot[s] = t
                return True
        return False

    failed_tube: Optional[int] = None
    for t in range(n):
        if not augment(t, set()):
            failed_tube = t
            break

    if failed_tube is None:
        return None

    # Alternating reachability from the unmatched tube in the final
    # (maximum) matching.
    reachable = {failed_tube}
    stack = [failed_tube]
    while stack:
        u = stack.pop()
        for s in allowed[u]:
            other = match_slot.get(s)
            if other is not None and other not in reachable:
                reachable.add(other)
                stack.append(other)

    union: set[int] = set()
    for u in reachable:
        union |= allowed[u]
    return {
        "tubes": sorted(tubes[u]["label"] for u in reachable),
        "allowed_union": sorted(union),
    }


# --------------------------------------------------------------------------- #
# Enumeration and optimisation
# --------------------------------------------------------------------------- #

def _canonical_key(assignment: Sequence[int], labels: Sequence[str]) -> Tuple[Tuple[int, str], ...]:
    """Label sequence by slot; empty slots sort strictly after any label.

    Each entry is (0, label) for an occupied slot and (1, "") for an empty
    one, which is total and independent of the label character set.
    """
    at_slot: Dict[int, str] = {}
    for tube_idx, slot in enumerate(assignment):
        at_slot[slot] = labels[tube_idx]
    return tuple(
        (0, at_slot[s]) if s in at_slot else (1, "")
        for s in range(SLOT_COUNT)
    )


def solve(tubes: List[dict]) -> dict:
    n = len(tubes)
    labels = [t["label"] for t in tubes]
    masses = [t["mass"] for t in tubes]
    currents = [t["current_slot"] for t in tubes]
    allowed = [set(t["allowed_slots"]) for t in tubes]

    witness = find_hall_witness(tubes)
    if witness is not None:
        return {
            "feasible": False,
            "slot_count": SLOT_COUNT,
            "tubes": labels,
            "conflict_witness": {
                "tubes": witness["tubes"],
                "allowed_union": witness["allowed_union"],
                "tube_count": len(witness["tubes"]),
                "union_size": len(witness["allowed_union"]),
                "reason": (
                    f"样管子集 {witness['tubes']} 共 {len(witness['tubes'])} 个，"
                    f"但允许槽并集仅为 {witness['allowed_union']}（{len(witness['allowed_union'])} 个），"
                    "槽位不可复用，故无可行装载（Hall 见证）。"
                ),
            },
            "optimal": None,
        }

    tube_order = list(range(n))
    best_force: Optional[Pair] = None
    best_moves: Optional[int] = None
    best_key: Optional[Tuple] = None
    best_assignment: Optional[Tuple[int, ...]] = None

    candidates = [sorted(allowed[t]) for t in tube_order]

    def enumerate_placements():
        partial: List[int] = []

        def recurse(idx: int, used: int):
            if idx == n:
                yield tuple(partial)
                return
            for s in candidates[idx]:
                bit = 1 << s
                if used & bit:
                    continue
                partial.append(s)
                yield from recurse(idx + 1, used | bit)
                partial.pop()

        yield from recurse(0, 0)

    # First pass: establish the lexicographic optimum
    # (force squared, move count, canonical slot-label sequence).
    for assignment in enumerate_placements():
        _, _, force = resultant(assignment, masses)
        moves = sum(1 for i, s in enumerate(assignment) if s != currents[i])
        key = _canonical_key(assignment, labels)
        if best_force is None:
            better = True
        else:
            c = qsqrt.sign(qsqrt.sub(force, best_force))
            better = c < 0 or (
                c == 0
                and (
                    moves < best_moves
                    or (moves == best_moves and key < best_key)
                )
            )
        if better:
            best_force = force
            best_moves = moves
            best_key = key
            best_assignment = assignment

    # Second pass: collect *every* solution tied on the first two objectives.
    # The mandatory/possible/impossible classification is defined over the
    # set of solutions tied on force then moves; the canonical rule only
    # selects which one is presented as the representative solution.
    all_optimal: List[Tuple[int, ...]] = []
    for assignment in enumerate_placements():
        _, _, force = resultant(assignment, masses)
        moves = sum(1 for i, s in enumerate(assignment) if s != currents[i])
        if force == best_force and moves == best_moves:
            all_optimal.append(assignment)
    assignment = best_assignment
    assert assignment is not None  # feasibility proven by Hall check
    sx, sy, force4 = resultant(assignment, masses)
    moves = best_moves

    # Count how many optimal solutions exist and build the tube/slot relation
    # table over all of them.
    occupancy: Dict[Tuple[int, int], int] = {}
    for sol in all_optimal:
        for tube_idx, slot in enumerate(sol):
            occupancy[(tube_idx, slot)] = occupancy.get((tube_idx, slot), 0) + 1
    total = len(all_optimal)

    relations: Dict[str, List[dict]] = {}
    for i, label in enumerate(labels):
        rows = []
        for s in range(SLOT_COUNT):
            count = occupancy.get((i, s), 0)
            if count == total:
                status = "mandatory"
            elif count > 0:
                status = "possible"
            else:
                status = "impossible"
            rows.append(
                {
                    "slot": s,
                    "status": status,
                    "occurrences": count,
                }
            )
        relations[label] = rows

    placed = [
        {
            "tube": labels[i],
            "mass": masses[i],
            "slot": assignment[i],
            "moved": assignment[i] != currents[i],
        }
        for i in range(n)
    ]
    slot_occupancy: List[Optional[dict]] = [None] * SLOT_COUNT
    for i, s in enumerate(assignment):
        slot_occupancy[s] = {"tube": labels[i], "mass": masses[i]}

    return {
        "feasible": True,
        "slot_count": SLOT_COUNT,
        "tubes": labels,
        "optimal_solution_count": total,
        "objective": {
            "force_squared_quadrupled": {
                "a": force4[0],
                "b": force4[1],
                "exact": qsqrt.describe(force4),
            },
            "force_squared": qsqrt.describe(force4, divisor=4),
            "resultant_quadrupled": {
                "x": qsqrt.describe(sx),
                "y": qsqrt.describe(sy),
            },
            "moves": moves,
            "move_detail": [
                {"tube": labels[i], "from": currents[i], "to": assignment[i]}
                for i in range(n)
                if assignment[i] != currents[i]
            ],
            "balanced_exactly": force4 == (0, 0),
        },
        "placement": placed,
        "slots": slot_occupancy,
        "canonical_key": list(best_key),
        "relations": relations,
        "status_legend": {
            "mandatory": "必然：所有最优方案中该管都在此槽",
            "possible": "可选：存在但非所有最优方案如此",
            "impossible": "不可能：最优方案中该管不会在此槽",
        },
    }
