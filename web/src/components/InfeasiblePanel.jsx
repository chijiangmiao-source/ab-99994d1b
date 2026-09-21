/** 不可行装载：展示霍尔冲突见证，输入保留在编辑区。 */
export default function InfeasiblePanel({ witness }) {
  return (
    <section className="card alert-error">
      <div className="card-title">
        <h2>无可行装载</h2>
        <span className="badge bad">霍尔冲突</span>
      </div>
      <p>{witness.explanation}</p>
      <div className="witness">
        <div>
          <div className="metric-label">冲突样管集（{witness.tube_count} 支）</div>
          <div className="chips">
            {witness.tubes.map((t) => (
              <span key={t} className="chip tube">{t}</span>
            ))}
          </div>
        </div>
        <div>
          <div className="metric-label">允许槽位并集（仅 {witness.slot_count} 个）</div>
          <div className="chips">
            {witness.allowed_union.map((s) => (
              <span key={s} className="chip slot">{s}</span>
            ))}
            {witness.allowed_union.length === 0 && <span className="muted">（空集）</span>}
          </div>
        </div>
      </div>
      <p className="mono witness-formula">
        |允许槽并集| = {witness.slot_count} &lt; {witness.tube_count} = |样管集|
      </p>
      <p className="muted">
        原始输入已保留在上方编辑区，请调整允许槽位或批次后重新计算。
      </p>
    </section>
  );
}
