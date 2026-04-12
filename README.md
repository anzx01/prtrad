# Polymarket Tail Risk Console

用于研究、准入、风控、影子运行与上线评审的 Polymarket 尾部风险控制台。

当前项目的核心目标不是做一组分散页面，而是打通这条业务主链路：

`市场数据 -> 数据质量 DQ -> 标签分类 -> 人工审核 -> NetEV / 校准 -> 组合风控 -> 回测 -> 影子运行 -> 上线评审`

## 当前里程碑

- `M1`：数据接入与 DQ 基础
- `M2`：标签分类、审核队列、基础报表
- `M3`：校准单元与 NetEV 准入
- `M4`：组合风控、状态机、Kill-switch、阈值维护
- `M5`：回测实验室、日报、周报、阶段评审
- `M6`：影子运行、上线前门槛、Go/NoGo
- `M7`：本轮暂不实施

## 项目结构

```text
prtrad/
├─ apps/
│  ├─ api/                 # FastAPI 后端
│  │  ├─ app/              # 路由与应用入口
│  │  ├─ db/               # SQLAlchemy 模型与 Alembic
│  │  └─ services/         # 业务服务层
│  └─ web/                 # Next.js 前端
├─ docs/                   # 正式文档与开发进度
├─ scripts/                # 统一脚本入口（PowerShell 优先）
├─ tests/                  # 测试
└─ workers/                # Celery Worker 与调度任务
```

## 本地启动

1. 安装依赖

```powershell
npm install
```

2. 初始化环境

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

3. 升级数据库

```powershell
npm run db:upgrade
```

4. 启动开发环境

```powershell
npm run dev
```

启动后默认地址：

- Web：`http://localhost:3000`
- API：`http://localhost:8000`
- API Docs：`http://localhost:8000/docs`

如果前端提示连不上 API，先检查：

```powershell
Invoke-RestMethod http://localhost:8000/health
```

## 常用命令

开发：

```powershell
npm run dev
npm run dev:web
npm run dev:api
npm run dev:worker
npm run dev:beat
npm run build:web
```

数据库：

```powershell
npm run db:upgrade
npm run db:downgrade
npm run db:current
```

任务触发：

```powershell
npm run task:market-sync
npm run task:snapshot-sync
npm run task:dq-run
npm run task:tagging-run
npm run health:dq
```

测试：

```powershell
npm run test:risk
npm run test:m456
npm run test:worker
python -m pytest -q
```

## 页面路由

- `/`：智能驾驶舱首页
- `/markets`：市场总表
- `/dq`：数据质量看板
- `/tagging`：标签分类
- `/review`：人工审核队列（支持单条与批量审核）
- `/lists`：名单管理
- `/monitoring`：系统监控
- `/tag-quality`：标签质量
- `/reports`：日报、周报、阶段评审智能速读
- `/calibration`：校准单元
- `/netev`：NetEV 准入
- `/risk`：组合风控
- `/state-alerts`：状态与告警
- `/backtests`：回测实验室
- `/launch-review`：影子运行与上线评审

## 智能驾驶舱首页

根路径 `/` 已从静态导航页改造成“智能驾驶舱”。

首页会自动并行汇总：

- `/monitoring/metrics`
- `/dq/summary`
- `/review/queue`
- `/risk/state`
- `/risk/exposures`
- `/risk/kill-switch?status=pending`
- `/calibration/units?include_inactive=true`
- `/backtests`
- `/shadow`
- `/launch-review`
- `/reports`

首页会直接给出三类结果：

- 系统当前判断：告诉你真正卡在哪里
- 下一步建议：把最值得现在处理的动作排在前面
- 主链路状态：把 DQ、审核、校准、风险、上线门槛、报告归档按工作流展示

首页支持的一键自动化动作：

- 重算风险暴露
- 重算长窗口校准
- 运行回测
- 运行影子运行
- 生成日报
- 生成周报
- 生成 `M4 / M5 / M6` 阶段评审
- 一键刷新完整证据包

说明：

- 自动化动作按顺序串行执行，避免并发写库
- 遇到 SQLite 偶发 `database is locked` 时，会做有限次短重试
- 审核队列这类必须人工处理的事情不会被假装自动化，首页会明确标记这是当前人工瓶颈

## 最近排障要点

### 1. DQ `pass=0`

- 典型原因不是前端坏了，而是快照链路陈旧，导致命中 `DQ_SNAPSHOT_STALE`
- 现在已补齐：
  - `capture_snapshots` 容错增强
  - `book_fetch_failed_tokens`
  - source payload 降级快照
  - `/dq` 页面快照抓取诊断
  - `npm run health:dq`

### 2. Calibration Units 全是 0

- 先查 recent closed/resolved market 是否真的同步进库
- 再查 calibration 重算是否真的执行
- 当前系统已补齐：
  - recent closed/resolved 扫描
  - `final_resolution` 回填
  - 从 `outcomePrices` 回退推断历史 resolved 样本

### 3. Review Queue `pending=0`

- 先不要直接怀疑前端
- 更常见原因是 tagging 自动分类最近没有持续产出 `ReviewRequired/Blocked`
- 先查：

```powershell
Invoke-RestMethod "http://localhost:8000/review/queue?queue_status=pending&page=1&page_size=5"
Invoke-RestMethod "http://localhost:8000/monitoring/metrics"
```

- 必要时手动补跑：

```powershell
npm run task:tagging-run
```

### 4. Launch Review 里 Go 被禁用

- `Create Review` 成功，不等于 checklist 已全部通过
- 如果 `Go` 被禁用，通常说明 backtest / shadow / stage review / kill-switch 证据还没满足门槛
- 这表示证据链未通过，不表示页面点击失效

## 关键文档

- 开发进度：[docs/dev-progress.md](docs/dev-progress.md)
- Tagging 默认基线：[docs/tagging/default-bootstrap-v1.md](docs/tagging/default-bootstrap-v1.md)
- v4 研究 PRD：`polymarket_tail_risk_system_v4_research_prd.md`

## 协作约定

- 默认使用中文沟通与文档
- 文本文件统一 UTF-8，优先无 BOM
- 运行、调试、测试优先走 `scripts/` 或仓库脚本
- 新功能默认补齐自动化验证
- 每日收工前更新 `docs/dev-progress.md`
