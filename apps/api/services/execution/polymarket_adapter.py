from __future__ import annotations

import time
from decimal import Decimal, InvalidOperation
from typing import Any

from db.models import TradingOrderRecord

from .contracts import CollateralBalanceSnapshot, ExecutionAdapterError, ExecutionAdapterResult


class PolymarketExecutionAdapter:
    provider = "polymarket_clob"

    _FILLED_STATUSES = frozenset({"filled", "matched", "mined", "confirmed"})
    _CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})
    _FAILED_STATUSES = frozenset({"failed", "rejected", "expired"})

    def __init__(self, *, settings: Any) -> None:
        self.settings = settings

    def get_collateral_snapshot(self) -> CollateralBalanceSnapshot:
        sdk = self._load_sdk()
        client, funder_address, signature_type = self._build_live_client(sdk=sdk)
        return self._fetch_collateral_snapshot(
            client=client,
            sdk=sdk,
            funder_address=funder_address,
            signature_type=signature_type,
            refresh_allowance=True,
        )

    def execute(self, *, order: TradingOrderRecord) -> ExecutionAdapterResult:
        sdk = self._load_sdk()
        client, funder_address, signature_type = self._build_live_client(sdk=sdk)
        collateral = self._preflight_collateral(
            client=client,
            sdk=sdk,
            order=order,
            funder_address=funder_address,
            signature_type=signature_type,
        )

        try:
            response = client.create_and_post_order(
                sdk.OrderArgsV2(
                    token_id=str(order.token_id),
                    price=float(order.order_price),
                    size=float(order.order_size),
                    side=sdk.Side.BUY,
                ),
                order_type=sdk.OrderType.GTC,
            )
        except Exception as exc:  # noqa: BLE001 - SDK throws custom runtime errors.
            raise ExecutionAdapterError(
                code="LIVE_ORDER_SUBMIT_FAILED",
                message=self._normalize_exception_message(exc),
            ) from exc

        if isinstance(response, dict) and not bool(response.get("success", True)):
            message = self._extract_error_message(response) or "实盘订单被交易所拒绝。"
            raise ExecutionAdapterError(code="LIVE_ORDER_REJECTED", message=message)

        provider_order_id = self._extract_order_id(response)
        final_status = self._normalize_status(response)
        details: dict[str, Any] = {
            "simulated": False,
            "funder_address": funder_address,
            "signature_type": signature_type,
            "collateral": self._serialize_collateral_snapshot(collateral),
            "submitted_response": self._serialize_response(response),
            "status_checks": [],
        }

        if provider_order_id:
            poll_summary = self._poll_until_terminal(
                client=client,
                sdk=sdk,
                provider_order_id=provider_order_id,
            )
            final_status = str(poll_summary["final_status"])
            details["status_checks"] = poll_summary["checks"]
            if poll_summary.get("final_response") is not None:
                details["final_order_response"] = poll_summary["final_response"]
            if poll_summary.get("cancel_response") is not None:
                details["cancel_response"] = poll_summary["cancel_response"]
            if poll_summary.get("cancel_requested"):
                details["cancel_requested"] = True

        return ExecutionAdapterResult(
            status=final_status,
            provider=self.provider,
            provider_order_id=provider_order_id,
            details=details,
        )

    def _build_live_client(self, *, sdk: Any) -> tuple[Any, str, int]:
        private_key = (self.settings.trading_live_private_key or "").strip()
        if not private_key:
            raise ExecutionAdapterError(
                code="LIVE_PRIVATE_KEY_MISSING",
                message="还没配置实盘私钥，请先补齐 `TRADING_LIVE_PRIVATE_KEY`。",
            )

        base_client = sdk.ClobClient(
            self.settings.polymarket_clob_api_url,
            int(self.settings.trading_live_chain_id),
            key=private_key,
            use_server_time=bool(self.settings.trading_live_use_server_time),
            retry_on_error=bool(self.settings.trading_live_retry_on_error),
        )
        api_creds = self._load_api_creds(base_client=base_client, sdk=sdk)

        signature_type = int(self.settings.trading_live_signature_type)
        if signature_type not in {0, 1, 2, 3}:
            raise ExecutionAdapterError(
                code="LIVE_SIGNATURE_TYPE_INVALID",
                message="`TRADING_LIVE_SIGNATURE_TYPE` 只能是 0、1、2、3 之一。",
            )
        funder_address = self._resolve_funder_address(base_client=base_client, signature_type=signature_type)

        client = sdk.ClobClient(
            self.settings.polymarket_clob_api_url,
            int(self.settings.trading_live_chain_id),
            key=private_key,
            creds=api_creds,
            signature_type=signature_type,
            funder=funder_address,
            use_server_time=bool(self.settings.trading_live_use_server_time),
            retry_on_error=bool(self.settings.trading_live_retry_on_error),
        )
        return client, funder_address, signature_type

    def _load_api_creds(self, *, base_client: Any, sdk: Any) -> Any:
        api_key = (self.settings.trading_live_api_key or "").strip()
        api_secret = (self.settings.trading_live_api_secret or "").strip()
        api_passphrase = (self.settings.trading_live_api_passphrase or "").strip()
        if api_key and api_secret and api_passphrase:
            return sdk.ApiCreds(
                api_key=api_key,
                api_secret=api_secret,
                api_passphrase=api_passphrase,
            )

        try:
            return base_client.create_or_derive_api_key()
        except Exception as exc:  # noqa: BLE001 - SDK throws custom runtime errors.
            raise ExecutionAdapterError(
                code="LIVE_API_CREDS_UNAVAILABLE",
                message=f"无法创建或派生 L2 API 凭证：{self._normalize_exception_message(exc)}",
            ) from exc

    def _resolve_funder_address(self, *, base_client: Any, signature_type: int) -> str:
        configured = (self.settings.trading_live_funder_address or "").strip()
        if configured:
            return configured
        if signature_type == 0:
            return str(base_client.get_address())
        raise ExecutionAdapterError(
            code="LIVE_FUNDER_MISSING",
            message="当前签名类型需要显式提供 funder 地址，请先补齐 `TRADING_LIVE_FUNDER_ADDRESS`。",
        )

    def _preflight_collateral(
        self,
        *,
        client: Any,
        sdk: Any,
        order: TradingOrderRecord,
        funder_address: str,
        signature_type: int,
    ) -> CollateralBalanceSnapshot:
        snapshot = self._fetch_collateral_snapshot(
            client=client,
            sdk=sdk,
            funder_address=funder_address,
            signature_type=signature_type,
            refresh_allowance=True,
        )
        required = self._decimal_or_none(order.notional_amount) or Decimal("0")

        if snapshot.balance is not None and snapshot.balance < required:
            raise ExecutionAdapterError(
                code="LIVE_NOT_ENOUGH_BALANCE",
                message=f"资金钱包余额不足，至少需要 {required:.6f} 的可用稳定币余额。",
            )
        if snapshot.allowance is not None and snapshot.allowance < required:
            raise ExecutionAdapterError(
                code="LIVE_ALLOWANCE_NOT_READY",
                message="资金钱包授权额度不足，请先在 Polymarket 完成首笔授权后再回来发单。",
            )
        if snapshot.available is not None and snapshot.available < required:
            raise ExecutionAdapterError(
                code="LIVE_NOT_ENOUGH_AVAILABLE_COLLATERAL",
                message=f"当前可用资金不足，至少需要 {required:.6f} 的可用下单额度。",
            )
        return snapshot

    def _fetch_collateral_snapshot(
        self,
        *,
        client: Any,
        sdk: Any,
        funder_address: str | None,
        signature_type: int | None,
        refresh_allowance: bool,
    ) -> CollateralBalanceSnapshot:
        params = sdk.BalanceAllowanceParams(asset_type=sdk.AssetType.COLLATERAL)
        if refresh_allowance:
            try:
                client.update_balance_allowance(params)
            except Exception:
                pass

        try:
            balance_info = client.get_balance_allowance(params)
        except Exception as exc:  # noqa: BLE001 - SDK throws custom runtime errors.
            raise ExecutionAdapterError(
                code="LIVE_BALANCE_CHECK_FAILED",
                message=f"无法读取实盘钱包余额：{self._normalize_exception_message(exc)}",
            ) from exc

        payload = balance_info if isinstance(balance_info, dict) else {"raw": str(balance_info)}
        balance = self._decimal_or_none(payload.get("balance"))
        allowance = self._decimal_or_none(payload.get("allowance"))
        available_candidates = [item for item in (balance, allowance) if item is not None]
        available = min(available_candidates) if available_candidates else None
        return CollateralBalanceSnapshot(
            balance=balance,
            allowance=allowance,
            available=available,
            funder_address=funder_address,
            signature_type=signature_type,
            raw=payload,
        )

    def _poll_until_terminal(self, *, client: Any, sdk: Any, provider_order_id: str) -> dict[str, Any]:
        attempts = max(1, int(self.settings.trading_live_status_poll_attempts))
        interval_seconds = max(0.0, float(self.settings.trading_live_status_poll_interval_seconds))
        checks: list[dict[str, Any]] = []

        for attempt in range(attempts):
            if attempt > 0 and interval_seconds > 0:
                time.sleep(interval_seconds)

            try:
                response = client.get_order(provider_order_id)
            except Exception as exc:  # noqa: BLE001 - SDK throws custom runtime errors.
                checks.append(
                    {
                        "attempt": attempt + 1,
                        "status": "unknown",
                        "error": self._normalize_exception_message(exc),
                    }
                )
                continue

            status = self._normalize_status(response)
            checks.append(
                {
                    "attempt": attempt + 1,
                    "status": status,
                    "response": self._serialize_response(response),
                }
            )

            if status in self._FILLED_STATUSES:
                return {
                    "final_status": status,
                    "checks": checks,
                    "final_response": self._serialize_response(response),
                    "cancel_requested": False,
                    "cancel_response": None,
                }
            if status in self._CANCELLED_STATUSES:
                return {
                    "final_status": "cancelled",
                    "checks": checks,
                    "final_response": self._serialize_response(response),
                    "cancel_requested": False,
                    "cancel_response": None,
                }
            if status in self._FAILED_STATUSES:
                message = self._extract_error_message(response) or "实盘订单最终失败。"
                raise ExecutionAdapterError(code="LIVE_ORDER_FINAL_FAILED", message=message)

        cancel_response = self._cancel_order(client=client, sdk=sdk, provider_order_id=provider_order_id)
        final_response = self._safe_get_order(client=client, provider_order_id=provider_order_id)
        final_status = self._normalize_status(final_response) if final_response is not None else "cancelled"

        if final_status in self._FILLED_STATUSES:
            return {
                "final_status": final_status,
                "checks": checks,
                "final_response": self._serialize_response(final_response),
                "cancel_requested": True,
                "cancel_response": self._serialize_response(cancel_response),
            }
        if final_status in self._FAILED_STATUSES:
            message = self._extract_error_message(final_response) or "实盘订单最终失败。"
            raise ExecutionAdapterError(code="LIVE_ORDER_FINAL_FAILED", message=message)
        if final_status not in self._CANCELLED_STATUSES:
            final_status = "cancelled"

        return {
            "final_status": final_status,
            "checks": checks,
            "final_response": self._serialize_response(final_response) if final_response is not None else None,
            "cancel_requested": True,
            "cancel_response": self._serialize_response(cancel_response),
        }

    def _cancel_order(self, *, client: Any, sdk: Any, provider_order_id: str) -> Any:
        try:
            response = client.cancel_order(sdk.OrderPayload(orderID=provider_order_id))
        except Exception as exc:  # noqa: BLE001 - SDK throws custom runtime errors.
            raise ExecutionAdapterError(
                code="LIVE_ORDER_CANCEL_FAILED",
                message=f"订单长时间未成交，自动撤单失败：{self._normalize_exception_message(exc)}",
            ) from exc

        if isinstance(response, dict) and not bool(response.get("success", True)):
            message = self._extract_error_message(response) or "订单长时间未成交，自动撤单失败。"
            raise ExecutionAdapterError(code="LIVE_ORDER_CANCEL_FAILED", message=message)
        return response

    def _safe_get_order(self, *, client: Any, provider_order_id: str) -> Any | None:
        try:
            return client.get_order(provider_order_id)
        except Exception:
            return None

    @staticmethod
    def _load_sdk() -> Any:
        try:
            import py_clob_client_v2 as sdk
        except Exception as exc:  # noqa: BLE001 - missing dependency or import failure.
            raise ExecutionAdapterError(
                code="LIVE_SDK_UNAVAILABLE",
                message="实盘 SDK 未安装，请先安装 `py_clob_client_v2` 依赖。",
            ) from exc
        return sdk

    @staticmethod
    def _extract_order_id(response: Any) -> str | None:
        candidates = [response]
        if isinstance(response, dict):
            nested = response.get("order")
            if isinstance(nested, dict):
                candidates.append(nested)

        for payload in candidates:
            if not isinstance(payload, dict):
                continue
            for key in ("orderID", "orderId", "id"):
                value = payload.get(key)
                if value:
                    return str(value)
        return None

    @classmethod
    def _normalize_status(cls, response: Any) -> str:
        if not isinstance(response, dict):
            return "submitted"

        for payload in (response, response.get("order")):
            if not isinstance(payload, dict):
                continue
            for key in ("status", "orderStatus"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    normalized = value.strip().lower()
                    if normalized in cls._FILLED_STATUSES:
                        return normalized
                    if normalized in cls._CANCELLED_STATUSES:
                        return "cancelled"
                    return normalized
        return "submitted"

    @staticmethod
    def _extract_error_message(response: Any) -> str | None:
        if not isinstance(response, dict):
            return None

        for payload in (response, response.get("order"), response.get("error")):
            if isinstance(payload, str) and payload.strip():
                return payload.strip()
            if not isinstance(payload, dict):
                continue
            for key in ("errorMsg", "error", "message", "msg", "reason"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    @staticmethod
    def _serialize_collateral_snapshot(snapshot: CollateralBalanceSnapshot) -> dict[str, Any]:
        return {
            "balance": float(snapshot.balance) if snapshot.balance is not None else None,
            "allowance": float(snapshot.allowance) if snapshot.allowance is not None else None,
            "available": float(snapshot.available) if snapshot.available is not None else None,
            "funder_address": snapshot.funder_address,
            "signature_type": snapshot.signature_type,
            "raw": snapshot.raw,
        }

    @staticmethod
    def _serialize_response(response: Any) -> Any:
        if isinstance(response, dict):
            return response
        if response is None:
            return None
        return {"raw": str(response)}

    @staticmethod
    def _normalize_exception_message(exc: Exception) -> str:
        message = str(exc).strip()
        return message or exc.__class__.__name__

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
