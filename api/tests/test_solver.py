"""求解器单元测试：精确比较、规范解、关系标注、霍尔见证、随机对拍。"""

import random
from itertools import permutations

from app.solver import (
    IMPOSSIBLE,
    NECESSARY,
    OPTIONAL,
    SLOT_VEC2,
    Tube,
    cmp_pq,
    conflict_witness,
    format_resultant,
    solve,
)


def brute_force(tubes):
    """独立实现：直接枚举槽位排列，返回 ((P,Q), moves, [各管槽位...])。"""
    n = len(tubes)
    best = None
    optimal = []
    for perm in permutations(range(8), n):
        if any(perm[i] not in tubes[i].allowed for i in range(n)):
            continue
        ax = bx = ay = by = 0
        for i, s in enumerate(perm):
            va, vb, vc, vd = SLOT_VEC2[s]
            m = tubes[i].mass
            ax += m * va
            bx += m * vb
            ay += m * vc
            by += m * vd
        p = ax * ax + 2 * bx * bx + ay * ay + 2 * by * by
        q = 2 * (ax * bx + ay * by)
        moves = sum(perm[i] != tubes[i].current_slot for i in range(n))
        if best is None or cmp_pq(p, q, best[0][0], best[0][1]) < 0 or (
            cmp_pq(p, q, best[0][0], best[0][1]) == 0 and moves < best[1]
        ):
            best = ((p, q), moves)
            optimal = []
        if cmp_pq(p, q, best[0][0], best[0][1]) == 0 and moves == best[1]:
            optimal.append(perm)
    return best, optimal


def canonical_of(tubes, optimal):
    def key(perm):
        owner = [None] * 8
        for i, s in enumerate(perm):
            owner[s] = tubes[i].tid
        return tuple((0, t) if t is not None else (1, "") for t in owner)

    return min(optimal, key=key)


def T(tid, mass, cur, allowed):
    return Tube(tid, mass, cur, tuple(sorted(allowed)))


# ---------- cmp_pq ----------

def test_cmp_pq_basic():
    assert cmp_pq(0, 0, 0, 0) == 0
    assert cmp_pq(1, 0, 0, 0) == 1
    assert cmp_pq(0, 0, 1, 0) == -1
    assert cmp_pq(0, 1, 0, 0) == 1      # √2 > 0
    assert cmp_pq(0, 1, 1, 0) == 1      # √2 > 1
    assert cmp_pq(0, 1, 2, 0) == -1     # √2 < 2
    assert cmp_pq(3, 0, 0, 2) == 1      # 3 > 2√2 (9 > 8)
    assert cmp_pq(0, 2, 3, 0) == -1     # 2√2 < 3
    assert cmp_pq(7, 5, 14, 0) == 1     # 7 + 5√2 ≈ 14.071 > 14
    assert cmp_pq(10, -7, 0, 0) == 1    # 10 - 7√2 ≈ 0.1005 > 0
    assert cmp_pq(10, -7, 0, 1) == -1   # 10 - 7√2 < √2
    # 逼近 √2 的分数：p/q = 131836323/93222358，p² 与 2q² 差 1
    p, q = 131836323, 93222358
    assert p * p - 2 * q * q == 1
    assert cmp_pq(p, -q, 0, 0) == 1     # p - q√2 > 0（极小的正数）


def test_format_resultant():
    assert format_resultant(0, 0, 4) == "0"
    assert format_resultant(8, 0, 4) == "2"
    assert format_resultant(0, 4, 4) == "√2"
    assert format_resultant(2, 2, 4) == "(1 + √2)/2"
    assert format_resultant(6, -2, 4) == "(3 - √2)/2"
    assert format_resultant(1, 0, 4) == "1/4"
    assert format_resultant(0, -2, 4) == "-√2/2"


# ---------- 经典情形 ----------

def test_two_tubes_opposite_canonical():
    # 两支等质量管，当前槽 0、1，允许全部槽位。
    # 最优合力 0（对置），最少移动 1：A 留 0、B 去 4，或 B 留 1、A 去 5。
    # 规范解取槽位序列字典序最小：槽 0 放 A 优于空槽。
    tubes = [T("A", 1, 0, range(8)), T("B", 1, 1, range(8))]
    res = solve(tubes)
    assert (res.p, res.q) == (0, 0)
    assert res.moves == 1
    assert res.assignment == (0, 4)          # A→0, B→4
    assert res.optimal_count == 2
    rel = res.relations
    assert rel[0][0] == OPTIONAL and rel[0][5] == OPTIONAL
    assert rel[1][1] == OPTIONAL and rel[1][4] == OPTIONAL
    assert rel[0][1] == IMPOSSIBLE and rel[1][0] == IMPOSSIBLE
    assert rel[0][2] == IMPOSSIBLE


def test_already_balanced_zero_moves():
    # 当前已对置：不移动即最优，且唯一
    tubes = [T("A", 5, 0, range(8)), T("B", 5, 4, range(8))]
    res = solve(tubes)
    assert (res.p, res.q) == (0, 0)
    assert res.moves == 0
    assert res.assignment == (0, 4)
    assert res.optimal_count == 1
    assert res.relations[0][0] == NECESSARY
    assert res.relations[1][4] == NECESSARY
    assert res.relations[0][4] == IMPOSSIBLE


def test_full_rotor_equal_masses():
    # 8 管等质量填满 8 槽：合力必为 0；当前已在位者不动最优
    tubes = [T(f"T{i}", 3, i, range(8)) for i in range(8)]
    res = solve(tubes)
    assert (res.p, res.q) == (0, 0)
    assert res.moves == 0
    assert res.assignment == tuple(range(8))
    assert res.optimal_count == 1
    for i in range(8):
        assert res.relations[i][i] == NECESSARY


def test_tie_break_with_forced_moves():
    # Y、Z 等质量，允许槽 {2,6}（对置），当前槽 0、1 均不可用。
    # 两种放法合力都为 0、都移动 2 管 -> 同优，规范解取槽 2 放标识较小者。
    tubes = [T("Y", 5, 0, [2, 6]), T("Z", 5, 1, [2, 6])]
    res = solve(tubes)
    assert (res.p, res.q) == (0, 0)
    assert res.moves == 2
    assert res.optimal_count == 2
    assert res.assignment == (2, 6)  # Y→2, Z→6
    assert res.relations[0][2] == OPTIONAL
    assert res.relations[0][6] == OPTIONAL
    assert res.relations[1][2] == OPTIONAL
    assert res.relations[1][6] == OPTIONAL
    assert res.relations[0][0] == IMPOSSIBLE


def test_exactness_near_tie():
    # Pell 构造：2r²-q²=1（r=38613965, q=54608393）=> p=2r=77227930, p²-2q²=2。
    # 两种候选方案的 4|F|² 分别为
    #   D→0: 11774850484169836 - 8325369518032968·√2
    #   D→4: 12083762204169836 - 8543803090032968·√2
    # 二者的 float64 值完全相同（1000000000054.0），但精确值 D→0 更小；
    # 且 D→0 需移动 2 管、D→4 只需 1 管——任何用浮点比较合力、
    # 再以移动数打破"平局"的实现都会错误地选择 D→4。
    tubes = [
        T("D", 500000, 4, [0, 4]),
        T("R1", 27304197, 1, [1]),
        T("R2", 27304196, 7, [7]),
        T("R3", 38613965, 5, [4]),
        T("R4", 3, 2, [2]),
    ]
    res = solve(tubes)
    assert res.assignment == (0, 1, 7, 4, 2)  # D 必须精确地放到槽 0
    assert res.moves == 2
    assert (res.p, res.q) == (11774850484169836, -8325369518032968)
    assert res.optimal_count == 1
    assert res.relations[0][0] == NECESSARY
    assert res.relations[0][4] == IMPOSSIBLE


def test_witness_three_tubes_two_slots():
    tubes = [T("A", 1, 0, [1, 2]), T("B", 1, 3, [1, 2]), T("C", 1, 4, [1, 2])]
    w = conflict_witness(tubes)
    assert w is not None
    tset, union = w
    assert tset == {0, 1, 2}
    assert union == [1, 2]
    assert len(union) < len(tset)
    assert solve(tubes) is None


def test_witness_empty_allowed():
    tubes = [T("A", 1, 0, []), T("B", 1, 1, [1, 2])]
    w = conflict_witness(tubes)
    assert w is not None
    tset, union = w
    assert 0 in tset
    assert len(union) < len(tset)


def test_feasible_no_witness():
    tubes = [T("A", 1, 0, [0, 1]), T("B", 1, 1, [1, 2])]
    assert conflict_witness(tubes) is None


# ---------- 随机对拍 ----------

def test_random_against_brute_force():
    rng = random.Random(20260921)
    for trial in range(60):
        n = rng.randint(2, 6)
        currents = rng.sample(range(8), n)
        tubes = []
        for i in range(n):
            k = rng.randint(1, 8)
            allowed = rng.sample(range(8), k)
            tubes.append(T(f"T{i}", rng.randint(1, 9), currents[i], allowed))
        best, optimal = brute_force(tubes)
        if best is None:
            assert conflict_witness(tubes) is not None
            continue
        res = solve(tubes)
        assert res is not None
        assert (res.p, res.q) == best[0]
        assert res.moves == best[1]
        assert res.optimal_count == len(optimal)
        canon = canonical_of(tubes, optimal)
        assert res.assignment == canon
        # 关系标注与暴力统计一致
        for i in range(n):
            for s in range(8):
                cnt = sum(1 for a in optimal if a[i] == s)
                expect = NECESSARY if cnt == len(optimal) else OPTIONAL if cnt else IMPOSSIBLE
                assert res.relations[i][s] == expect, (trial, i, s)
