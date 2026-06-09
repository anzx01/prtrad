# Polymarket Tail Risk 项目重新聚焦计划

## 问题诊断

当前项目偏离了原始目标。PRD V4 的核心是**寻找并验证交易机会**,但实际实现变成了**上线合规审批系统**。

---

## 原始目标 vs 当前实现

### 原始目标(PRD V4)
在 Polymarket 中寻找尾部 NO 仓位的定价偏差,通过模拟交易验证,再考虑实盘。

### 当前实现
构建了一套完整的上线评审合规流程,但缺少核心的交易执行和验证环节。

---

## 缺失的核心模块

### 1. 持仓管理 (Position Management)
**功能**:
- 跟踪当前持有的市场仓位
- 记录开仓/平仓时间、价格、数量
- 计算未实现/已实现 PnL
- 管理资金占用

**数据模型**(建议):
```python
class Position:
    id: UUID
    market_ref_id: UUID
    entry_time: datetime
    entry_price: Decimal
    entry_size: Decimal
    exit_time: datetime | None
    exit_price: Decimal | None
    status: str  # "open" | "closed"
    unrealized_pnl: Decimal | None
    realized_pnl: Decimal | None
```

### 2. 模拟交易引擎 (Paper Trading Engine)
**功能**:
- 根据 NetEV 筛选结果自动开仓
- 模拟市场价格变化
- 触发止损/止盈规则
- 记录交易历史

**核心服务**(建议):
```python
class PaperTradingService:
    def evaluate_entry_signal(candidate: NetEVCandidate) -> bool
    def simulate_entry(market_id, size) -> Position
    def update_positions(snapshot: MarketSnapshot)
    def evaluate_exit_conditions(position: Position) -> bool
    def simulate_exit(position: Position)
```

### 3. 交易验证报告 (Trading Validation)
**功能**:
- 统计模拟交易表现
- 按分类/时间段分析
- 计算夏普比率、最大回撤
- 对比回测结果与模拟交易表现

---

## 简化建议

### 保留的核心模块
1. **数据接入** (Ingest) - 必须
2. **数据质量** (DQ) - 必须
3. **分类标签** (Tagging) - 必须
4. **校准** (Calibration) - 必须
5. **NetEV 筛选** - 必须
6. **组合风控** (Risk) - 简化版,聚焦仓位上限

### 需要新增的模块
7. **持仓管理** (Position Management) ⭐ 新增
8. **模拟交易引擎** (Paper Trading) ⭐ 新增
9. **交易验证报告** (Validation Report) ⭐ 新增

### 可以暂缓的模块
- **人工审核队列** (Review Queue) - 自动化优先
- **评分系统** (Scoring) - 合并到 NetEV 逻辑
- **Launch Review / Go NoGo** - 等模拟交易验证后再说
- **阶段评审报告** (M4/M5/M6) - 暂时不需要
- **Shadow 运行** - 模拟交易就是 shadow
- **Kill-switch 审批** - 简化为自动触发规则

---

## 重新聚焦后的核心链路

```
市场数据 (Ingest)
  ↓
数据质量检查 (DQ)
  ↓
分类标签 (Tagging)
  ↓
校准估计 (Calibration) - 发现历史 edge
  ↓
NetEV 筛选 - 识别当前机会
  ↓
【新增】模拟交易引擎 - 自动开仓
  ↓
【新增】持仓管理 - 跟踪 PnL
  ↓
【新增】交易验证 - 分析表现
  ↓
组合风控 - 限制风险暴露
  ↓
回测对比 - 回测 vs 模拟交易一致性
```

---

## 实施路线图

### Phase 1: 最小交易闭环 (1-2 天)
1. 创建 `Position` 数据模型
2. 实现简单的 `PaperTradingService`
   - 从 NetEV admit 的候选自动开仓
   - 记录 entry 价格/时间
3. 每次快照更新时更新持仓 PnL
4. 简单前端页面显示当前持仓

### Phase 2: 平仓逻辑 (1 天)
1. 实现平仓触发条件:
   - 市场关闭时自动平仓
   - 简单止损规则(可选)
2. 记录 realized PnL
3. 前端显示历史交易记录

### Phase 3: 验证报告 (1 天)
1. 统计模拟交易表现
   - 总 PnL
   - 胜率
   - 按分类分析
2. 对比回测结果
3. 生成验证报告

### Phase 4: 迭代优化
- 优化开仓条件
- 调整仓位大小规则
- 引入更复杂的风险管理

---

## 关键判断

### 问题的根源
你在"还没验证策略能不能赚钱"之前,就开始构建"怎么安全上线"的流程。

### 正确的顺序
1. **先证明 edge 存在**(回测)
2. **再证明能捕获 edge**(模拟交易)
3. **最后考虑如何上线**(合规流程)

当前卡在第 1 步和第 2 步之间 - 回测有了,但没有模拟交易来验证。

### 下一步行动
**选项 A**: 补齐模拟交易层,完成验证闭环(推荐)
**选项 B**: 如果当前系统定位就是"合规工具",则需要重新定义项目目标

---

## 建议的最小可行版本 (MVP)

```python
# apps/api/db/models.py 新增
class Position(Base):
    __tablename__ = "positions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    market_ref_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"))
    entry_time: Mapped[datetime]
    entry_price: Mapped[Decimal]
    position_size: Mapped[Decimal]
    exit_time: Mapped[datetime | None]
    exit_price: Mapped[Decimal | None]
    status: Mapped[str]  # "open" | "closed"
    unrealized_pnl: Mapped[Decimal | None]
    realized_pnl: Mapped[Decimal | None]
    
# apps/api/services/paper_trading/service.py 新增
class PaperTradingService:
    def evaluate_candidates(self, limit: int = 10):
        """从 NetEV admit 的候选中选择开仓"""
        candidates = netev_service.list_candidates(decision="admit")
        for candidate in candidates[:limit]:
            if self._should_enter(candidate):
                self.enter_position(candidate)
    
    def enter_position(self, candidate: NetEVCandidate):
        """模拟开仓"""
        snapshot = self._get_latest_snapshot(candidate.market_ref_id)
        position = Position(
            id=uuid.uuid4(),
            market_ref_id=candidate.market_ref_id,
            entry_time=utc_now(),
            entry_price=snapshot.best_ask_no,
            position_size=Decimal("100"),  # 固定仓位
            status="open",
        )
        self.db.add(position)
        self.db.commit()
    
    def update_positions(self):
        """更新所有开放持仓的 PnL"""
        open_positions = self._get_open_positions()
        for position in open_positions:
            snapshot = self._get_latest_snapshot(position.market_ref_id)
            current_price = snapshot.best_bid_no
            position.unrealized_pnl = (
                (position.entry_price - current_price) * position.position_size
            )
            self.db.commit()
    
    def close_expired_positions(self):
        """平仓已关闭市场的持仓"""
        open_positions = self._get_open_positions()
        for position in open_positions:
            market = self.db.get(Market, position.market_ref_id)
            if market.market_status in ["closed", "resolved"]:
                self.exit_position(position)
```

---

## 总结

**当前问题**: 项目变成了"上线审批系统",而非"交易验证系统"

**核心缺失**: 没有持仓管理和模拟交易执行

**建议方向**: 暂停合规功能开发,先补齐交易验证闭环

**最小行动**: 用 1-2 天实现一个最简单的模拟交易引擎,验证策略是否真的有 edge

---

**2026-06-09 诊断完成**
