"""Minimal valid mock data for Pydantic model-validated tests."""

MOCK_ORDER = {
    "order_id": "ord-123",
    "user_id": "usr-1",
    "client_order_id": "cli-1",
    "ticker": "KXBTC-100K",
    "side": "yes",
    "action": "buy",
    "type": "limit",
    "status": "resting",
    "yes_price_dollars": "0.50",
    "no_price_dollars": "0.50",
    "fill_count_fp": "0",
    "remaining_count_fp": "10",
    "initial_count_fp": "10",
    "taker_fill_cost_dollars": "0.00",
    "maker_fill_cost_dollars": "0.00",
    "taker_fees_dollars": "0.00",
    "maker_fees_dollars": "0.00",
}

MOCK_MARKET = {
    "ticker": "KXBTC-100K",
    "event_ticker": "KXBTC",
    "market_type": "binary",
    "yes_sub_title": "Yes",
    "no_sub_title": "No",
    "created_time": "2024-01-01T00:00:00Z",
    "updated_time": "2024-01-01T00:00:00Z",
    "open_time": "2024-01-01T00:00:00Z",
    "close_time": "2024-12-31T00:00:00Z",
    "latest_expiration_time": "2024-12-31T00:00:00Z",
    "settlement_timer_seconds": 3600,
    "status": "open",
    "yes_bid_dollars": "0.45",
    "yes_bid_size_fp": "100",
    "yes_ask_dollars": "0.55",
    "yes_ask_size_fp": "100",
    "no_bid_dollars": "0.45",
    "no_ask_dollars": "0.55",
    "last_price_dollars": "0.50",
    "volume_fp": "1000",
    "volume_24h_fp": "500",
    "result": "",
    "can_close_early": False,
    "fractional_trading_enabled": True,
    "open_interest_fp": "500",
    "notional_value_dollars": "1.00",
    "previous_yes_bid_dollars": "0.44",
    "previous_yes_ask_dollars": "0.56",
    "previous_price_dollars": "0.49",
    "liquidity_dollars": "0.0000",
    "expiration_value": "",
    "rules_primary": "If BTC > 100K, resolves Yes.",
    "rules_secondary": "Settlement per official sources.",
    "price_level_structure": "standard",
    "price_ranges": [{"start": "0.01", "end": "0.99", "step": "0.01"}],
}

MOCK_FILL = {
    "trade_id": "t-1",
    "order_id": "ord-1",
    "ticker": "KXBTC-100K",
    "side": "yes",
    "action": "buy",
    "type": "limit",
    "count_fp": "10",
    "yes_price_dollars": "0.50",
    "no_price_dollars": "0.50",
    "is_taker": True,
    "created_time": "2024-01-01T00:00:00Z",
}

MOCK_SETTLEMENT = {
    "market_result": "yes",
    "ticker": "KXBTC-100K",
    "event_ticker": "KXBTC",
    "no_count_fp": "0",
    "no_total_cost_dollars": "0.00",
    "yes_count_fp": "10",
    "yes_total_cost_dollars": "5.00",
    "revenue": 1000,
    "settled_time": "2024-01-01T00:00:00Z",
    "fee_cost": "0.00",
}

MOCK_SERIES = {
    "ticker": "KXBTC",
    "frequency": "daily",
    "title": "BTC Price",
    "category": "Crypto",
    "fee_type": "quadratic",
    "fee_multiplier": 1.0,
}

MOCK_EVENT = {
    "event_ticker": "EVT-1",
    "series_ticker": "KXBTC",
    "sub_title": "BTC > 100K",
    "title": "Will BTC exceed 100K?",
    "collateral_return_type": "binary",
    "mutually_exclusive": True,
    "available_on_brokers": True,
}

MOCK_MILESTONE = {
    "id": "ms-1",
    "category": "Sports",
    "type": "football_game",
    "start_date": "2024-01-01",
    "related_event_tickers": ["EVT-1"],
    "title": "NFL Game",
    "notification_message": "Game starting",
    "details": {},
    "primary_event_tickers": ["EVT-1"],
    "last_updated_ts": "2024-01-01T00:00:00Z",
}

MOCK_LIVE_DATA = {
    "type": "football_game",
    "details": {},
    "milestone_id": "ms-1",
}

MOCK_TRADE = {
    "ticker": "KXBTC-100K",
    "trade_id": "t-1",
    "count_fp": "10",
    "yes_price_dollars": "0.50",
    "no_price_dollars": "0.50",
    "taker_side": "yes",
    "created_time": "2024-01-01T00:00:00Z",
}
