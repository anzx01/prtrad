# PKG-RISK-03 完成报告

**任务编号**: PKG-RISK-03  
**任务名称**: 清晰度/客观性评分模块  
**对应 Backlog**: M2-003  
**完成时间**: 2026-04-03  
**状态**: ✅ 已完成

## 交付物

### 1. 评分服务模块

**文件**: `apps/api/services/scoring/`

- `service.py`: 核心评分逻辑
- `contracts.py`: 数据契约定义
- `__init__.py`: 模块导出

**功能**:
- 清晰度评分（5 个维度）
- 客观性评分（5 个维度）
- 综合评分计算
- 准入建议判定
- 审计日志集成

### 2. 数据库模型

**表**: `market_scoring_results`

**字段**:
- 评分结果：`clarity_score`, `resolution_objectivity_score`, `overall_score`
- 准入建议：`admission_recommendation`, `rejection_reason_code`
- 详细信息：`scoring_details` (JSON)
- 关联：`market_ref_id`, `classification_result_id`

**迁移脚本**: `apps/api/db/migrations/versions/20260403_0006_market_scoring_results.py`

### 3. Worker 任务

**任务**: `scoring.score_classified_markets`

**调度**: 每 180 秒运行一次（可配置）

**功能**:
- 查询已分类但未评分的市场
- 批量执行评分
- 持久化评分结果
- 写入审计日志

### 4. 文档

**文件**: `docs/scoring/market-scoring-v1.md`

包含：
- 评分维度说明
- 配置参数
- 使用示例
- API 参考

## 验收标准（DoD）

✅ 每个分类结果具备两类评分  
✅ 低于阈值的市场被标记为 `ReviewRequired` 或拒绝  
✅ 评分依据可追溯（存储在 `scoring_details` 中）  
✅ 评分操作写入审计日志  
✅ Worker 任务可定时自动运行  
✅ 数据库迁移成功执行  
✅ 代码通过语法检查

## 评分逻辑

### 清晰度评分 (Clarity Score)

1. **问题长度** (20%): 10-200 字符最佳
2. **时间范围** (25%): 包含日期、年份
3. **可量化指标** (20%): 数字、百分比
4. **模糊词汇惩罚** (15%): 避免 "maybe", "possibly"
5. **描述完整性** (20%): 有详细描述

### 客观性评分 (Objectivity Score)

1. **结算标准** (30%): 明确的结算标准
2. **权威数据源** (25%): 引用官方来源
3. **主观词汇惩罚** (20%): 避免 "believe", "think"
4. **类别客观性** (15%): Numeric > Time > Statistical
5. **可验证条件** (10%): 事实性陈述

### 准入建议

- **Approved**: 所有评分 ≥ 0.7
- **ReviewRequired**: 评分在 0.5-0.7 之间
- **Rejected**: 任一评分 < 0.5

## 配置

在 `.env` 文件中：

```bash
SCORING_RUN_INTERVAL_SECONDS=180
SCORING_MARKET_LIMIT=200
```

## 审计日志

所有评分操作记录到 `audit_logs` 表：

- **object_type**: `market_scoring`
- **action**: `score_market`
- **result**: 准入建议
- **event_payload**: 评分详情

## 下一步

评分模块已就绪，可以进入下一个任务包：

**PKG-RISK-04**: 审核任务流（ReviewTask）

评分结果将用于：
- 自动生成审核待办
- 统一拒绝原因管理
- 交易候选筛选
