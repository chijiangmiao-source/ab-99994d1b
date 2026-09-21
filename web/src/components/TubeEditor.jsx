import React from 'react'

const SLOTS = Array.from({ length: 8 }, (_, s) => s)

export default function TubeEditor({ tubes, onChange, errorField }) {
  const update = (index, patch) => {
    onChange(tubes.map((t, i) => (i === index ? { ...t, ...patch } : t)))
  }

  const toggleAllowed = (index, slot) => {
    const t = tubes[index]
    const has = t.allowed_slots.includes(slot)
    const next = has
      ? t.allowed_slots.filter((s) => s !== slot)
      : [...t.allowed_slots, slot].sort((a, b) => a - b)
    update(index, { allowed_slots: next })
  }

  const removeTube = (index) => {
    if (tubes.length <= 2) return
    onChange(tubes.filter((_, i) => i !== index))
  }

  const addTube = () => {
    if (tubes.length >= 8) return
    const used = new Set(tubes.map((t) => t.label))
    let label = 'T'
    for (let i = tubes.length + 1; ; i++) {
      const candidate = `T${i}`
      if (!used.has(candidate)) {
        label = candidate
        break
      }
    }
    const usedSlots = new Set(tubes.map((t) => t.current_slot))
    const cs = SLOTS.find((s) => !usedSlots.has(s)) ?? 0
    onChange([
      ...tubes,
      { label, mass: 1, current_slot: cs, allowed_slots: SLOTS.slice() },
    ])
  }

  const fieldErr = (path) =>
    errorField && (errorField === path || errorField.startsWith(path + '.'))

  return (
    <div className="editor">
      <div className="editor-head">
        <span>
          样管清单（{tubes.length}/8，至少 2 个；标识唯一、质量为正整数、当前槽位互异）
        </span>
        <button type="button" className="btn btn-secondary" onClick={addTube} disabled={tubes.length >= 8}>
          ＋ 新增样管
        </button>
      </div>
      <div className="tube-rows">
        {tubes.map((t, i) => (
          <div className={`tube-card ${fieldErr(`tubes[${i}]`) ? 'has-error' : ''}`} key={i}>
            <div className="tube-card-head">
              <div className="field">
                <label>标识</label>
                <input
                  type="text"
                  value={t.label}
                  onChange={(e) => update(i, { label: e.target.value })}
                  className={`input ${fieldErr(`tubes[${i}].label`) ? 'input-error' : ''}`}
                />
              </div>
              <div className="field field-mass">
                <label>质量</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={t.mass}
                  onChange={(e) => update(i, { mass: e.target.value })}
                  className={`input ${fieldErr(`tubes[${i}].mass`) ? 'input-error' : ''}`}
                />
              </div>
              <div className="field">
                <label>当前槽位</label>
                <select
                  value={t.current_slot}
                  onChange={(e) => update(i, { current_slot: Number(e.target.value) })}
                  className={`input ${fieldErr(`tubes[${i}].current_slot`) ? 'input-error' : ''}`}
                >
                  {SLOTS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                className="btn btn-remove"
                onClick={() => removeTube(i)}
                disabled={tubes.length <= 2}
                title="删除该样管（至少保留 2 个）"
              >
                删除
              </button>
            </div>
            <div className="field">
              <label>允许槽位（可多选，至少 1 个）</label>
              <div className={`slot-toggles ${fieldErr(`tubes[${i}].allowed_slots`) ? 'toggles-error' : ''}`}>
                {SLOTS.map((s) => {
                  const on = t.allowed_slots.includes(s)
                  const isCurrent = t.current_slot === s
                  return (
                    <button
                      type="button"
                      key={s}
                      className={`slot-toggle ${on ? 'on' : 'off'} ${isCurrent ? 'is-current' : ''}`}
                      onClick={() => toggleAllowed(i, s)}
                      title={isCurrent ? `槽 ${s}（当前槽位）` : `槽 ${s}`}
                    >
                      {s}
                      {isCurrent && <span className="current-dot" aria-hidden="true" />}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
