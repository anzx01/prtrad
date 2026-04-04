# 审核任务流（Review Task Flow）

## 概述

审核任务流是 Polymarket Tail Risk 系统中的关键组件，用于管理需要人工审核的市场分类结果。当自动分类引擎无法确定市场的准确分类，或者分类结果存在冲突、低置信度等问题时，系统会自动生成审核任务，进入人工审核流程。

## 核心功能

### 1. 审核任务自动生成

系统会自动为以下情况生成审核任务：

- **低置信度分类**：分类置信度低于阈值（默认 0.7）
- **规则冲突**：多个规则产生冲突的分类结果
- **评分不通过**：清晰度或客观性评分低于准入阈值
- **手动标记**：分类结果被明确标记为需要审核

### 2. 审核任务状态管理

审核任务支持以下状态流转：

```
pending (待审核)
  ↓
in_progress (审核中)
  ↓
approved (通过) / rejected (拒绝) / cancelled (取消)
```

**状态说明**：

- `pending`: 任务已创建，等待审核人员认领
- `in_progress`: 任务已被认领，正在审核中
- `approved`: 审核通过，分类结果被确认
- `rejected`: 审核拒绝，分类结果被否决
- `cancelled`: 任务被取消（如市场已关闭）

**允许的状态迁移**：

- `pending` → `in_progress`, `cancelled`
- `in_progress` → `approved`, `rejected`, `pending`
- `approved`, `rejected`, `cancelled` 为终态，不可再迁移

### 3. 优先级管理

审核任务支持四个优先级：

- `urgent`: 紧急（冲突数 > 2 或置信度 < 0.5）
- `high`: 高优先级
- `normal`: 普通优先级（默认）
- `low`: 低优先级

审核队列按优先级和创建时间排序，确保重要任务优先处理。

## 数据模型

### MarketReviewTask

```python
class MarketReviewTask:
    id: UUID                          # 任务 ID
    market_ref_id: UUID               # 关联市场 ID
    classification_result_id: UUID    # 关联分类结果 ID
    queue_status: str                 # 队列状态
    review_reason_code: str | None    # 审核原因码
    priority: str                     # 优先级
    assigned_to: str | None           # 分配给的审核人
    review_payload: dict | None       # 审核相关数据
    resolved_at: datetime | None      # 解决时间
    created_at: datetime              # 创建时间
    updated_at: datetime              # 更新时间
```

## 服务接口

### ReviewService

#### 创建审核任务

```python
def create_review_task(
    review_input: ReviewTaskInput
) -> MarketReviewTask
```

**输入**：
- `market_ref_id`: 市场 ID
- `classification_result_id`: 分类结果 ID
- `review_reason_code`: 审核原因码（可选）
- `priority`: 优先级（默认 "normal"）
- `review_payload`: 附加数据（可选）

**输出**：创建的审核任务对象

**异常**：
- `ValueError`: 分类结果不存在或已有审核任务

#### 查询审核队列

```python
def get_review_queue(
    queue_status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[MarketReviewTask]
```

**参数**：
- `queue_status`: 状态过滤（可选）
- `priority`: 优先级过滤（可选）
- `assigned_to`: 审核人过滤（可选）
- `limit`: 返回数量限制
- `offset`: 分页偏移量

**输出**：审核任务列表（按优先级和创建时间排序）

#### 更新审核任务

```python
def update_review_task(
    review_task_id: UUID,
    update: ReviewTaskUpdate,
    actor_id: str | None = None,
) -> MarketReviewTask
```

**输入**：
- `review_task_id`: 任务 ID
- `update`: 更新数据
  - `queue_status`: 新状态（可选）
  - `assigned_to`: 分配人（可选）
  - `review_payload`: 附加数据（可选）
- `actor_id`: 操作者 ID

**输出**：更新后的审核任务

**异常**：
- `ValueError`: 任务不存在或状态迁移不合法

#### 批准审核

```python
def approve_review(
    review_task_id: UUID,
    actor_id: str,
    approval_notes: str | None = None,
) -> MarketReviewTask
```

**输入**：
- `review_task_id`: 任务 ID
- `actor_id`: 审核人 ID
- `approval_notes`: 批准备注（可选）

**输出**：更新后的审核任务

**前置条件**：任务必须处于 `in_progress` 状态

#### 拒绝审核

```python
def reject_review(
    review_task_id: UUID,
    actor_id: str,
    rejection_reason: str,
    rejection_notes: str | None = None,
) -> MarketReviewTask
```

**输入**：
- `review_task_id`: 任务 ID
- `actor_id`: 审核人 ID
- `rejection_reason`: 拒绝原因码
- `rejection_notes`: 拒绝备注（可选）

**输出**：更新后的审核任务

**前置条件**：任务必须处于 `in_progress` 状态

## Worker 任务

### generate_review_tasks

**任务名称**：`review.generate_review_tasks`

**调度频率**：每 300 秒（5 分钟）执行一次（可配置）

**功能**：自动为需要审核的分类结果生成审核任务

**执行逻辑**：

1. 查询 `requires_review=True` 且尚未创建审核任务的分类结果
2. 根据分类结果确定审核原因码：
   - 有失败原因码：使用该原因码
   - 有冲突：使用 `CONFLICT_DETECTED`
   - 低置信度：使用 `LOW_CONFIDENCE`
   - 其他：使用 `MANUAL_REVIEW_REQUIRED`
3. 根据冲突数和置信度确定优先级：
   - 冲突数 > 2 或置信度 < 0.5：`high`
   - 其他：`normal`
4. 创建审核任务并写入审计日志

**配置参数**：

- `REVIEW_TASK_GENERATION_INTERVAL_SECONDS`: 调度间隔（默认 300 秒）
- `REVIEW_TASK_MARKET_LIMIT`: 单次处理市场数量限制（默认 200）

**返回结果**：

```json
{
  "status": "success",
  "generated_at": "2026-04-04T12:00:00Z",
  "total": 50,
  "created": 48,
  "failed": 2
}
```

## 审计日志

所有审核任务操作都会写入审计日志（`audit_logs` 表），包括：

- **create_review_task**: 创建审核任务
- **update_review_task**: 更新审核任务
- **approve_review**: 批准审核
- **reject_review**: 拒绝审核

审计日志包含以下信息：

- `actor_id`: 操作者 ID
- `object_type`: `market_review_task`
- `object_id`: 审核任务 ID
- `action`: 操作类型
- `result`: 操作结果
- `event_payload`: 操作详情
- `task_id`: Worker 任务 ID（如果适用）
- `created_at`: 操作时间

## 使用示例

### 创建审核任务

```python
from services.review import ReviewService, ReviewTaskInput
from db.session import session_scope

with session_scope() as session:
    review_service = ReviewService(db=session)
    
    review_input = ReviewTaskInput(
        market_ref_id=market_id,
        classification_result_id=classification_id,
        review_reason_code="LOW_CONFIDENCE",
        priority="high",
    )
    
    review_task = review_service.create_review_task(review_input)
    session.commit()
```

### 查询待审核任务

```python
from services.review import ReviewService
from db.session import session_scope

with session_scope() as session:
    review_service = ReviewService(db=session)
    
    # 查询待审核的高优先级任务
    pending_tasks = review_service.get_review_queue(
        queue_status="pending",
        priority="high",
        limit=10,
    )
```

### 认领并审核任务

```python
from services.review import ReviewService, ReviewTaskUpdate
from db.session import session_scope

with session_scope() as session:
    review_service = ReviewService(db=session)
    
    # 认领任务
    update = ReviewTaskUpdate(
        queue_status="in_progress",
        assigned_to="reviewer@example.com",
    )
    review_task = review_service.update_review_task(
        review_task_id=task_id,
        update=update,
        actor_id="reviewer@example.com",
    )
    
    # 审核通过
    review_task = review_service.approve_review(
        review_task_id=task_id,
        actor_id="reviewer@example.com",
        approval_notes="分类结果准确，批准通过",
    )
    
    session.commit()
```

## 常见审核原因码

| 原因码 | 说明 |
|--------|------|
| `LOW_CONFIDENCE` | 分类置信度低于阈值 |
| `CONFLICT_DETECTED` | 规则冲突 |
| `LOW_CLARITY_SCORE` | 清晰度评分过低 |
| `LOW_OBJECTIVITY_SCORE` | 客观性评分过低 |
| `MANUAL_REVIEW_REQUIRED` | 需要人工审核（通用） |
| `AMBIGUOUS_CATEGORY` | 类别模糊 |
| `MISSING_RESOLUTION_CRITERIA` | 缺少结算标准 |

## 最佳实践

1. **及时处理高优先级任务**：高优先级任务通常涉及冲突或低置信度，应优先处理
2. **记录详细的审核备注**：批准或拒绝时应记录清晰的理由，便于后续追溯
3. **定期检查审核队列**：避免任务积压，确保审核流程顺畅
4. **监控审核任务生成速率**：如果生成速率过高，可能需要优化分类规则
5. **分析拒绝原因分布**：定期分析拒绝原因，优化自动分类引擎

## 相关文档

- [市场分类服务](./market-classification-v1.md)
- [市场评分服务](./market-scoring-v1.md)
- [审计日志规范](../audit/audit-log-spec.md)

## 版本历史

- **v1.0** (2026-04-04): 初始版本，实现基础审核任务流
