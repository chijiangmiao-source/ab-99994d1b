"""八槽离心机转子的精确配平求解器。

转子：8 个等角槽位，槽位 k 位于角度 k*45°（k = 0..7）。
合力平方的比较全部在 Q(√2) 中用整数运算精确完成，不使用任何浮点容差。

质量为 m 的样管位于槽位 k 时，力矢量为 m*(cos θk, sin θk)。
把 2*cos、2*sin 表示为 a + b·√2（a, b ∈ ℤ），则双倍合力
2F = (Ax + Bx·√2, Ay + By·√2) 的系数都是整数，并且

    4·|F|² = P + Q·√2，其中 P = Ax² + 2·Bx² + Ay² + 2·By²，
                              Q = 2·(Ax·Bx + Ay·By)。

两个形如 P + Q·√2 的数通过 cmp_pq() 精确比较（√2 为无理数，
p + q·√2 = 0 当且仅当 p = q = 0，因此符号判定是精确的）。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import gcd

SLOT_COUNT = 8

# 2*(cos(k*45°), sin(k*45°))，记为 (ax, bx, ay, by)：
# 2cos = ax + bx·√2，2sin = ay + by·√2
SLOT_VEC2 = (
    (2, 0, 0, 0),    # 槽位 0，  0°
    (0, 1, 0, 1),    # 槽位 1， 45°
    (0, 0, 2, 0),    # 槽位 2， 90°
    (0, -1, 0, 1),   # 槽位 3，135°
    (-2, 0, 0, 0),   # 槽位 4，180°
    (0, -1, 0, -1),  # 槽位 5，225°
    (0, 0, -2, 0),   # 槽位 6，270°
    (0, 1, 0, -1),   # 槽位 7，315°
)

NECESSARY = "necessary"   # 必然：所有前两目标同优的方案都占用该槽
OPTIONAL = "optional"     # 可选：部分同优方案占用该槽
IMPOSSIBLE = "impossible"  # 不可能：任何同优方案都不占用该槽


def cmp_pq(p1: int, q1: int, p2: int, q2: int) -> int:
    """精确比较 p1 + q1·√2 与 p2 + q2·√2，返回 -1 / 0 / 1。"""
    dp = p1 - p2
    dq = q1 - q2
    if dp == 0:
        return (dq > 0) - (dq < 0)
    if dq == 0:
        return (dp > 0) - (dp < 0)
    if (dp > 0) == (dq > 0):
        return 1 if dp > 0 else -1
    # dp、dq 异号：dp + dq·√2 的符号由 dp² 与 2·dq² 的大小决定
    lhs = dp * dp
    rhs = 2 * dq * dq
    if lhs == rhs:
        # √2 无理 => 仅当 dp == dq == 0，前面已处理；此处仅为防御
        return 0
    if dp > 0:  # dq < 0：值 = dp - |dq|·√2
        return 1 if lhs > rhs else -1
    # dp < 0 < dq：值 = dq·√2 - |dp|
    return 1 if lhs < rhs else -1


@dataclass(frozen=True)
class Tube:
    tid: str
    mass: int
    current_slot: int
    allowed: tuple  # 升序去重后的允许槽位


@dataclass
class SolveResult:
    p: int               # |F|² = (p + q·√2) / scale
    q: int
    scale: int           # 恒为 4
    force2: tuple        # (Ax, Bx, Ay, By)：2F = (Ax + Bx·√2, Ay + By·√2)
    moves: int           # 最少移动管数
    assignment: tuple    # 规范解：assignment[i] = 第 i 支管所在槽位
    optimal_count: int   # 前两目标同优的方案总数
    relations: tuple     # relations[i][s] ∈ {necessary, optional, impossible}


def solve(tubes: list[Tube]) -> SolveResult | None:
    """枚举全部可行装载，按 (合力, 移动数, 规范序列) 取最优。

    目标顺序：
      1. 最小化合力（在 Q(√2) 中精确比较 4·|F|² = P + Q·√2）；
      2. 最小化移动样管数；
      3. 同优时按槽位 0..7 上的样管标识序列取字典序最小，
         空槽排在任意标识之后。
    返回 None 表示无可行装载（调用方应先经 conflict_witness 判定）。
    """
    n = len(tubes)
    # 回溯顺序：允许槽少者优先（剪枝），标识次序保证确定性
    order = sorted(range(n), key=lambda i: (len(tubes[i].allowed), tubes[i].tid))

    allowed = [t.allowed for t in tubes]
    masses = [t.mass for t in tubes]
    current = [t.current_slot for t in tubes]

    best_pq: list | None = None
    best_moves = 0
    optimal: list[tuple[tuple, tuple]] = []  # (规范序列键, 各管槽位)

    assign = [-1] * n
    slot_owner: list[str | None] = [None] * SLOT_COUNT
    used = [False] * SLOT_COUNT

    def recurse(depth: int, ax: int, bx: int, ay: int, by: int, moves: int) -> None:
        nonlocal best_pq, best_moves
        if depth == n:
            p = ax * ax + 2 * bx * bx + ay * ay + 2 * by * by
            q = 2 * (ax * bx + ay * by)
            if best_pq is None:
                better, equal = True, False
            else:
                c = cmp_pq(p, q, best_pq[0], best_pq[1])
                better, equal = c < 0, c == 0
            if better or (equal and moves < best_moves):
                best_pq = [p, q]
                best_moves = moves
                optimal.clear()
                equal = True
            if equal and moves == best_moves:
                seq_key = tuple(
                    (0, owner) if owner is not None else (1, "")
                    for owner in slot_owner
                )
                optimal.append((seq_key, tuple(assign)))
            return
        i = order[depth]
        m = masses[i]
        ci = current[i]
        for s in allowed[i]:
            if used[s]:
                continue
            va, vb, vc, vd = SLOT_VEC2[s]
            used[s] = True
            assign[i] = s
            slot_owner[s] = tubes[i].tid
            recurse(depth + 1,
                    ax + m * va, bx + m * vb,
                    ay + m * vc, by + m * vd,
                    moves + (0 if s == ci else 1))
            slot_owner[s] = None
            assign[i] = -1
            used[s] = False

    recurse(0, 0, 0, 0, 0, 0)
    if best_pq is None:
        return None

    _, canonical = min(optimal, key=lambda item: item[0])
    total = len(optimal)

    counts = [[0] * SLOT_COUNT for _ in range(n)]
    for _, a in optimal:
        for i, s in enumerate(a):
            counts[i][s] += 1
    relations = tuple(
        tuple(
            NECESSARY if counts[i][s] == total
            else OPTIONAL if counts[i][s] else IMPOSSIBLE
            for s in range(SLOT_COUNT)
        )
        for i in range(n)
    )

    ax = bx = ay = by = 0
    for i, s in enumerate(canonical):
        m = masses[i]
        va, vb, vc, vd = SLOT_VEC2[s]
        ax += m * va
        bx += m * vb
        ay += m * vc
        by += m * vd

    return SolveResult(
        p=best_pq[0], q=best_pq[1], scale=4,
        force2=(ax, bx, ay, by), moves=best_moves,
        assignment=canonical, optimal_count=total, relations=relations,
    )


def _max_matching(tubes: list[Tube]) -> dict[int, int]:
    """Kuhn 算法求 样管 -> 允许槽 的最大匹配，返回 {槽位: 样管下标}。"""
    match_slot: dict[int, int] = {}

    def augment(u: int, seen: set[int]) -> bool:
        for s in tubes[u].allowed:
            if s in seen:
                continue
            seen.add(s)
            if s not in match_slot or augment(match_slot[s], seen):
                match_slot[s] = u
                return True
        return False

    for u in range(len(tubes)):
        augment(u, set())
    return match_slot


def conflict_witness(tubes: list[Tube]) -> tuple[set[int], list[int]] | None:
    """无可行装载时返回霍尔冲突见证 (样管下标集合 S, 允许槽并集 N(S))，
    满足 |N(S)| < |S|；有可行装载时返回 None。

    构造：取最大匹配，从全部未匹配样管出发沿交错路可达的样管集 S，
    其邻域恰为可达槽位集，且 |N(S)| = |S| - (未匹配管数) < |S|。
    """
    match_slot = _max_matching(tubes)
    n = len(tubes)
    if len(match_slot) == n:
        return None
    matched_tubes = set(match_slot.values())
    start = [u for u in range(n) if u not in matched_tubes]

    z_tubes = set(start)
    z_slots: set[int] = set()
    queue = deque(start)
    while queue:
        u = queue.popleft()
        for s in tubes[u].allowed:
            if match_slot.get(s) == u:
                continue  # 跳过匹配边，只沿非匹配边走
            if s not in z_slots:
                z_slots.add(s)
                v = match_slot.get(s)
                if v is not None and v not in z_tubes:
                    z_tubes.add(v)
                    queue.append(v)

    union = sorted({s for u in z_tubes for s in tubes[u].allowed})
    # 交错路论证保证并集即 z_slots，且 |并集| < |S|
    assert len(union) < len(z_tubes), "霍尔见证构造失败"
    return z_tubes, union


def format_radical(p: int, q: int) -> str:
    """把 p + q·√2 格式化为精确字符串，如 "3 + 2√2"、"-√2"、"0"。"""
    out = ""
    if p != 0 or q == 0:
        out = str(p)
    if q != 0:
        coeff = "√2" if abs(q) == 1 else f"{abs(q)}√2"
        if out:
            out += (" + " if q > 0 else " - ") + coeff
        else:
            out = ("" if q > 0 else "-") + coeff
    return out


def format_resultant(p: int, q: int, scale: int) -> str:
    """把 (p + q·√2)/scale 约分后格式化，如 "(3 + √2)/2"、"2"、"√2"。"""
    g = gcd(gcd(abs(p), abs(q)), scale)
    p2, q2, s2 = p // g, q // g, scale // g
    body = format_radical(p2, q2)
    if s2 == 1:
        return body
    if p2 != 0 and q2 != 0:
        return f"({body})/{s2}"
    return f"{body}/{s2}"
