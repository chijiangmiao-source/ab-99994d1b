// Typed-ish client for the FastAPI backend. No response values are parsed as
// floats: the objective numbers are exact strings produced in Q(sqrt(2)).

export async function fetchMeta() {
  const res = await fetch('/api/meta')
  if (!res.ok) throw new Error(`元数据请求失败：HTTP ${res.status}`)
  return res.json()
}

export async function solve(tubes) {
  const res = await fetch('/api/solve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tubes }),
  })
  let body = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON error page */
  }
  if (!res.ok) {
    const detail = body && body.detail
    const message =
      (detail && (detail.message || (Array.isArray(detail) ? JSON.stringify(detail) : String(detail)))) ||
      `计算请求失败：HTTP ${res.status}`
    const field = detail && detail.field
    const error = new Error(message)
    error.field = field
    error.status = res.status
    throw error
  }
  return body
}
