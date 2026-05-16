"""Unit tests for generated models — validation, serialization, extra fields."""

from __future__ import annotations

import pytest

from pykalshi.models.enums import ExchangeInstance, OrderStatus, SelfTradePreventionType
from pykalshi.models.core import Order, ExchangeStatus, PriceRange
from pykalshi.models.responses import CreateOrderResponse, GetOrdersResponse


class TestEnums:
    def test_order_status_values(self) -> None:
        assert OrderStatus.RESTING == "resting"
        assert OrderStatus.CANCELED == "canceled"
        assert OrderStatus.EXECUTED == "executed"

    def test_exchange_instance_values(self) -> None:
        assert ExchangeInstance.EVENT_CONTRACT == "event_contract"
        assert ExchangeInstance.MARGINED == "margined"

    def test_stp_values(self) -> None:
        assert SelfTradePreventionType.TAKER_AT_CROSS == "taker_at_cross"
        assert SelfTradePreventionType.MAKER == "maker"

    def test_enum_is_str(self) -> None:
        assert isinstance(OrderStatus.RESTING, str)


class TestOrderModel:
    @pytest.fixture
    def order_dict(self) -> dict:
        return {
            "order_id": "abc-123",
            "user_id": "user-1",
            "client_order_id": "client-1",
            "ticker": "KXBTC-100K",
            "side": "yes",
            "action": "buy",
            "outcome_side": "yes",
            "book_side": "bid",
            "type": "limit",
            "status": "resting",
            "yes_price_dollars": "0.56",
            "no_price_dollars": "0.44",
            "fill_count_fp": "0.00",
            "remaining_count_fp": "10.00",
            "initial_count_fp": "10.00",
            "taker_fees_dollars": "0.00",
            "maker_fees_dollars": "0.00",
            "taker_fill_cost_dollars": "0.00",
            "maker_fill_cost_dollars": "0.00",
        }

    def test_from_dict(self, order_dict: dict) -> None:
        order = Order(**order_dict)
        assert order.order_id == "abc-123"
        assert order.ticker == "KXBTC-100K"
        assert order.type_ == "limit"  # aliased from "type"

    def test_extra_fields_ignored(self, order_dict: dict) -> None:
        order_dict["unknown_new_field"] = "should_be_ignored"
        order = Order(**order_dict)
        assert order.order_id == "abc-123"

    def test_optional_fields_default_none(self, order_dict: dict) -> None:
        order = Order(**order_dict)
        assert order.expiration_time is None
        assert order.order_group_id is None


class TestResponseWrappers:
    def test_create_order_response(self) -> None:
        data = {
            "order": {
                "order_id": "x",
                "user_id": "u",
                "client_order_id": "c",
                "ticker": "T",
                "side": "yes",
                "action": "buy",
                "outcome_side": "yes",
                "book_side": "bid",
                "type": "limit",
                "status": "resting",
                "yes_price_dollars": "1.00",
                "no_price_dollars": "0.00",
                "fill_count_fp": "0.00",
                "remaining_count_fp": "1.00",
                "initial_count_fp": "1.00",
                "taker_fees_dollars": "0.00",
                "maker_fees_dollars": "0.00",
                "taker_fill_cost_dollars": "0.00",
                "maker_fill_cost_dollars": "0.00",
            }
        }
        resp = CreateOrderResponse(**data)
        assert resp.order.order_id == "x"

    def test_get_orders_response(self) -> None:
        data = {"orders": [], "cursor": "next-page"}
        resp = GetOrdersResponse(**data)
        assert resp.orders == []
        assert resp.cursor == "next-page"


class TestExchangeStatus:
    def test_construction(self) -> None:
        status = ExchangeStatus(exchange_active=True, trading_active=True)
        assert status.exchange_active is True
        assert status.trading_active is True

    def test_optional_resume_time(self) -> None:
        status = ExchangeStatus(
            exchange_active=False,
            trading_active=False,
            exchange_estimated_resume_time="2025-01-01T00:00:00Z",
        )
        assert status.exchange_estimated_resume_time is not None


class TestPriceRange:
    def test_construction(self) -> None:
        pr = PriceRange(start="0.01", end="0.99", step="0.01")
        assert pr.start == "0.01"
        assert pr.end == "0.99"
        assert pr.step == "0.01"
