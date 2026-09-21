# 高速离心机全局配平审计台

八槽等角转子（槽位 0–7）的**全局最优装载**全栈应用：在 React 页面编辑样管、当前槽位与
允许槽位，由真实 FastAPI 服务在 **Q(√2) 精确数**中穷举比较合力，给出可复算的配平结论，
并在八槽转子图与管槽归属矩阵中展示。

## 优化目标（严格字典序）

1. **最小化合力平方**——所有比较在 Q(√2) = { a + b√2 } 中精确进行，无浮点容差；
2. 在合力最优的方案中，**最少化需要移动的样管数**；
3. 仍同优时取**规范解**：按槽位 0→7 读出的样管标识序列字典序最小，空槽排在任意标识之后。

对满足前两项目标的**全部**同优方案，统计每个“管 × 槽”关系：

- **必然 mandatory**：所有同优方案中该管都在此槽；
- **可选 possible**：部分同优方案如此（规范解会以方框标出其中一种）；
- **不可能 impossible**：同优方案中该管从不会在此槽。

无可行装载时，依据 Hall 婚配定理返回一个**冲突见证**：某个样管子集，其允许槽并集的槽位数
严格少于样管数（例如 3 根管只允许进入 2 个不同槽）。页面输入原样保留并给出明确反馈。

## 为什么是 Q(√2)

槽 k 位于角 kπ/4。将单位向量整体乘以 2 后，各槽方向的分量只含整数与 √2 的整数倍
（如 2·(cos π/4, sin π/4) = (√2, √2)）。合力平方因此是 a + b√2 形式；其 √2 系数一般
非零，不能用整数或浮点近似比较。判定 a + b√2 的符号只需比较整数 a² 与 2b²（√2 无理，
不会误判相等）。枚举至多 8! = 40320 个注入，两趟遍历：第一趟确定最优，第二趟收集全部
前两项同优解以做必然/可选/不可能统计。

## 目录结构

```
backend/          FastAPI 服务（Q(√2) 运算、校验、全枚举求解、Hall 见证）
  app/qsqrt.py      Q(√2) 精确运算：加/减/乘/符号/精确分数渲染
  app/solver.py     输入校验、合力、Hall 见证、枚举优化与关系分类
  app/main.py       /health、/api/meta、/api/solve
  test_solver.py    与独立枚举参考互相校验的差分测试（非镜像内容）
web/              React + Vite 页面，nginx 承载并反代 /api
  src/components/   TubeEditor / RotorDiagram / RelationMatrix
verify/           一次性验收服务，只打真实 HTTP 接口并以退出码报告
docker-compose.yml
```

## 启动（Docker Compose）

```bash
docker compose up --build
```

- 页面： http://localhost:8080
- API： http://localhost:8000 （健康检查 GET /health；页面经 nginx 反代 /api）
- `verify` 服务在 web/api 健康检查通过后自动运行一次真实接口验收后退出，
  查看结果：`docker compose logs verify`；单独重跑：`docker compose run --rm verify`。
  全部通过时退出码为 0，任一断言失败为非零。

宿主机端口可配置（见 `.env.example`）：

```bash
WEB_PORT=18080 API_PORT=18000 docker compose up --build
```

## 本地开发

```bash
# API
python -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn --app-dir backend app.main:app --reload --port 8000

# Web（vite 已配置把 /api、/health 代理到 8000）
cd web && npm install && npm run dev
```

## 接口

- `GET /health` → `{status:"ok", ...}`
- `GET /api/meta` → 槽数、目标说明、关系状态枚举
- `POST /api/solve`，请求体：

```json
{
  "tubes": [
    {"label": "A", "mass": 12, "current_slot": 0, "allowed_slots": [0, 1, 4, 5]}
  ]
}
```

约束：2–8 个样管；标识唯一非空；质量为正整数；当前槽位 0–7 且互异；每管至少一个允许槽。
校验失败返回 422 与 `{message, field}`；无解返回 `feasible:false` 与 `conflict_witness`；
成功时返回精确合力（含 a/b 分子分母与形如 `8-4√2` 的精确字符串）、移动明细、规范键、
逐槽占用与 8 列关系矩阵。
