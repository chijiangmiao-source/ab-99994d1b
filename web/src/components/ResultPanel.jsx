import RotorDiagram from "./RotorDiagram.jsx";
import AssignmentMatrix from "./AssignmentMatrix.jsx";

/** 最优解结果：目标值、转子图、归属矩阵、分配明细。 */
export default function ResultPanel({ result }) {
  const { objectives, force, assignment, slots, relations } = result;
  const rs = objectives.resultant_squared;

  return (
    <section className="card">
      <div className="card-title">
        <h2>全局配平结论</h2>
        <span className="badge ok">可配平</span>
      </div>

      <div className="summary">
        <div className="metric">
          <div className="metric-label">合力平方 |F|²（精确）</div>
          <div className="metric-value mono">{rs.exact}</div>
          <div className="metric-sub mono">
            = ({rs.p} {rs.q < 0 ? "−" : "+"} {Math.abs(rs.q)}·√2) / {rs.scale}
            {rs.approx != null && <> ≈ {rs.approx.toPrecision(8)}</>}
          </div>
        </div>
        <div className="metric">
          <div className="metric-label">移动样管数</div>
          <div className="metric-value">{objectives.moves}</div>
          <div className="metric-sub">第二目标最小值</div>
        </div>
        <div className="metric">
          <div className="metric-label">前两目标同优方案</div>
          <div className="metric-value">{objectives.optimal_count}</div>
          <div className="metric-sub">关系标注基于此集合</div>
        </div>
      </div>

      <div className="panels">
        <RotorDiagram
          slots={slots}
          assignment={assignment}
          force={force}
          resultantExact={rs.exact}
        />
        <AssignmentMatrix assignment={assignment} relations={relations} />
      </div>

      <h3>分配明细（规范解）</h3>
      <table className="assign-table">
        <thead>
          <tr>
            <th>样管</th>
            <th>质量</th>
            <th>当前槽位</th>
            <th>目标槽位</th>
            <th>是否移动</th>
          </tr>
        </thead>
        <tbody>
          {assignment.map((a) => (
            <tr key={a.tube}>
              <td className="mono">{a.tube}</td>
              <td className="mono">{a.mass}</td>
              <td className="mono">{a.current_slot}</td>
              <td className="mono">{a.slot}</td>
              <td>{a.moved ? <span className="badge moved">移动</span> : <span className="badge kept">保持</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
