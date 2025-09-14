"""
Trading Plan Data Models
Phase 1.4.3: Data structures for trading plans and signal packs
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import uuid


@dataclass
class TradingPlan:
    """Complete trading plan data structure"""
    plan_id: str
    signal_id: str
    symbol: str
    timeframe: str
    direction: str
    entry_conditions: Dict[str, Any]
    entry_price: Decimal
    position_size: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    risk_reward_ratio: Decimal
    confidence_score: float
    strength_score: float
    time_horizon: str
    valid_until: datetime
    created_at: datetime
    market_context: Dict[str, Any]
    signal_metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate trading plan data after initialization"""
        if self.risk_reward_ratio < 1.0:
            raise ValueError(f"Risk-reward ratio must be >= 1.0, got {self.risk_reward_ratio}")
        
        if self.position_size <= 0:
            raise ValueError(f"Position size must be > 0, got {self.position_size}")
        
        if self.entry_price <= 0:
            raise ValueError(f"Entry price must be > 0, got {self.entry_price}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trading plan to dictionary for serialization"""
        return {
            'plan_id': self.plan_id,
            'signal_id': self.signal_id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'direction': self.direction,
            'entry_conditions': self.entry_conditions,
            'entry_price': float(self.entry_price),
            'position_size': float(self.position_size),
            'stop_loss': float(self.stop_loss),
            'take_profit': float(self.take_profit),
            'risk_reward_ratio': float(self.risk_reward_ratio),
            'confidence_score': self.confidence_score,
            'strength_score': self.strength_score,
            'time_horizon': self.time_horizon,
            'valid_until': self.valid_until.isoformat(),
            'created_at': self.created_at.isoformat(),
            'market_context': self.market_context,
            'signal_metadata': self.signal_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingPlan':
        """Create TradingPlan from dictionary"""
        return cls(
            plan_id=data['plan_id'],
            signal_id=data['signal_id'],
            symbol=data['symbol'],
            timeframe=data['timeframe'],
            direction=data['direction'],
            entry_conditions=data['entry_conditions'],
            entry_price=Decimal(str(data['entry_price'])),
            position_size=Decimal(str(data['position_size'])),
            stop_loss=Decimal(str(data['stop_loss'])),
            take_profit=Decimal(str(data['take_profit'])),
            risk_reward_ratio=Decimal(str(data['risk_reward_ratio'])),
            confidence_score=data['confidence_score'],
            strength_score=data['strength_score'],
            time_horizon=data['time_horizon'],
            valid_until=datetime.fromisoformat(data['valid_until']),
            created_at=datetime.fromisoformat(data['created_at']),
            market_context=data['market_context'],
            signal_metadata=data['signal_metadata']
        )


@dataclass
class SignalPack:
    """LLM-ready signal pack with all context"""
    pack_id: str
    signal_id: str
    trading_plan_id: str
    features: Dict[str, Any]
    patterns: Dict[str, Any]
    regime: Dict[str, Any]
    market_context: Dict[str, Any]
    processing_metadata: Dict[str, Any]
    llm_format: Dict[str, Any]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal pack to dictionary for serialization"""
        return {
            'pack_id': self.pack_id,
            'signal_id': self.signal_id,
            'trading_plan_id': self.trading_plan_id,
            'features': self.features,
            'patterns': self.patterns,
            'regime': self.regime,
            'market_context': self.market_context,
            'processing_metadata': self.processing_metadata,
            'llm_format': self.llm_format,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignalPack':
        """Create SignalPack from dictionary"""
        return cls(
            pack_id=data['pack_id'],
            signal_id=data['signal_id'],
            trading_plan_id=data['trading_plan_id'],
            features=data['features'],
            patterns=data['patterns'],
            regime=data['regime'],
            market_context=data['market_context'],
            processing_metadata=data['processing_metadata'],
            llm_format=data['llm_format'],
            created_at=datetime.fromisoformat(data['created_at'])
        )


@dataclass
class RiskMetrics:
    """Risk management metrics"""
    position_size: Decimal
    risk_amount: Decimal
    risk_percentage: float
    stop_loss_distance: Decimal
    take_profit_distance: Decimal
    risk_reward_ratio: Decimal
    max_drawdown: float
    volatility_adjustment: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert risk metrics to dictionary"""
        return {
            'position_size': float(self.position_size),
            'risk_amount': float(self.risk_amount),
            'risk_percentage': self.risk_percentage,
            'stop_loss_distance': float(self.stop_loss_distance),
            'take_profit_distance': float(self.take_profit_distance),
            'risk_reward_ratio': float(self.risk_reward_ratio),
            'max_drawdown': self.max_drawdown,
            'volatility_adjustment': self.volatility_adjustment
        }


@dataclass
class ExecutionParameters:
    """Execution-specific parameters"""
    entry_strategy: str
    execution_venue: str
    order_type: str
    time_in_force: str
    slippage_tolerance: float
    execution_priority: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert execution parameters to dictionary"""
        return {
            'entry_strategy': self.entry_strategy,
            'execution_venue': self.execution_venue,
            'order_type': self.order_type,
            'time_in_force': self.time_in_force,
            'slippage_tolerance': self.slippage_tolerance,
            'execution_priority': self.execution_priority
        }


@dataclass
class MarketContext:
    """Market context information"""
    current_price: Decimal
    volume_24h: Decimal
    volatility_24h: float
    market_cap: Optional[Decimal] = None
    sector: Optional[str] = None
    correlation_btc: Optional[float] = None
    news_sentiment: Optional[float] = None
    market_regime: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert market context to dictionary"""
        return {
            'current_price': float(self.current_price),
            'volume_24h': float(self.volume_24h),
            'volatility_24h': self.volatility_24h,
            'market_cap': float(self.market_cap) if self.market_cap else None,
            'sector': self.sector,
            'correlation_btc': self.correlation_btc,
            'news_sentiment': self.news_sentiment,
            'market_regime': self.market_regime
        }


def generate_plan_id() -> str:
    """Generate unique trading plan ID"""
    return f"tp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def generate_pack_id() -> str:
    """Generate unique signal pack ID"""
    return f"sp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def calculate_time_horizon(timeframe: str) -> str:
    """Calculate appropriate time horizon based on signal timeframe"""
    horizon_mapping = {
        '1m': '5m',
        '5m': '15m', 
        '15m': '1h',
        '1h': '4h',
        '4h': '1d',
        '1d': '1w'
    }
    return horizon_mapping.get(timeframe, '1h')


def calculate_valid_until(timeframe: str) -> datetime:
    """Calculate when trading plan expires based on timeframe"""
    now = datetime.now()
    validity_mapping = {
        '1m': timedelta(minutes=5),
        '5m': timedelta(minutes=15),
        '15m': timedelta(hours=1),
        '1h': timedelta(hours=4),
        '4h': timedelta(days=1),
        '1d': timedelta(days=7)
    }
    validity = validity_mapping.get(timeframe, timedelta(hours=1))
    return now + validity


if __name__ == "__main__":
    # Test the data models
    print("🧪 Testing Trading Plan Data Models...")
    
    # Test TradingPlan creation
    plan = TradingPlan(
        plan_id=generate_plan_id(),
        signal_id="test_signal_123",
        symbol="BTC",
        timeframe="1h",
        direction="long",
        entry_conditions={"price_above": 50000, "volume_spike": True},
        entry_price=Decimal("50000.00"),
        position_size=Decimal("0.1"),
        stop_loss=Decimal("49000.00"),
        take_profit=Decimal("52000.00"),
        risk_reward_ratio=Decimal("2.0"),
        confidence_score=0.75,
        strength_score=0.65,
        time_horizon="4h",
        valid_until=calculate_valid_until("1h"),
        created_at=datetime.now(),
        market_context={"volatility": 0.02, "trend": "up"},
        signal_metadata={"source": "multi_timeframe", "confirmations": 3}
    )
    
    print(f"✅ TradingPlan created: {plan.plan_id}")
    print(f"   Symbol: {plan.symbol}, Direction: {plan.direction}")
    print(f"   Entry: ${plan.entry_price}, Stop: ${plan.stop_loss}, Target: ${plan.take_profit}")
    print(f"   Risk-Reward: {plan.risk_reward_ratio}")
    
    # Test SignalPack creation
    pack = SignalPack(
        pack_id=generate_pack_id(),
        signal_id="test_signal_123",
        trading_plan_id=plan.plan_id,
        features={"rsi": 45.0, "macd": 0.001},
        patterns={"breakout": True, "support": 49000},
        regime={"trend": "up", "volatility": "normal"},
        market_context={"price": 50000, "volume": 1000000},
        processing_metadata={"processing_time": 0.05, "quality_score": 0.85},
        llm_format={"summary": "Strong bullish signal with volume confirmation"},
        created_at=datetime.now()
    )
    
    print(f"✅ SignalPack created: {pack.pack_id}")
    print(f"   Features: {len(pack.features)} items")
    print(f"   LLM Format: {pack.llm_format}")
    
    # Test serialization
    plan_dict = plan.to_dict()
    pack_dict = pack.to_dict()
    
    print("✅ Serialization working")
    print(f"   Plan dict keys: {list(plan_dict.keys())}")
    print(f"   Pack dict keys: {list(pack_dict.keys())}")
    
    print("\n🎉 All data models working correctly!")
