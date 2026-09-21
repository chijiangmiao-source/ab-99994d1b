import React from 'react'

const STATUS = {
  mandatory: { label: '必然', cls: 'rel-mandatory', symbol: '●' },
  possible: { label: '可选', cls: 'rel-possible', symbol: '◐' },
  impossible: { label: '不可能', cls: 'rel-impossible', symbol: '·' },
}

// Tube x slot ownership matrix over every solution tied on the first two
// objectives (minimum resultant, then minimum moves).
export default function RelationMatrix({ relations, tubes, assignment, totalOptimal, highlightTube }) {
  const labels = tubes.map((t) => t.label)
  const currentByLabel = new Map(tubes.map((t) => [t.label, t.current_slot]))
  const assignedByLabel = new Map(
    (assignment || []).map((p) => [p.tube, p.slot]),
  )

  return (
    <div className="matrix-wrap">
      <table className="relation-matrix">
        <thead>
          <tr>
            <th className="corner">
              管 \ 槽
              <div className="corner-sub">（当前 → 规范解）</div>
            </th>
            {Array.from({ length: 8 }, (_, s) => (
              <th key={s} className="slot-head">
                {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {labels.map((label) => {
            const rows = relations[label] || []
            const cur = currentByLabel.get(label)
            const assigned = assignedByLabel.get(label)
            return (
              <tr key={label} className={highlightTube === label ? 'row-hot' : ''}>
                <th className="tube-head">
                  <span className="tube-name">{label}</span>
                  <span className="tube-route">
                    {cur}
                    <span className="arrow"> → </span>
                    {assigned === undefined ? '—' : assigned}
                    {assigned !== undefined && assigned !== cur && <span className="moved-tag">移</span>}
                  </span>
                </th>
                {rows.map((cell) => {
                  const meta = STATUS[cell.status]
                  const isAssigned = assigned === cell.slot
                  return (
                    <td
                      key={cell.slot}
                      className={`rel-cell ${meta.cls} ${isAssigned ? 'is-assigned' : ''}`}
                      title={`管 ${label} → 槽 ${cell.slot}：${meta.label}；在 ${cell.occurrences}/${totalOptimal} 个前两项同优方案中出现`}
                    >
                      <span className="rel-symbol">{meta.symbol}</span>
                      {isAssigned && <span className="assigned-ring" aria-hidden="true" />}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
      <ul className="legend">
        {Object.entries(STATUS).map(([key, meta]) => (
          <li key={key}>
            <span className={`legend-swatch ${meta.cls}`}>{meta.symbol}</span>
            <strong>{meta.label}</strong>
            {key === 'mandatory' && '：前两项目标同优的所有方案中，该管必在此槽'}
            {key === 'possible' && '：部分最优方案中在此槽，可任选'}
            {key === 'impossible' && '：任何最优方案中该管都不会在此槽'}
          </li>
        ))}
      </ul>
    </div>
  )
}
