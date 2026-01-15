"""
Tests for Mudrex SDK Models
===========================
"""

import pytest
from datetime import datetime
from mudrex.models import (
    WalletBalance,
    FuturesBalance,
    Asset,
    Leverage,
    Order,
    Position,
    OrderType,
    TriggerType,
    MarginType,
    OrderStatus,
)


class TestWalletBalance:
    def test_from_dict(self):
        data = {
            "total": "1000.50",
            "rewards": "10.00",
            "withdrawable": "750.00",
            "invested": "200.00",
        }
        balance = WalletBalance.from_dict(data)
        
        assert balance.total == "1000.50"
        assert balance.rewards == "10.00"
        assert balance.withdrawable == "750.00"
        assert balance.invested == "200.00"
        # available is a property that returns withdrawable
        assert balance.available == "750.00"
    
    def test_from_dict_defaults(self):
        data = {}
        balance = WalletBalance.from_dict(data)
        
        assert balance.total == "0"
        assert balance.withdrawable == "0"
        # available is a property that returns withdrawable
        assert balance.available == "0"
    
    def test_available_property(self):
        """Test that available property returns withdrawable value."""
        data = {
            "total": "500.00",
            "withdrawable": "300.00",
        }
        balance = WalletBalance.from_dict(data)
        
        # The available property should return the same value as withdrawable
        assert balance.available == balance.withdrawable
        assert balance.available == "300.00"


class TestAsset:
    def test_from_dict(self):
        data = {
            "asset_id": "BTCUSDT",
            "symbol": "BTCUSDT",
            "base_currency": "BTC",
            "quote_currency": "USDT",
            "min_quantity": "0.001",
            "max_quantity": "100",
            "quantity_step": "0.001",
            "min_leverage": "1",
            "max_leverage": "100",
            "maker_fee": "0.02",
            "taker_fee": "0.04",
            "is_active": True
        }
        asset = Asset.from_dict(data)
        
        assert asset.asset_id == "BTCUSDT"
        assert asset.symbol == "BTCUSDT"
        assert asset.base_currency == "BTC"
        assert asset.max_leverage == "100"
    
    def test_from_dict_with_price_step(self):
        """Test that Asset correctly parses price_step from API response.
        
        The API returns price_step (tick size) which is required for 
        proper order price rounding.
        """
        data = {
            "id": "01903a7b-bf65-707d-a7dc-d7b84c3c756c",
            "name": "Bitcoin",
            "symbol": "BTCUSDT",
            "min_contract": "0.001",
            "max_contract": "1190",
            "quantity_step": "0.001",
            "min_price": "0.1",
            "max_price": "1999999.8",
            "price_step": "0.1",
            "min_leverage": "1",
            "max_leverage": "100",
            "trading_fee_perc": "0.1",
            "price": "114550"
        }
        asset = Asset.from_dict(data)
        
        assert asset.price_step == "0.1"
        assert asset.min_price == "0.1"
        assert asset.max_price == "1999999.8"
        assert asset.price == "114550"
        assert asset.name == "Bitcoin"
        # Also verify field mapping for alternative names
        assert asset.min_quantity == "0.001"  # from min_contract
        assert asset.max_quantity == "1190"   # from max_contract


class TestOrder:
    def test_from_dict(self):
        data = {
            "order_id": "ord_12345",
            "asset_id": "BTCUSDT",
            "symbol": "BTCUSDT",
            "order_type": "LONG",
            "trigger_type": "MARKET",
            "status": "FILLED",
            "quantity": "0.001",
            "filled_quantity": "0.001",
            "price": "100000",
            "leverage": "10",
        }
        order = Order.from_dict(data)
        
        assert order.order_id == "ord_12345"
        assert order.order_type == OrderType.LONG
        assert order.trigger_type == TriggerType.MARKET
        assert order.status == OrderStatus.FILLED
        assert order.leverage == "10"


class TestPosition:
    def test_from_dict(self):
        data = {
            "position_id": "pos_12345",
            "asset_id": "BTCUSDT",
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": "0.001",
            "entry_price": "100000",
            "mark_price": "101000",
            "leverage": "10",
            "margin": "10",
            "unrealized_pnl": "1.00",
            "realized_pnl": "0",
        }
        position = Position.from_dict(data)
        
        assert position.position_id == "pos_12345"
        assert position.side == OrderType.LONG
        assert position.entry_price == "100000"
        assert position.unrealized_pnl == "1.00"
    
    def test_pnl_percentage(self):
        position = Position(
            position_id="pos_123",
            asset_id="BTCUSDT",
            symbol="BTCUSDT",
            side=OrderType.LONG,
            quantity="0.001",
            entry_price="100000",
            mark_price="101000",
            leverage="10",
            margin="10",
            unrealized_pnl="1.00",
            realized_pnl="0",
        )
        
        # PnL = 1.00, Margin = 10, so percentage = 10%
        assert position.pnl_percentage == 10.0
    
    def test_from_dict_with_nested_stoploss(self):
        """Test that Position correctly parses nested stoploss/takeprofit from API response.
        
        The Mudrex API returns SL/TP as nested objects:
        {"stoploss": {"price": "4100", "order_id": "...", "order_type": "SHORT"}}
        """
        data = {
            "id": "pos_12345",
            "symbol": "ETHUSDT",
            "order_type": "LONG",
            "quantity": "0.02",
            "entry_price": "4133.41",
            "mark_price": "4150.00",
            "leverage": "50",
            "margin": "10",
            "unrealized_pnl": "0.33",
            "realized_pnl": "0",
            "liquidation_price": "4071.1",
            "stoploss": {"price": "4100", "order_id": "sl_123", "order_type": "SHORT"},
            "takeprofit": {"price": "5000", "order_id": "tp_123", "order_type": "SHORT"},
            "status": "OPEN"
        }
        position = Position.from_dict(data)
        
        assert position.stoploss_price == "4100"
        assert position.takeprofit_price == "5000"
    
    def test_from_dict_with_flat_stoploss(self):
        """Test backwards compatibility with flat stoploss_price field."""
        data = {
            "id": "pos_12345",
            "symbol": "BTCUSDT",
            "order_type": "SHORT",
            "quantity": "0.001",
            "entry_price": "100000",
            "mark_price": "99000",
            "leverage": "10",
            "margin": "100",
            "unrealized_pnl": "10",
            "realized_pnl": "0",
            "stoploss_price": "101000",
            "takeprofit_price": "95000",
            "status": "OPEN"
        }
        position = Position.from_dict(data)
        
        assert position.stoploss_price == "101000"
        assert position.takeprofit_price == "95000"


class TestEnums:
    def test_order_type(self):
        assert OrderType.LONG.value == "LONG"
        assert OrderType.SHORT.value == "SHORT"
    
    def test_trigger_type(self):
        assert TriggerType.MARKET.value == "MARKET"
        assert TriggerType.LIMIT.value == "LIMIT"
    
    def test_margin_type(self):
        assert MarginType.ISOLATED.value == "ISOLATED"
