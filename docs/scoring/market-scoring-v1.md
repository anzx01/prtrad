# 市场评分模块 (Market Scoring)

## 概述

市场评分模块对已分类的市场进行清晰度和客观性评分，并根据评分结果给出准入建议。

## 评分维度

### 1. 清晰度评分 (Clarity Score)

评估市场问题的清晰度，包括：

- **问题长度** (20%): 10-200 字符为最佳
- **时间范围明确性** (25%): 是否包含明确的日期、年份或时间词
- **可量化指标** (20%): 是否包含数字、百分比、排名等
- **模糊词汇惩罚** (15%): 避免 "maybe", "possibly", "approximately" 等
- **描述完整性** (20%): 是否有详细的描述文本

### 2. 客观性评分 (Resolution Objectivity Score)

评估结算标准的客观性，包括：

- **结算标准存在性** (30%): 是否有明确的结算标准
- **权威数据源引用** (25%): 是否引用官方、政府、权威媒体等数据源
- **主观词汇惩罚** (20%): 避免 "believe", "think", "seems" 等
- **类别客观性** (15%): 不同类别的固有客观性（Numeric > Time > Statistical）
- **可验证条件** (10%): 是否包含可验证的事实性陈述

### 3. 综合评分 (Overall Score)

综合评分 = 清晰度评分 × 0.5 + 客观性评分 × 0.5

## 准入建议

根据评分结果，系统会给出以下三种建议：

1. **Approved**: 所有评分均达到批准阈值（默认 0.7）
2. **ReviewRequired**: 评分在审核阈值（0.5）和批准阈值（0.7）之间
3. **Rejected**: 任一评分低于审核阈值（0.5）

## 拒绝原因码

- `SCORE_CLARITY_TOO_LOW`: 清晰度评分过低
- `SCORE_OBJECTIVITY_TOO_LOW`: 客观性评分过低
- `SCORE_OVERALL_TOO_LOW`: 综合评分过低
- `CLASSIFICATION_LOW_CONFIDENCE`: 分类置信度过低
- `SCORE_REQUIRES_REVIEW`: 评分需要人工审核

## 配置参数

在 `.env` 文件中配置：

```bash
# 评分任务运行间隔（秒）
SCORING_RUN_INTERVAL_SECONDS=180

# 每次评分的市场数量限制
SCORING_MARKET_LIMIT=200
```

## 数据库表

### market_scoring_results

存储市场评分结果：

- `market_ref_id`: 市场 ID
- `classification_result_id`: 关联的分类结果 ID
- `clarity_score`: 清晰度评分 (0-1)
- `resolution_objectivity_score`: 客观性评分 (0-1)
- `overall_score`: 综合评分 (0-1)
- `admission_recommendation`: 准入建议 (Approved/ReviewRequired/Rejected)
- `rejection_reason_code`: 拒绝原因码
- `scoring_details`: 评分详细信息（JSON）
- `scored_at`: 评分时间

## Worker 任务

### scoring.score_classified_markets

定时任务，对已分类但尚未评分的市场进行评分。

**任务名称**: `scoring.score_classified_markets`

**调度**: 每 180 秒运行一次（可配置）

**参数**:
- `market_limit`: 限制处理的市场数量

**返回**:
```json
{
  "status": "success",
  "scored_at": "2026-04-03T...",
  "total": 100,
  "scored": 98,
  "approved": 45,
  "review_required": 40,
  "rejected": 13,
  "errors": 2
}
```

## 审计日志

评分操作会写入审计日志：

- **object_type**: `market_scoring`
- **action**: `score_market`
- **result**: 准入建议 (Approved/ReviewRequired/Rejected)
- **event_payload**: 包含评分详情

## 使用示例

### 手动触发评分任务

```python
from worker.tasks.scoring import score_classified_markets

# 异步执行
result = score_classified_markets.delay(market_limit=50)

# 同步执行
result = score_classified_markets(market_limit=50)
```

### 查询评分结果

```python
from db.models import MarketScoringResult
from db.session import session_scope

with session_scope() as session:
    # 查询需要审核的市场
    results = session.query(MarketScoringResult).filter(
        MarketScoringResult.admission_recommendation == "ReviewRequired"
    ).all()
    
    for result in results:
        print(f"Market: {result.market_ref_id}")
        print(f"Clarity: {result.clarity_score}")
        print(f"Objectivity: {result.resolution_objectivity_score}")
        print(f"Overall: {result.overall_score}")
```

## 对应 Backlog 任务

本模块实现了以下 Backlog 任务：

- **M2-003**: 清晰度/客观性评分模块
  - ✅ 计算 `clarity_score` 与 `resolution_objectivity_score`
  - ✅ 输出准入建议
  - ✅ 低于阈值的市场标记为 `ReviewRequired` 或拒绝
  - ✅ 评分依据可追溯（存储在 `scoring_details` 中）

## 下一步

评分结果将用于：

1. **M2-004**: 审核任务流 - 自动生成审核待办
2. **M2-008**: 分类拒绝原因码接入 - 统一拒绝原因管理
3. **M3+**: 准入决策 - 作为交易候选筛选的输入
