const SLOTS = [...Array(8).keys()];

const STATUS_TEXT = {
  necessary: "必",
  optional: "可",
  impossible: "×",
};

const STATUS_TITLE = {
  necessary: "必然：所有前两目标同优的方案都占用此槽",
  optional: "可选：部分同优方案占用此槽",
  impossible: "不可能：任何同优方案都不占用此槽",
};

/** 归属矩阵：样管 × 槽位，标注必然/可选/不可能，以及规范解与当前槽。 */
export default function AssignmentMatrix({ assignment, relations }) {
  const relMap = new Map(relations.map((r) => [`${r.tube}:${r.slot}`, r]));
  const assigned = new Map(assignment.map((a) => [a.tube, a.slot]));

  return (
    <div className="matrix">
      <table className="matrix-table">
        <thead>
          <tr>
            <th>样管＼槽位</th>
            {SLOTS.map((s) => (
              <th key={s}>{s}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {assignment.map((a) => (
            <tr key={a.tube}>
              <th>
                {a.tube}
                <span className="muted"> (m={a.mass})</span>
              </th>
              {SLOTS.map((s) => {
                const rel = relMap.get(`${a.tube}:${s}`);
                const isAssigned = assigned.get(a.tube) === s;
                const isCurrent = a.current_slot === s;
                if (!rel?.allowed) {
                  return (
                    <td key={s} className="cell na" title="不在允许槽位内">
                      —
                    </td>
                  );
                }
                return (
                  <td
                    key={s}
                    className={`cell ${rel.status}${isAssigned ? " assigned" : ""}`}
                    title={STATUS_TITLE[rel.status]}
                  >
                    <span className="mark">{STATUS_TEXT[rel.status]}</span>
                    {isAssigned && <span className="canon">●</span>}
                    {isCurrent && <span className="cur">当</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="legend">
        <span><i className="sw nec" /> 必然</span>
        <span><i className="sw opt" /> 可选</span>
        <span><i className="sw imp" /> 不可能</span>
        <span><i className="sw na" /> 不允许</span>
        <span>● 规范解</span>
        <span>当 当前槽位</span>
      </div>
    </div>
  );
}
