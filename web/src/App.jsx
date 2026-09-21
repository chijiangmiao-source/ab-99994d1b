import { useMemo, useState } from "react";
import TubeEditor from "./components/TubeEditor.jsx";
import ResultPanel from "./components/ResultPanel.jsx";
import InfeasiblePanel from "./components/InfeasiblePanel.jsx";
import { fetchBalance } from "./api.js";

const DEFAULT_TUBES = [
  { id: "A", mass: "12", current_slot: 0, allowed_slots: [0, 1, 4, 5] },
  { id: "B", mass: "12", current_slot: 4, allowed_slots: [0, 4] },
  { id: "C", mass: "7", current_slot: 2, allowed_slots: [2, 3, 6, 7] },
  { id: "D", mass: "7", current_slot: 6, allowed_slots: [2, 6] },
];

let keyCounter = 0;
const nextKey = () => ++keyCounter;
const withKey = (t) => ({ ...t, key: nextKey() });

/** 客户端预校验（服务端仍会独立校验并返回 422）。 */
function validateTubes(tubes) {
  const issues = [];
  if (tubes.length < 2) issues.push("每批至少需要 2 支样管");
  if (tubes.length > 8) issues.push("每批最多 8 支样管");
  const ids = new Map();
  const slots = new Map();
  tubes.forEach((t, i) => {
    const row = `第 ${i + 1} 行`;
    const id = t.id.trim();
    if (!id) issues.push(`${row}：标识不能为空`);
    else if (ids.has(id)) issues.push(`${row}：标识 “${id}” 与第 ${ids.get(id) + 1} 行重复`);
    else ids.set(id, i);
    if (!/^\d+$/.test(t.mass.trim()) || BigInt(t.mass.trim() || "0") <= 0n)
      issues.push(`${row}：质量必须为正整数`);
    const s = Number(t.current_slot);
    if (slots.has(s)) issues.push(`${row}：当前槽位 ${s} 与第 ${slots.get(s) + 1} 行冲突`);
    else slots.set(s, i);
  });
  return issues;
}

function normalizeDetail(detail) {
  if (typeof detail === "string") return [detail];
  if (Array.isArray(detail)) {
    return detail.map((d) => {
      const loc = Array.isArray(d.loc)
        ? d.loc.filter((x) => x !== "body").join(".")
        : "";
      return loc ? `${loc}: ${d.msg}` : d.msg || JSON.stringify(d);
    });
  }
  return [JSON.stringify(detail)];
}

export default function App() {
  const [tubes, setTubes] = useState(() => DEFAULT_TUBES.map(withKey));
  const [outcome, setOutcome] = useState(null);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(false);

  const issues = useMemo(() => validateTubes(tubes), [tubes]);

  function updateTube(key, patch) {
    setTubes((ts) => ts.map((t) => (t.key === key ? { ...t, ...patch } : t)));
  }

  function toggleSlot(key, slot) {
    setTubes((ts) =>
      ts.map((t) => {
        if (t.key !== key) return t;
        const has = t.allowed_slots.includes(slot);
        return {
          ...t,
          allowed_slots: has
            ? t.allowed_slots.filter((s) => s !== slot)
            : [...t.allowed_slots, slot].sort((a, b) => a - b),
        };
      })
    );
  }

  function removeTube(key) {
    setTubes((ts) => ts.filter((t) => t.key !== key));
  }

  function addTube() {
    setTubes((ts) => {
      if (ts.length >= 8) return ts;
      const usedIds = new Set(ts.map((t) => t.id.trim()));
      const id =
        "ABCDEFGH".split("").find((c) => !usedIds.has(c)) ||
        `T${ts.length + 1}`;
      const usedSlots = new Set(ts.map((t) => Number(t.current_slot)));
      const free = [...Array(8).keys()].find((s) => !usedSlots.has(s)) ?? 0;
      return [
        ...ts,
        { key: nextKey(), id, mass: "1", current_slot: free, allowed_slots: [free] },
      ];
    });
  }

  async function onCompute() {
    if (issues.length) {
      setErrors(issues);
      return;
    }
    setErrors([]);
    setLoading(true);
    try {
      const payload = tubes.map((t) => ({
        id: t.id.trim(),
        mass: Number(t.mass.trim()),
        current_slot: Number(t.current_slot),
        allowed_slots: [...t.allowed_slots].sort((a, b) => a - b),
      }));
      const { status, data } = await fetchBalance(payload);
      if (status === 200 && data?.status === "optimal") {
        setOutcome({ kind: "optimal", data });
      } else if (status === 200 && data?.status === "infeasible") {
        setOutcome({ kind: "infeasible", data });
      } else if (data?.detail) {
        setErrors(normalizeDetail(data.detail));
      } else {
        setErrors([`服务返回异常（HTTP ${status}）`]);
      }
    } catch (e) {
      setErrors([`无法连接 API：${e.message}`]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <h1>离心机转子配平审计台</h1>
        <p>
          八槽等角转子 · Q(√2) 精确比较合力平方 · 先最小化合力，再最少移动样管 ·
          同优取规范解并标注必然/可选/不可能关系
        </p>
      </header>

      <main className="main">
        <section className="card">
          <div className="card-title">
            <h2>样管批次</h2>
            <span className="muted">{tubes.length} / 8 管</span>
          </div>
          <TubeEditor
            tubes={tubes}
            onUpdate={updateTube}
            onToggleSlot={toggleSlot}
            onRemove={removeTube}
            onAdd={addTube}
          />
          {issues.length > 0 && (
            <ul className="issues">
              {issues.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          )}
          <div className="actions">
            <button
              className="primary"
              onClick={onCompute}
              disabled={loading || issues.length > 0}
            >
              {loading ? "计算中…" : "计算全局配平"}
            </button>
            <span className="muted">
              目标：最小化 |F|²（Q(√2) 精确比较）→ 最少移动 → 规范解
            </span>
          </div>
        </section>

        {errors.length > 0 && (
          <section className="card alert-error">
            <h2>请求被拒绝</h2>
            <ul className="issues">
              {errors.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
            <p className="muted">原始输入已保留，可修正后重新提交。</p>
          </section>
        )}

        {outcome?.kind === "infeasible" && (
          <InfeasiblePanel witness={outcome.data.witness} />
        )}
        {outcome?.kind === "optimal" && <ResultPanel result={outcome.data} />}
      </main>
    </div>
  );
}
