# Polymarket Tail Risk Web App

用于研究、准入、风控、影子运行与上线评审的 Polymarket 尾部风险控制台。

当前主链路目标：
`市场数据 -> 数据质量(DQ) -> 标签分类 -> 人工审核 -> 评分/NetEV -> 组合风控 -> 回测报告 -> 影子运行 -> 上线评审`

## 当前里程碑

- M1：数据接入与 DQ 基础
- M2：标签分类、审核队列、报表基础
- M3：校准单元与 NetEV 准入
- M4：组合风控、状态机、kill-switch、阈值维护
- M5：回测实验室、日报/周报/阶段评审报告
- M6：影子运行、上线门槛检查与 Go/NoGo
- M7：本轮暂不实施

## 项目结构

```text
prtrad/
├─ apps/
│  ├─ api/                   # FastAPI 后端
│  │  ├─ app/                # 路由与应用入口
│  │  ├─ db/                 # SQLAlchemy 模型与 Alembic 迁移
│  │  └─ services/           # 业务服务层
│  └─ web/                   # Next.js 前端
├─ docs/                     # 正式文档与开发进度
├─ scripts/                  # 统一脚本入口（PowerShell 优先）
├─ tests/                    # 单元与集成测试
└─ workers/                  # Celery Worker 与任务
```

## 本地启动

1. 安装依赖

```powershell
npm install
```

2. 初始化环境

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/bootstrap.ps1
```

3. 升级数据库

```powershell
npm run db:upgrade
```

4. 启动开发服务

```powershell
npm run dev
```

启动后：

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

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
```

自动化测试：

```powershell
npm run test:risk      # M4 风控回归
npm run test:m456      # M4-M6 回归 + Web TypeScript 检查
npm run test:worker    # Worker 任务烟测
python -m pytest -q    # 全量 pytest
```

## 页面路由

- `/markets`：市场列表
- `/dq`：数据质量看板
- `/tagging`：标签分类
- `/review`：审核队列
- `/lists`：名单管理
- `/monitoring`：系统监控
- `/tag-quality`：标签质量
- `/reports`：日报/周报/阶段评审
- `/calibration`：校准单元
- `/netev`：NetEV 准入
- `/risk`：组合风控主面板
- `/state-alerts`：状态机与告警
- `/backtests`：回测实验室
- `/launch-review`：影子运行与上线评审

## 近期排障说明（2026-04-10）

### DQ `pass=0` 排查结论

- 症状：`/dq` 看板 `pass=0`
- 根因链路：CLOB 快照抓取失败导致快照陈旧，DQ 命中 `DQ_SNAPSHOT_STALE`
- 已落地修复：
  - `capture_snapshots` 增强容错（批次失败不再拖垮整批）
  - 新增 `book_fetch_failed_tokens` 指标
  - 新增 source payload 降级快照（默认开启，开关见下）
  - 新增自动化测试覆盖降级与容错

### 新增配置

- `INGEST_ALLOW_SOURCE_PAYLOAD_FALLBACK`（默认 `true`）
  - 当 CLOB 拉取失败时，允许使用 `markets.source_payload.market` 构建降级快照，避免 DQ 全量 stale

## 关键文档

- 开发进度：`docs/dev-progress.md`
- Tagging 默认基线：`docs/tagging/default-bootstrap-v1.md`
- v4 研究 PRD：`polymarket_tail_risk_system_v4_research_prd.md`

## 协作约定

- 默认中文沟通与文档
- 文本文件统一 UTF-8（优先无 BOM）
- 优先通过 `scripts/` 执行运行/调试/测试
- 新功能默认补齐自动化测试
- 每日收工前更新 `docs/dev-progress.md`
