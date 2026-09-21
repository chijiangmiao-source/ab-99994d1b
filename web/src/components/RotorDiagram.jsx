const CX = 190;
const CY = 190;
const R_SLOT = 112;   // 槽位圆心半径
const R_LABEL = 152;  // 槽位编号半径
const R_TUBE = 27;    // 槽位圆半径

function polar(k, r) {
  const a = (k * Math.PI) / 4; // 槽位 k 位于 k*45°，逆时针
  return { x: CX + r * Math.cos(a), y: CY - r * Math.sin(a) };
}

/** 八槽转子图：规范解的槽位占用、移动标记与合力方向。 */
export default function RotorDiagram({ slots, assignment, force, resultantExact }) {
  const bySlot = new Map(assignment.map((a) => [a.slot, a]));

  // 力分量仅用于方向展示（精确值以文本形式给出）
  const fx = (force.x.a + force.x.b * Math.SQRT2) / force.x.scale;
  const fy = (force.y.a + force.y.b * Math.SQRT2) / force.y.scale;
  const mag = Math.hypot(fx, fy);
  const LEN = 64;
  const dx = mag > 0 ? (fx / mag) * LEN : 0;
  const dy = mag > 0 ? (fy / mag) * LEN : 0;

  return (
    <div className="rotor">
      <svg viewBox="0 0 380 380" role="img" aria-label="八槽转子图">
        <defs>
          <marker
            id="arrowhead"
            markerWidth="8"
            markerHeight="8"
            refX="6"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L6,3 L0,6 Z" fill="#c0392b" />
          </marker>
        </defs>

        <circle cx={CX} cy={CY} r={R_LABEL + 12} className="rotor-rim" />
        <circle cx={CX} cy={CY} r={R_SLOT} className="rotor-ring" />

        {slots.map(({ slot }) => {
          const p = polar(slot, R_SLOT);
          return (
            <line
              key={`spoke-${slot}`}
              x1={CX}
              y1={CY}
              x2={p.x}
              y2={p.y}
              className="spoke"
            />
          );
        })}

        {mag > 0 ? (
          <line
            x1={CX}
            y1={CY}
            x2={CX + dx}
            y2={CY - dy}
            className="force-arrow"
            markerEnd="url(#arrowhead)"
          />
        ) : (
          <circle cx={CX} cy={CY} r={7} className="force-zero" />
        )}
        <circle cx={CX} cy={CY} r={3} className="hub" />

        {slots.map(({ slot, tube }) => {
          const p = polar(slot, R_SLOT);
          const l = polar(slot, R_LABEL);
          const a = tube ? bySlot.get(slot) : null;
          const cls = a ? (a.moved ? "slot moved" : "slot kept") : "slot empty";
          return (
            <g key={slot}>
              <circle cx={p.x} cy={p.y} r={R_TUBE} className={cls} />
              {a ? (
                <>
                  <text x={p.x} y={p.y - 2} className="tube-id">
                    {a.tube}
                  </text>
                  <text x={p.x} y={p.y + 13} className="tube-mass">
                    m={a.mass}
                  </text>
                </>
              ) : (
                <text x={p.x} y={p.y + 4} className="empty-mark">
                  空
                </text>
              )}
              <text x={l.x} y={l.y + 4} className="slot-no">
                {slot}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="legend">
        <span><i className="dot kept" /> 未移动</span>
        <span><i className="dot moved" /> 已移动</span>
        <span><i className="dot empty" /> 空槽</span>
        <span><i className="dot force" /> 合力方向 |F|² = {resultantExact}</span>
      </div>
    </div>
  );
}
