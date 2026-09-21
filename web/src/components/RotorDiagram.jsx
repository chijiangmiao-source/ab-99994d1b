import React from 'react'

// Eight-slot rotor drawn with slots at angle k*45deg, slot 0 on the right,
// numbered counter-clockwise to match the usual math angle convention used by
// the solver. Slot 3 is top-ish left; labels rotate with the slot.
const SLOT_ANGLE = (s) => s * 45

function slotPosition(slot, radius) {
  const rad = (SLOT_ANGLE(slot) * Math.PI) / 180
  return { x: Math.cos(rad) * radius, y: -Math.sin(rad) * radius }
}

const STATUS_STYLE = {
  mandatory: { fill: '#1b7f4b', stroke: '#0f5132', text: '#ffffff' },
  possible: { fill: '#f1c40f', stroke: '#b8860b', text: '#1f2937' },
  impossible: { fill: '#e9ecef', stroke: '#adb5bd', text: '#6c757d' },
}

export default function RotorDiagram({ slots, placement, relations, currentMap }) {
  const size = 420
  const cx = size / 2
  const cy = size / 2
  const R = 158
  const nodeR = 40

  // relation lookup: tube -> slot status
  const statusFor = new Map()
  if (relations) {
    for (const [tube, rows] of Object.entries(relations)) {
      for (const row of rows) statusFor.set(`${tube}:${row.slot}`, row.status)
    }
  }

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="rotor" role="img" aria-label="八槽转子结果图">
      <circle cx={cx} cy={cy} r={R + 52} fill="#0f172a" opacity="0.04" />
      <circle cx={cx} cy={cy} r={R} fill="#f8fafc" stroke="#94a3b8" strokeWidth="2" />
      <circle cx={cx} cy={cy} r="26" fill="#0f172a" />
      <text x={cx} y={cy + 5} textAnchor="middle" fill="#e2e8f0" fontSize="14">
        转子
      </text>

      {/* spoke guides with slot numbers */}
      {Array.from({ length: 8 }, (_, s) => {
        const p = slotPosition(s, R)
        const outer = slotPosition(s, R + 46)
        return (
          <g key={`spoke-${s}`}>
            <line x1={cx} y1={cy} x2={cx + p.x} y2={cy + p.y} stroke="#cbd5e1" strokeWidth="1" />
            <text
              x={cx + outer.x}
              y={cy + outer.y + 4}
              textAnchor="middle"
              fontSize="13"
              fill="#475569"
              fontWeight="600"
            >
              {s}
            </text>
          </g>
        )
      })}

      {/* movement arcs from current slot to assigned slot */}
      {placement &&
        placement
          .filter((p) => p.moved)
          .map((p) => {
            const a = slotPosition(p.slot, R)
            const b = slotPosition(currentMap.get(p.tube), R)
            const mx = cx + (a.x + b.x) / 2 * 0.72
            const my = cy + (a.y + b.y) / 2 * 0.72
            return (
              <path
                key={`arc-${p.tube}`}
                d={`M ${cx + b.x * 0.82} ${cy + b.y * 0.82} Q ${mx} ${my} ${cx + a.x * 0.82} ${cy + a.y * 0.82}`}
                fill="none"
                stroke="#ef4444"
                strokeWidth="2"
                strokeDasharray="5 4"
              />
            )
          })}

      {slots.map((occupant, s) => {
        const p = slotPosition(s, R)
        const x = cx + p.x
        const y = cy + p.y
        const tube = occupant ? occupant.tube : null
        const status = tube ? statusFor.get(`${tube}:${s}`) : null
        const style = status ? STATUS_STYLE[status] : { fill: '#ffffff', stroke: '#94a3b8', text: '#94a3b8' }
        return (
          <g key={`slot-${s}`}>
            <circle cx={x} cy={y} r={nodeR} fill={style.fill} stroke={style.stroke} strokeWidth="2.5" />
            {occupant ? (
              <>
                <text x={x} y={y - 3} textAnchor="middle" fontSize="17" fontWeight="700" fill={style.text}>
                  {occupant.tube}
                </text>
                <text x={x} y={y + 15} textAnchor="middle" fontSize="12" fill={style.text}>
                  m={occupant.mass}
                </text>
              </>
            ) : (
              <text x={x} y={y + 4} textAnchor="middle" fontSize="13" fill={style.text}>
                空
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}
