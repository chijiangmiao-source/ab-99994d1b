const SLOTS = [...Array(8).keys()];

/** 样管编辑表：标识、质量、当前槽位、允许槽位（0-7 切换）。 */
export default function TubeEditor({ tubes, onUpdate, onToggleSlot, onRemove, onAdd }) {
  return (
    <div className="tube-editor">
      <table className="editor-table">
        <thead>
          <tr>
            <th>标识</th>
            <th>质量</th>
            <th>当前槽位</th>
            <th className="allowed-col">允许槽位</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {tubes.map((t) => (
            <tr key={t.key}>
              <td>
                <input
                  className="id-input"
                  value={t.id}
                  maxLength={32}
                  onChange={(e) => onUpdate(t.key, { id: e.target.value })}
                />
              </td>
              <td>
                <input
                  className="mass-input"
                  value={t.mass}
                  inputMode="numeric"
                  onChange={(e) => onUpdate(t.key, { mass: e.target.value })}
                />
              </td>
              <td>
                <select
                  value={t.current_slot}
                  onChange={(e) =>
                    onUpdate(t.key, { current_slot: Number(e.target.value) })
                  }
                >
                  {SLOTS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </td>
              <td className="allowed-col">
                <div className="slot-toggles">
                  {SLOTS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      className={
                        "slot-toggle" +
                        (t.allowed_slots.includes(s) ? " on" : "")
                      }
                      onClick={() => onToggleSlot(t.key, s)}
                      title={`允许槽位 ${s}`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </td>
              <td>
                <button
                  type="button"
                  className="remove"
                  onClick={() => onRemove(t.key)}
                  disabled={tubes.length <= 2}
                  title="删除该样管"
                >
                  ×
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        type="button"
        className="add"
        onClick={onAdd}
        disabled={tubes.length >= 8}
      >
        + 添加样管
      </button>
    </div>
  );
}
