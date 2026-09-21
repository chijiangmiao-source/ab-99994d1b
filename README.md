# 离心机转子配平审计台

八槽高速离心机的全栈配平审计系统。实验员在 React 页面编辑样管（标识、质量、
当前槽位、允许槽位），经 FastAPI 真实接口计算全局配平结论，并在八槽转子图与
归属矩阵中查看：合力最小的装载方案、每支样管是否移动、以及在"前两项目标同优"
的全部方案中每个管槽关系是**必然**、**可选**还是**不可能**。

## 问题与算法

- 转子固定 8 个等角槽位，编号 0–7，槽位 k 位于角度 k·45°。
- 每批 2–8 支样管：标识唯一、质量为正整数、当前槽位互异。
- 每管必须进入一个允许槽，槽位不得复用（双射约束）。
- 目标顺序（字典序）：
  1. **最小化合力**：在 **Q(√2)** 中精确比较合力平方 `4·|F|² = P + Q·√2`
     （P、Q 为整数，全程整数运算，**不使用任何浮点容差**）；
  2. **最少移动样管数**；
  3. **规范解**：同优方案按槽位 0–7 上的样管标识序列取字典序最小，
     空槽排在任意标识之后。
- 对所有达到前两项最优的方案，标注每个 (样管, 槽位) 关系：
  `necessary`（必然）/ `optional`（可选）/ `impossible`（不可能）。
- **无可行装载**时返回霍尔冲突见证：一个样管集合 S 及其允许槽并集 N(S)，
  满足 |N(S)| < |S|（由最大匹配的交错路构造）。页面保留原输入并明确反馈。

### 精确数表示

槽位 k 的单位矢量放大 2 倍后系数全为整数：`2·(cos θk, sin θk) = (ax+bx·√2, ay+by·√2)`。
于是双倍合力 `2F = (Ax+Bx·√2, Ay+By·√2)`，且

```
4·|F|² = P + Q·√2，  P = Ax² + 2Bx² + Ay² + 2By²，  Q = 2(AxBx + AyBy)
```

两个形如 `P + Q·√2` 的数通过整数符号判定精确比较（`api/app/solver.py: cmp_pq`）。
验收用例包含 Pell 构造的近邻情形：两个候选方案的 `4·|F|²` 之差的 float64
表示完全相同（`1000000000054.0`），但精确值不同——任何浮点容差比较都会答错。

## 快速开始（Docker）

```bash
docker compose up --build        # 启动 api + web（verify 运行一次后自动退出）
# 浏览器打开 http://localhost:8080
```

宿主机端口可配置（默认 API 8000、Web 8080）：

```bash
cp .env.example .env             # 修改 API_PORT / WEB_PORT
API_PORT=9000 WEB_PORT=9090 docker compose up --build
```

健康检查：

- API：`GET http://localhost:8000/healthz`（容器内亦配置 HEALTHCHECK）
- Web：`GET http://localhost:8080/healthz`（nginx 直接应答）

### 一次性验收服务 verify

`verify` 是 Compose 中的一次性服务：等待 api、web 健康后，对**真实运行的接口**
（直连 API 与经 Web 反向代理的全链路）执行约 80 项验收——期望值由脚本内置的
独立精确枚举重新计算——随后自行退出，**以退出码报告结果**（0 通过 / 1 失败）。

```bash
docker compose up --build -d api web     # 先起服务
docker compose run --rm verify           # 运行验收；echo $? 查看退出码
# 或一条命令（verify 退出时连带停止栈）：
docker compose up --build --exit-code-from verify verify
```

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/healthz` | 健康检查 |
| GET | `/api/v1/meta` | 转子参数与目标顺序 |
| POST | `/api/v1/balance` | 配平计算（详见下） |
| GET | `/docs` | Swagger UI（交互式接口文档） |

### POST /api/v1/balance

请求：

```json
{
  "tubes": [
    {"id": "A", "mass": 12, "current_slot": 0, "allowed_slots": [0, 1, 4, 5]},
    {"id": "B", "mass": 12, "current_slot": 4, "allowed_slots": [0, 4]}
  ]
}
```

可配平时 `status = "optimal"`：

- `objectives.resultant_squared`：`{p, q, scale, exact, approx}`，
  精确含义 `|F|² = (p + q·√2)/scale`（`exact` 为约分后的精确字符串，
  `approx` 仅供展示）；
- `objectives.moves`：最少移动数；`objectives.optimal_count`：前两目标同优方案数；
- `assignment`：规范解（每管的槽位、是否移动）；`slots`：槽位 → 样管映射；
- `force`：双倍合力的精确系数 `2F = (a + b·√2)/scale`；
- `relations`：全部 管×槽 关系的 `necessary` / `optional` / `impossible` 标注
  （含 `allowed` 标记）。

不可行时 `status = "infeasible"`，返回霍尔冲突见证：

```json
{
  "status": "infeasible",
  "witness": {
    "tubes": ["A", "B", "C"],
    "allowed_union": [1, 2],
    "tube_count": 3,
    "slot_count": 2,
    "explanation": "3 支样管的允许槽位并集只有 2 个，霍尔条件不满足，无可行装载"
  }
}
```

输入非法（管数不在 2–8、标识重复、当前槽位冲突、质量非正整数、槽位越界等）
返回 **422** 及逐条错误明细；页面保留原输入。

## 本地开发

```bash
# API（Python 3.11+）
cd api && pip install -r requirements.txt
uvicorn app.main:app --reload          # http://127.0.0.1:8000
python -m pytest tests/ -q             # 求解器单元测试（含随机对拍）

# Web（Node 20+）
cd web && npm install
npm run dev                            # http://127.0.0.1:5173（已代理 /api）

# 验收（需 API 已启动；Web 基址可选）
API_BASE=http://127.0.0.1:8000 WEB_BASE=http://127.0.0.1:8080 python verify/verify.py
```

## 目录结构

```
├── docker-compose.yml      # api + web + verify（一次性验收）
├── .env.example            # 可配置宿主机端口
├── api/                    # FastAPI 后端
│   ├── app/solver.py       # Q(√2) 精确求解器、规范解、关系标注、霍尔见证
│   ├── app/models.py       # 批次校验（2-8 管、标识唯一、槽位互异、正整数质量）
│   ├── app/main.py         # 路由：/healthz、/api/v1/meta、/api/v1/balance
│   └── tests/              # pytest：精确比较、规范解、见证、随机对拍
├── web/                    # React + Vite 前端，nginx 托管并反代 /api
│   └── src/components/     # 编辑器、八槽转子图、归属矩阵、结果/见证面板
└── verify/                 # 一次性验收服务（仅标准库，退出码报告结果）
```
