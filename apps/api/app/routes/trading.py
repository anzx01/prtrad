from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from services.execution import ExecutionService
from services.trading import TradingService


router = APIRouter(prefix="/trading", tags=["trading"])


class TradingBlockerSchema(BaseModel):
    code: str
    message: str


class TradingModeGuardSchema(BaseModel):
    ready: bool
    blockers: list[TradingBlockerSchema]


class TradingMarketSchema(BaseModel):
    market_id: str
    question: str
    net_ev: float
    price: float


class TradingLinkedRunSchema(BaseModel):
    id: str
    run_name: str
    recommendation: str
    created_at: str | None = None
    risk_state: str | None = None


class TradingOrderSchema(BaseModel):
    id: str
    mode: str
    status: str
    provider: str
    market_id: str
    question: str
    outcome_side: str
    token_id: str | None = None
    price: float | None = None
    size: float | None = None
    notional: float | None = None
    net_ev: float | None = None
    requested_by: str | None = None
    provider_order_id: str | None = None
    failure_reason_code: str | None = None
    failure_reason_text: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    submitted_at: str | None = None
    completed_at: str | None = None


class TradingStateSchema(BaseModel):
    id: str
    status: str
    mode: str
    started_by: str | None = None
    stopped_by: str | None = None
    last_started_at: str | None = None
    last_stopped_at: str | None = None
    last_stop_reason_code: str | None = None
    last_stop_reason_text: str | None = None
    last_stop_was_automatic: bool
    paper: TradingModeGuardSchema
    live: TradingModeGuardSchema
    executable_market_count: int
    executable_markets: list[TradingMarketSchema]
    latest_backtest: TradingLinkedRunSchema | None = None
    latest_shadow: TradingLinkedRunSchema | None = None
    risk_state: str
    pending_kill_switch_count: int
    live_mode_enabled: bool
    headline: str
    description: str
    latest_order: TradingOrderSchema | None = None
    updated_at: str | None = None


class TradingStateResponse(BaseModel):
    state: TradingStateSchema


class TradingStartRequest(BaseModel):
    mode: str
    actor_id: str | None = None


class TradingStopRequest(BaseModel):
    actor_id: str | None = None
    reason: str | None = None


class TradingExecuteRequest(BaseModel):
    mode: str | None = None
    actor_id: str | None = None


class TradingExecuteResponse(BaseModel):
    state: TradingStateSchema
    order: TradingOrderSchema


class TradingOrdersResponse(BaseModel):
    orders: list[TradingOrderSchema]


class TradingOrderResponse(BaseModel):
    order: TradingOrderSchema


@router.get("/state", response_model=TradingStateResponse)
def get_trading_state(session: Session = Depends(get_db)) -> TradingStateResponse:
    service = TradingService(session)
    state = service.get_state_view()
    session.commit()
    return TradingStateResponse(state=state)


@router.post("/start", response_model=TradingStateResponse)
def start_trading(body: TradingStartRequest, session: Session = Depends(get_db)) -> TradingStateResponse:
    service = TradingService(session)
    try:
        state = service.start(mode=body.mode, actor_id=body.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    session.commit()
    return TradingStateResponse(state=state)


@router.post("/stop", response_model=TradingStateResponse)
def stop_trading(body: TradingStopRequest, session: Session = Depends(get_db)) -> TradingStateResponse:
    service = TradingService(session)
    state = service.stop(actor_id=body.actor_id, reason=body.reason)
    session.commit()
    return TradingStateResponse(state=state)


@router.post("/execute-next", response_model=TradingExecuteResponse)
def execute_next_trading(
    body: TradingExecuteRequest | None = None,
    session: Session = Depends(get_db),
) -> TradingExecuteResponse:
    service = ExecutionService(session)
    payload = body or TradingExecuteRequest()
    try:
        result = service.execute_next(mode=payload.mode, actor_id=payload.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    session.commit()
    return TradingExecuteResponse(**result)


@router.get("/orders", response_model=TradingOrdersResponse)
def list_trading_orders(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_db),
) -> TradingOrdersResponse:
    service = ExecutionService(session)
    orders = service.list_orders(limit=limit)
    session.commit()
    return TradingOrdersResponse(orders=orders)


@router.get("/orders/{order_id}", response_model=TradingOrderResponse)
def get_trading_order(order_id: str, session: Session = Depends(get_db)) -> TradingOrderResponse:
    service = ExecutionService(session)
    order = service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在。")
    session.commit()
    return TradingOrderResponse(order=order)
