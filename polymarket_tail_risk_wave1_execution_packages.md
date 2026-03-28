# Polymarket Tail Risk Wave 1 执行包
## 面向 `PLAT + DATA` 的首批开发拆分（可直接分发给 Codex/Claude Code）

---

# 1. 目标

本执行包覆盖 `M1-M2` 中最先落地的主链路任务，优先跑通：

1. 工程骨架与运行底座
2. 数据库核心模型
3. 市场与快照采集
4. 数据质量规则
5. 审计与调度闭环
6. M2 起步所需标签规则底座

---

# 2. Wave 1 范围（任务映射）

来自 Backlog 的任务：

- `PLAT`：`M1-001`, `M1-006`, `M1-008`
- `DATA`：`M1-002`, `M1-003`, `M1-004`, `M1-005`
- `RISK`（仅起步）：`M2-001`

不在本 Wave 范围：

- 页面开发（`M1-009`, `M2-006`, `M2-007`）
- 回测与报告（M3+）

---

# 3. 并行与依赖图

执行顺序建议：

1. `PKG-PLAT-01`（先做）
2. `PKG-DATA-01`（依赖 PLAT-01）
3. `PKG-PLAT-02`（可与 DATA-01 并行）
4. `PKG-DATA-02`（依赖 DATA-01）
5. `PKG-DATA-03`（依赖 DATA-02）
6. `PKG-PLAT-03`（依赖 PLAT-01，可并行于 DATA-02/03）
7. `PKG-RISK-01`（依赖 DATA-01 与 PLAT-03）

---

# 4. 执行包定义

## PKG-PLAT-01 工程骨架与规范

- 关联任务：`M1-001`
- 负责人泳道：`PLAT`
- 优先级：`P0`
- 依赖：无
- 写入范围建议：
1. `apps/web/`
2. `apps/api/`
3. `workers/`
4. `infra/`
5. `docs/`

### 交付物

1. 前后端与 worker 基础目录骨架
2. 本地开发环境启动方案
3. 统一配置加载规范
4. 日志字段规范文档
5. 环境变量清单文档

### DoD

1. 本地可启动最小系统（web/api/worker）
2. 模块配置加载路径统一
3. 日志字段包含 request_id/task_id/rule_version

---

## PKG-DATA-01 数据库 Schema v1

- 关联任务：`M1-002`
- 负责人泳道：`DATA`
- 优先级：`P0`
- 依赖：`PKG-PLAT-01`
- 写入范围建议：
1. `apps/api/db/migrations/`
2. `apps/api/db/models/`
3. `docs/schema/`

### 交付物

1. 核心实体建表迁移脚本
2. 索引与约束定义
3. 表关系说明文档

### DoD

1. 核心表可建库与回滚
2. 关键查询索引可用
3. 表设计可支撑 Market/Snapshot/DQ/DecisionLog

---

## PKG-PLAT-02 任务调度底座

- 关联任务：`M1-006`
- 负责人泳道：`PLAT`
- 优先级：`P0`
- 依赖：`PKG-PLAT-01`
- 写入范围建议：
1. `workers/`
2. `infra/`
3. `docs/runbooks/`

### 交付物

1. Celery worker 与 beat 调度配置
2. 任务重试策略
3. 幂等键约定
4. 死信/失败任务处理说明

### DoD

1. 定时任务可自动触发
2. 失败任务可重试
3. 重复调度不会导致重复写入

---

## PKG-DATA-02 市场与快照采集

- 关联任务：`M1-003`, `M1-004`
- 负责人泳道：`DATA`
- 优先级：`P0`
- 依赖：`PKG-DATA-01`, `PKG-PLAT-02`
- 写入范围建议：
1. `workers/tasks/ingest/`
2. `apps/api/services/ingest/`
3. `docs/data-sources/`

### 交付物

1. 市场元数据增量采集任务
2. 价格与流动性快照采集任务
3. 去重与更新时间策略
4. 采样频率配置

### DoD

1. 可按计划稳定拉取数据
2. 市场和快照可持续入库
3. 失败任务可重试并留痕

---

## PKG-DATA-03 数据质量规则引擎 v1

- 关联任务：`M1-005`
- 负责人泳道：`DATA`
- 优先级：`P0`
- 依赖：`PKG-DATA-02`
- 写入范围建议：
1. `workers/tasks/dq/`
2. `apps/api/services/dq/`
3. `docs/dq/`

### 交付物

1. DQ 规则（缺失/过期/异常/重复/时间逻辑）
2. DQ 结果表与评分逻辑
3. DQ 告警产出

### DoD

1. 每个市场可得到 DQ 状态
2. DQ 失败可被下游识别并屏蔽
3. DQ 结果与规则版本可追溯

---

## PKG-PLAT-03 审计日志基础链路

- 关联任务：`M1-008`
- 负责人泳道：`PLAT`
- 优先级：`P0`
- 依赖：`PKG-PLAT-01`
- 写入范围建议：
1. `apps/api/middleware/`
2. `apps/api/services/audit/`
3. `workers/common/`
4. `docs/audit/`

### 交付物

1. 统一审计日志写入组件
2. 审计字段字典
3. 关键动作埋点清单

### DoD

1. 关键读写动作可审计
2. 日志包含 actor/object/action/result/timestamp
3. 与 request_id/task_id 关联可查

---

## PKG-RISK-01 标签字典与规则配置底座

- 关联任务：`M2-001`
- 负责人泳道：`RISK`
- 优先级：`P0`
- 依赖：`PKG-DATA-01`, `PKG-PLAT-03`
- 写入范围建议：
1. `apps/api/services/tagging/`
2. `apps/api/db/models/`
3. `docs/tagging/`

### 交付物

1. 标签字典模型（类别/因子/名单）
2. 规则配置模型
3. 规则版本管理基础能力

### DoD

1. 标签规则可版本化
2. 规则变更有审计记录
3. 可回滚到历史规则版本

---

# 5. 可直接发送给 Codex/Claude Code 的任务指令

下面每条都可以直接作为单任务 prompt 使用。

## 指令模板 A（用于 PKG-PLAT-01）

任务编号：`PKG-PLAT-01`  
目标：完成工程骨架与规范初始化，对齐 Backlog 的 `M1-001`。  
允许修改目录：`apps/web`, `apps/api`, `workers`, `infra`, `docs`。  
必须交付：
1. 目录骨架
2. 开发环境启动方案
3. 配置模板与环境变量清单
4. 日志字段规范（含 request_id/task_id/rule_version）
验收标准：满足执行包 DoD。  
限制：不实现业务逻辑，不引入与任务无关的大型依赖。

## 指令模板 B（用于 PKG-DATA-01）

任务编号：`PKG-DATA-01`  
目标：完成数据库 Schema v1，对齐 `M1-002`。  
允许修改目录：`apps/api/db/migrations`, `apps/api/db/models`, `docs/schema`。  
必须交付：
1. 核心建表迁移
2. 索引和约束
3. 表关系说明文档
验收标准：可迁移、可回滚、可支撑 Market/Snapshot/DQ/DecisionLog。  
限制：不实现采集任务。

## 指令模板 C（用于 PKG-PLAT-02）

任务编号：`PKG-PLAT-02`  
目标：建立任务调度底座，对齐 `M1-006`。  
允许修改目录：`workers`, `infra`, `docs/runbooks`。  
必须交付：
1. Celery worker + beat 基础配置
2. 重试与幂等策略
3. 失败处理说明
验收标准：定时任务可跑、失败可重试、幂等有效。  
限制：不做具体数据采集逻辑。

## 指令模板 D（用于 PKG-DATA-02）

任务编号：`PKG-DATA-02`  
目标：实现市场与快照采集，对齐 `M1-003` + `M1-004`。  
允许修改目录：`workers/tasks/ingest`, `apps/api/services/ingest`, `docs/data-sources`。  
必须交付：
1. 市场元数据增量采集
2. 快照采集
3. 去重与采样策略
验收标准：稳定入库、失败重试、去重有效。  
限制：不实现 DQ 规则引擎。

## 指令模板 E（用于 PKG-DATA-03）

任务编号：`PKG-DATA-03`  
目标：实现 DQ v1 规则引擎，对齐 `M1-005`。  
允许修改目录：`workers/tasks/dq`, `apps/api/services/dq`, `docs/dq`。  
必须交付：
1. DQ 规则清单
2. DQ 评分与结果落库
3. DQ 告警记录
验收标准：每市场可产出 DQ 状态并可追溯。  
限制：不做前端页面。

## 指令模板 F（用于 PKG-PLAT-03）

任务编号：`PKG-PLAT-03`  
目标：建立审计日志基础链路，对齐 `M1-008`。  
允许修改目录：`apps/api/middleware`, `apps/api/services/audit`, `workers/common`, `docs/audit`。  
必须交付：
1. 统一审计日志写入组件
2. 审计字段字典
3. 关键操作埋点
验收标准：关键动作可追溯，且可关联 request_id/task_id。  
限制：不涉及 UI。

## 指令模板 G（用于 PKG-RISK-01）

任务编号：`PKG-RISK-01`  
目标：建立标签字典与规则配置底座，对齐 `M2-001`。  
允许修改目录：`apps/api/services/tagging`, `apps/api/db/models`, `docs/tagging`。  
必须交付：
1. 标签字典模型
2. 规则配置模型
3. 规则版本基础能力
验收标准：规则可版本化、可回滚、可审计。  
限制：不实现自动分类计算逻辑（`M2-002` 留后续包）。

---

# 6. 推荐派发顺序（今天可执行）

1. 先发 `PKG-PLAT-01`
2. 并行发 `PKG-DATA-01` 与 `PKG-PLAT-02`
3. 再发 `PKG-DATA-02`
4. 并行发 `PKG-DATA-03` 与 `PKG-PLAT-03`
5. 最后发 `PKG-RISK-01`

这样可以把主链路依赖压到最短，同时避免多人写同一目录产生冲突。
