import React, { useEffect, useMemo, useState } from 'react'
import { solve as apiSolve, fetchMeta } from './api'
import { defaultTubes } from './defaults'
import TubeEditor from './components/TubeEditor'
import RotorDiagram from './components/RotorDiagram'
import RelationMatrix from './components/RelationMatrix'

function normaliseMass(value) {
  // Number inputs hand back strings. Convert integral strings exactly; leave
  // empty / non-integer / non-numeric input so the API replies with its
  // precise Chinese validation message (input itself is never discarded).
  if (typeof value === 'number') return value
  const s = String(value).trim()
  if (s === '') return null
  return /^[+-]?\d+$/.test(s) ? Number(s) : s
}

function toApiTubes(tubes) {
  return tubes.map((t) => ({
    label: String(t.label).trim(),
    mass: normaliseMass(t.mass),
    current_slot: Number(t.current_slot),
    allowed_slots: t.allowed_slots.map(Number),
  }))
}

export default function App() {
  const [tubes, setTubes] = useState(() => {
    try {
      const saved = localStorage.getItem('centrifuge-input-v1')
      if (saved) return JSON.parse(saved)
    } catch {
      /* ignore */
    }
    return defaultTubes
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [apiHealthy, setApiHealthy] = useState(null)
  const [meta, setMeta] = useState(null)

  useEffect(() => {
    localStorage.setItem('centrifuge-input-v1', JSON.stringify(tubes))
  }, [tubes])

  useEffect(() => {
    fetch('/health')
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(() => setApiHealthy(true))
      .catch(() => setApiHealthy(false))
    fetchMeta().then(setMeta).catch(() => {})
  }, [])

  const currentMap = useMemo(
    () => new Map(tubes.map((t) => [t.label, Number(t.current_slot)])),
    [tubes],
  )

  const onCalculate = async () => {
    setLoading(true)
    setError(null)
    // Keep the current input exactly as edited; only the result is replaced.
    try {
      const res = await apiSolve(toApiTubes(tubes))
      setResult(res)
    } catch (e) {
      setResult(null)
      setError({ message: e.message, field: e.field || null })
    } finally {
      setLoading(false)
    }
  }

  const onReset = () => {
    setTubes(defaultTubes)
    setResult(null)
    setError(null)
  }

  return (
    <div className="page">
      <header className="app-header">
        <div>
          <h1>高速离心机 · 全局配平审计台</h1>
          <p className="subtitle">
            八槽等角转子（槽位 0–7）· 合力平方以 Q(√2) 精确数比较 · 先最小合力、再最少移动、同优取规范解
          </p>
        </div>
        <div className={`health-badge ${apiHealthy ? 'ok' : apiHealthy === false ? 'bad' : ''}`}>
          API：{apiHealthy === null ? '检测中…' : apiHealthy ? '已连通' : '不可用'}
        </div>
      </header>

      <main className="layout">
        <section className="panel input-panel">
          <h2>① 样管与槽位编辑</h2>
          <TubeEditor tubes={tubes} onChange={setTubes} errorField={error?.field} />
          <div className="actions">
            <button type="button" className="btn btn-primary" onClick={onCalculate} disabled={loading}>
              {loading ? '精确计算中…' : '计算全局最优装载'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={onReset}>
              恢复示例
            </button>
          </div>
          {error && (
            <div className="alert alert-error" role="alert">
              <strong>输入未通过校验，输入已保留：</strong>
              <div>{error.message}</div>
              {error.field && <div className="error-field">定位字段：{error.field}</div>}
            </div>
          )}
        </section>

        {result && !result.feasible && (
          <section className="panel">
            <h2>② 无可行装载 · 冲突见证</h2>
            <div className="alert alert-warn" role="alert">
              <div>
                <strong>不存在满足“每管进入一个允许槽且槽位不复用”的装载。</strong>
              </div>
              <p>{result.conflict_witness.reason}</p>
              <div className="witness">
                <div>
                  <span className="witness-label">冲突样管子集（{result.conflict_witness.tube_count} 个）：</span>
                  {result.conflict_witness.tubes.join('、')}
                </div>
                <div>
                  <span className="witness-label">允许槽并集（{result.conflict_witness.union_size} 个）：</span>
                  槽 {result.conflict_witness.allowed_union.join('、')}
                </div>
              </div>
              <p className="witness-hint">
                由 Hall 婚配定理，{result.conflict_witness.tube_count} 个样管只有{' '}
                {result.conflict_witness.union_size} 个不同的允许槽，必然至少两管争槽。请放宽某些管的允许槽后重算；
                上方原始输入已完整保留。
              </p>
            </div>
          </section>
        )}

        {result && result.feasible && (
          <>
            <section className="panel">
              <h2>② 最优目标（Q(√2) 精确值）</h2>
              <ObjectivePanel result={result} />
            </section>

            <section className="panel">
              <h2>③ 八槽转子图</h2>
              <div className="rotor-row">
                <RotorDiagram
                  slots={result.slots}
                  placement={result.placement}
                  relations={result.relations}
                  currentMap={currentMap}
                />
                <PlacementLegend />
              </div>
            </section>

            <section className="panel">
              <h2>
                ④ 管槽归属矩阵
                <span className="panel-note">
                  （统计 {result.optimal_solution_count} 个前两项目标同优的方案；规范解以方框标出）
                </span>
              </h2>
              <RelationMatrix
                relations={result.relations}
                tubes={tubes}
                assignment={result.placement}
                totalOptimal={result.optimal_solution_count}
              />
              <CanonicalKey result={result} />
            </section>
          </>
        )}

        {!result && !error && (
          <section className="panel placeholder">
            <h2>② 计算结果</h2>
            <p>编辑样管后点击“计算全局最优装载”，这里将显示精确合力、移动方案、转子图与管槽归属矩阵。</p>
            {meta && (
              <ul className="meta-list">
                {meta.objectives.map((o) => (
                  <li key={o}>{o}</li>
                ))}
              </ul>
            )}
          </section>
        )}
      </main>

      <footer className="app-footer">
        全部比较在 Q(√2) = {'{ a + b√2 : a, b ∈ ℚ }'} 内精确完成，无浮点容差、无预置答案。
      </footer>
    </div>
  )
}

function ObjectivePanel({ result }) {
  const o = result.objective
  const f = o.force_squared
  const q = o.force_squared_quadrupled
  return (
    <div className="objective">
      <div className="obj-grid">
        <div className="obj-card">
          <div className="obj-title">合力平方 |F|²</div>
          <div className="obj-value exact">{f.exact}</div>
          <div className="obj-sub">
            = (a+b√2)/4，其中 a={q.a}, b={q.b}
          </div>
        </div>
        <div className="obj-card">
          <div className="obj-title">移动样管数</div>
          <div className="obj-value">{o.moves}</div>
          <div className="obj-sub">第二目标：在最优合力下最少移动</div>
        </div>
        <div className="obj-card">
          <div className="obj-title">精确平衡</div>
          <div className={`obj-value ${o.balanced_exactly ? 'balanced' : 'unbalanced'}`}>
            {o.balanced_exactly ? '合力为 0' : '合力 ≠ 0'}
          </div>
          <div className="obj-sub">
            合力向量（2F）= ({o.resultant_quadrupled.x.exact}, {o.resultant_quadrupled.y.exact})
          </div>
        </div>
        <div className="obj-card">
          <div className="obj-title">前两项同优方案数</div>
          <div className="obj-value">{result.optimal_solution_count}</div>
          <div className="obj-sub">必然/可选/不可能据此集合统计</div>
        </div>
      </div>
      {o.move_detail.length > 0 ? (
        <div className="moves">
          <strong>移动明细：</strong>
          {o.move_detail.map((m) => (
            <span className="move-chip" key={m.tube}>
              {m.tube}：{m.from} → {m.to}
            </span>
          ))}
        </div>
      ) : (
        <div className="moves">
          <strong>无需移动任何样管，当前布局已是最优。</strong>
        </div>
      )}
    </div>
  )
}

function PlacementLegend() {
  return (
    <ul className="legend legend-vertical">
      <li>
        <span className="legend-swatch rel-mandatory">●</span> 绿色＝该管在此槽为必然关系
      </li>
      <li>
        <span className="legend-swatch rel-possible">◐</span> 黄色＝可选关系（规范解恰好如此时）
      </li>
      <li>
        <span className="legend-swatch rel-impossible">·</span> 灰＝最优解中不可能
      </li>
      <li>
        <span className="legend-line" /> 红色虚线＝样管由当前槽移入
      </li>
    </ul>
  )
}

function CanonicalKey({ result }) {
  const seq = result.canonical_key
  return (
    <div className="canonical">
      <strong>规范解槽位序列：</strong>
      <span className="canonical-seq">
        [
        {seq.map((entry, i) => (
          <React.Fragment key={i}>
            {i > 0 ? ', ' : ''}
            {entry[0] === 0 ? entry[1] : <em className="empty-slot">(空)</em>}
          </React.Fragment>
        ))}
        ]
      </span>
      <span className="canonical-note">（按槽 0→7 读出；空槽排在任意标识之后）</span>
    </div>
  )
}
