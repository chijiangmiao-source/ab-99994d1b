const BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

/** 提交配平计算，返回 { status, data }；网络错误会抛出。 */
export async function fetchBalance(tubes) {
  const res = await fetch(`${BASE}/api/v1/balance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tubes }),
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* 保留 null，由调用方按 HTTP 状态处理 */
  }
  return { status: res.status, data };
}
