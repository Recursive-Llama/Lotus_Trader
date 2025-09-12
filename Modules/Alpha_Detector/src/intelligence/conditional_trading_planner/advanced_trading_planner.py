"""
Advanced Trading Planner

Phase 3: Advanced trading plan generation with market regime detection,
dynamic adaptation, and A/B testing capabilities.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum


class MarketRegime(Enum):
    """Market regime classifications for adaptive trading plans."""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING = "trending"
    RANGING = "ranging"


class PlanType(Enum):
    """Trading plan types for different market conditions."""
    BASIC_CONDITIONAL = "basic_conditional"
    ADVANCED_CONDITIONAL = "advanced_conditional"
    RISK_MANAGED = "risk_managed"
    DYNAMIC_ADAPTIVE = "dynamic_adaptive"
    MARKET_REGIME_SPECIFIC = "market_regime_specific"


class AdvancedTradingPlanner:
    """
    Advanced trading planner with market regime detection and dynamic adaptation.
    
    Phase 3 Features:
    1. Market regime detection
    2. Dynamic plan adaptation
    3. A/B testing framework
    4. Advanced risk management
    5. Performance-based plan evolution
    """
    
    def __init__(self, supabase_manager, llm_client):
        """
        Initialize advanced trading planner.
        
        Args:
            supabase_manager: Database manager for strand operations
            llm_client: LLM client for analysis
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.advanced_planner")
        
        # Market regime detection parameters
        self.regime_detection_window = 30  # days
        self.volatility_threshold = 0.02  # 2% daily volatility
        self.trend_threshold = 0.05  # 5% trend strength
        
        # A/B testing parameters
        self.ab_test_duration = 7  # days
        self.min_sample_size = 10  # minimum trades per variant
        
        self.logger.info("Advanced Trading Planner initialized")
    
    async def create_adaptive_trading_plan(self, analysis: Dict[str, Any]) -> Optional[str]:
        """
        Create an adaptive trading plan based on current market regime and historical performance.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            
        Returns:
            ID of created adaptive trading plan, or None if failed
        """
        try:
            self.logger.info(f"Creating adaptive trading plan for: {analysis.get('prediction_review_id')}")
            
            # Step 1: Detect current market regime
            market_regime = await self._detect_market_regime(analysis)
            
            # Step 2: Analyze historical performance by regime
            regime_performance = await self._analyze_regime_performance(analysis, market_regime)
            
            # Step 3: Generate regime-specific trading rules
            trading_rules = await self._generate_regime_specific_rules(analysis, market_regime, regime_performance)
            
            # Step 4: Create adaptive management rules
            management_rules = await self._create_adaptive_management_rules(analysis, market_regime)
            
            # Step 5: Generate performance expectations
            performance_expectations = self._generate_adaptive_expectations(analysis, market_regime, regime_performance)
            
            # Step 6: Create A/B testing variants if applicable
            ab_variants = await self._create_ab_test_variants(analysis, trading_rules, management_rules)
            
            # Step 7: Create adaptive trading plan strand
            plan_id = await self._create_adaptive_plan_strand(
                analysis, market_regime, trading_rules, management_rules, 
                performance_expectations, ab_variants
            )
            
            if plan_id:
                self.logger.info(f"Created adaptive trading plan: {plan_id}")
            
            return plan_id
            
        except Exception as e:
            self.logger.error(f"Error creating adaptive trading plan: {e}")
            return None
    
    async def _detect_market_regime(self, analysis: Dict[str, Any]) -> MarketRegime:
        """
        Detect current market regime based on recent price action and volatility.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            
        Returns:
            Detected market regime
        """
        try:
            pattern_info = analysis.get('pattern_info', {})
            asset = pattern_info.get('asset', 'BTC')
            
            # Query recent price data for regime detection
            # This would typically come from a price data API
            # For now, we'll use a simplified detection based on historical performance
            
            historical_performance = analysis.get('historical_performance', {})
            
            # Analyze volatility from historical data
            volatility_scores = []
            trend_scores = []
            
            for cluster_name, metrics in historical_performance.items():
                if isinstance(metrics, dict):
                    # Calculate volatility proxy from max drawdown
                    max_drawdown = abs(metrics.get('avg_drawdown', 0))
                    volatility_scores.append(max_drawdown)
                    
                    # Calculate trend proxy from success rate and returns
                    success_rate = metrics.get('success_rate', 0.5)
                    avg_return = metrics.get('avg_return', 0)
                    trend_score = success_rate * avg_return
                    trend_scores.append(trend_score)
            
            # Determine regime based on aggregated metrics
            avg_volatility = sum(volatility_scores) / len(volatility_scores) if volatility_scores else 0.02
            avg_trend = sum(trend_scores) / len(trend_scores) if trend_scores else 0
            
            if avg_volatility > self.volatility_threshold:
                return MarketRegime.HIGH_VOLATILITY
            elif avg_volatility < self.volatility_threshold * 0.5:
                return MarketRegime.LOW_VOLATILITY
            elif avg_trend > self.trend_threshold:
                return MarketRegime.BULL_MARKET
            elif avg_trend < -self.trend_threshold:
                return MarketRegime.BEAR_MARKET
            else:
                return MarketRegime.SIDEWAYS
                
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return MarketRegime.SIDEWAYS
    
    async def _analyze_regime_performance(self, analysis: Dict[str, Any], market_regime: MarketRegime) -> Dict[str, Any]:
        """
        Analyze historical performance for the detected market regime.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            market_regime: Detected market regime
            
        Returns:
            Regime-specific performance metrics
        """
        try:
            pattern_info = analysis.get('pattern_info', {})
            asset = pattern_info.get('asset', 'BTC')
            
            # Query historical data filtered by regime characteristics
            # This would typically involve more sophisticated regime classification
            # For now, we'll use the existing historical performance data
            
            historical_performance = analysis.get('historical_performance', {})
            
            # Filter and analyze performance for this regime
            regime_metrics = {
                "regime": market_regime.value,
                "total_trades": 0,
                "success_rate": 0.0,
                "avg_return": 0.0,
                "avg_drawdown": 0.0,
                "avg_duration": 0.0,
                "rr_ratio": 0.0
            }
            
            # Aggregate metrics from all relevant clusters
            all_metrics = [metrics for metrics in historical_performance.values() 
                          if isinstance(metrics, dict)]
            
            if all_metrics:
                regime_metrics.update({
                    "total_trades": sum(m.get('total_reviews', 0) for m in all_metrics),
                    "success_rate": sum(m.get('success_rate', 0) for m in all_metrics) / len(all_metrics),
                    "avg_return": sum(m.get('avg_return', 0) for m in all_metrics) / len(all_metrics),
                    "avg_drawdown": sum(m.get('avg_drawdown', 0) for m in all_metrics) / len(all_metrics),
                    "avg_duration": sum(m.get('avg_duration', 0) for m in all_metrics) / len(all_metrics)
                })
                
                # Calculate R/R ratio
                if regime_metrics['avg_drawdown'] > 0:
                    regime_metrics['rr_ratio'] = abs(regime_metrics['avg_return'] / regime_metrics['avg_drawdown'])
            
            return regime_metrics
            
        except Exception as e:
            self.logger.error(f"Error analyzing regime performance: {e}")
            return {"regime": market_regime.value, "error": str(e)}
    
    async def _generate_regime_specific_rules(self, analysis: Dict[str, Any], 
                                            market_regime: MarketRegime, 
                                            regime_performance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading rules specific to the detected market regime.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            market_regime: Detected market regime
            regime_performance: Regime-specific performance metrics
            
        Returns:
            Regime-specific trading rules
        """
        try:
            pattern_info = analysis.get('pattern_info', {})
            
            # Base trading rules
            base_rules = {
                "direction": "long",
                "entry_condition": "price_breaks_above_support_level",
                "stop_loss": "2%_below_entry",
                "target_price": "6%_above_entry"
            }
            
            # Regime-specific adaptations
            if market_regime == MarketRegime.HIGH_VOLATILITY:
                base_rules.update({
                    "stop_loss": "3%_below_entry",  # Wider stops in high volatility
                    "target_price": "8%_above_entry",  # Higher targets
                    "entry_condition": "price_breaks_above_support_with_volume_confirmation",
                    "risk_multiplier": 0.5  # Reduce position size
                })
            elif market_regime == MarketRegime.LOW_VOLATILITY:
                base_rules.update({
                    "stop_loss": "1.5%_below_entry",  # Tighter stops
                    "target_price": "4%_above_entry",  # Lower targets
                    "entry_condition": "price_breaks_above_support_level",
                    "risk_multiplier": 1.2  # Increase position size
                })
            elif market_regime == MarketRegime.BULL_MARKET:
                base_rules.update({
                    "direction": "long",
                    "entry_condition": "price_breaks_above_resistance_level",
                    "target_price": "resistance_level_plus_2%",
                    "risk_multiplier": 1.0
                })
            elif market_regime == MarketRegime.BEAR_MARKET:
                base_rules.update({
                    "direction": "short",  # Consider shorting in bear market
                    "entry_condition": "price_breaks_below_support_level",
                    "target_price": "support_level_minus_2%",
                    "risk_multiplier": 0.8
                })
            elif market_regime == MarketRegime.SIDEWAYS:
                base_rules.update({
                    "entry_condition": "price_bounces_off_support_level",
                    "target_price": "resistance_level",
                    "stop_loss": "1%_below_support",
                    "risk_multiplier": 0.9
                })
            
            # Add regime-specific risk management
            base_rules["regime_specific_rules"] = {
                "market_regime": market_regime.value,
                "regime_confidence": regime_performance.get('success_rate', 0.5),
                "adaptive_stop_loss": True,
                "regime_exit_condition": f"if_regime_changes_to_{MarketRegime.BEAR_MARKET.value}_exit_immediately"
            }
            
            return base_rules
            
        except Exception as e:
            self.logger.error(f"Error generating regime-specific rules: {e}")
            return {}
    
    async def _create_adaptive_management_rules(self, analysis: Dict[str, Any], 
                                              market_regime: MarketRegime) -> Dict[str, str]:
        """
        Create adaptive management rules based on market regime.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            market_regime: Detected market regime
            
        Returns:
            Adaptive management rules
        """
        try:
            management_rules = {}
            
            # Base management rules
            base_rules = {
                "if_breaks_resistance": "move_stop_to_breakeven",
                "if_reversal_pattern": "exit_early",
                "if_volume_spikes_again": "take_50%_profit"
            }
            
            # Regime-specific management rules
            if market_regime == MarketRegime.HIGH_VOLATILITY:
                management_rules.update({
                    "if_price_drops_2%": "reduce_position_by_50%",
                    "if_volatility_increases": "tighten_stop_loss",
                    "if_gap_up": "take_75%_profit_immediately",
                    "if_gap_down": "exit_immediately"
                })
            elif market_regime == MarketRegime.LOW_VOLATILITY:
                management_rules.update({
                    "if_price_drops_1%": "add_position_at_lower_support",
                    "if_breaks_resistance": "trail_stop_1%_below_price",
                    "if_sideways_for_2_hours": "exit_early"
                })
            elif market_regime == MarketRegime.BULL_MARKET:
                management_rules.update({
                    "if_breaks_resistance": "trail_stop_2%_below_price",
                    "if_new_high": "take_25%_profit_move_stop_breakeven",
                    "if_volume_decreases": "take_50%_profit"
                })
            elif market_regime == MarketRegime.BEAR_MARKET:
                management_rules.update({
                    "if_breaks_support": "exit_immediately",
                    "if_any_green_candle": "take_50%_profit",
                    "if_volume_spikes": "exit_immediately"
                })
            elif market_regime == MarketRegime.SIDEWAYS:
                management_rules.update({
                    "if_breaks_range": "exit_immediately",
                    "if_approaches_resistance": "take_75%_profit",
                    "if_approaches_support": "add_position"
                })
            
            # Add base rules
            management_rules.update(base_rules)
            
            return management_rules
            
        except Exception as e:
            self.logger.error(f"Error creating adaptive management rules: {e}")
            return {}
    
    def _generate_adaptive_expectations(self, analysis: Dict[str, Any], 
                                      market_regime: MarketRegime, 
                                      regime_performance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate adaptive performance expectations based on market regime.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            market_regime: Detected market regime
            regime_performance: Regime-specific performance metrics
            
        Returns:
            Adaptive performance expectations
        """
        try:
            # Base expectations
            base_expectations = {
                "success_rate": 0.5,
                "avg_return": 0.03,
                "r_r_ratio": 2.0,
                "avg_duration_hours": 4.0
            }
            
            # Use regime performance if available
            if regime_performance and not regime_performance.get('error'):
                base_expectations.update({
                    "success_rate": regime_performance.get('success_rate', 0.5),
                    "avg_return": regime_performance.get('avg_return', 0.03),
                    "r_r_ratio": regime_performance.get('rr_ratio', 2.0),
                    "avg_duration_hours": regime_performance.get('avg_duration', 4.0)
                })
            
            # Regime-specific adjustments
            if market_regime == MarketRegime.HIGH_VOLATILITY:
                base_expectations["avg_return"] *= 1.5  # Higher potential returns
                base_expectations["success_rate"] *= 0.8  # Lower success rate
                base_expectations["avg_duration_hours"] *= 0.7  # Shorter duration
            elif market_regime == MarketRegime.LOW_VOLATILITY:
                base_expectations["avg_return"] *= 0.7  # Lower returns
                base_expectations["success_rate"] *= 1.2  # Higher success rate
                base_expectations["avg_duration_hours"] *= 1.3  # Longer duration
            elif market_regime == MarketRegime.BULL_MARKET:
                base_expectations["success_rate"] *= 1.3  # Higher success rate
                base_expectations["avg_return"] *= 1.2  # Higher returns
            elif market_regime == MarketRegime.BEAR_MARKET:
                base_expectations["success_rate"] *= 0.6  # Lower success rate
                base_expectations["avg_return"] *= 0.5  # Lower returns
            
            # Add regime-specific metadata
            base_expectations["market_regime"] = market_regime.value
            base_expectations["regime_confidence"] = regime_performance.get('success_rate', 0.5)
            base_expectations["adaptive_expectations"] = True
            
            return base_expectations
            
        except Exception as e:
            self.logger.error(f"Error generating adaptive expectations: {e}")
            return base_expectations
    
    async def _create_ab_test_variants(self, analysis: Dict[str, Any], 
                                     trading_rules: Dict[str, Any], 
                                     management_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create A/B testing variants for trading plan optimization.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            trading_rules: Base trading rules
            management_rules: Base management rules
            
        Returns:
            List of A/B test variants
        """
        try:
            variants = []
            
            # Variant A: Conservative approach
            variant_a = {
                "variant_id": "conservative",
                "description": "Conservative risk management",
                "trading_rules": {
                    **trading_rules,
                    "stop_loss": f"{float(trading_rules.get('stop_loss', '2%').replace('%_below_entry', '')) * 0.8}%_below_entry",
                    "target_price": f"{float(trading_rules.get('target_price', '6%').replace('%_above_entry', '')) * 0.8}%_above_entry",
                    "risk_multiplier": trading_rules.get('risk_multiplier', 1.0) * 0.8
                },
                "management_rules": {
                    **management_rules,
                    "if_price_drops_1%": "take_25%_profit",
                    "if_breaks_resistance": "take_50%_profit_move_stop_breakeven"
                }
            }
            
            # Variant B: Aggressive approach
            variant_b = {
                "variant_id": "aggressive",
                "description": "Aggressive profit taking",
                "trading_rules": {
                    **trading_rules,
                    "stop_loss": f"{float(trading_rules.get('stop_loss', '2%').replace('%_below_entry', '')) * 1.2}%_below_entry",
                    "target_price": f"{float(trading_rules.get('target_price', '6%').replace('%_above_entry', '')) * 1.2}%_above_entry",
                    "risk_multiplier": trading_rules.get('risk_multiplier', 1.0) * 1.2
                },
                "management_rules": {
                    **management_rules,
                    "if_price_drops_1%": "add_position_at_lower_support",
                    "if_breaks_resistance": "trail_stop_1%_below_price"
                }
            }
            
            # Variant C: Balanced approach (control)
            variant_c = {
                "variant_id": "balanced",
                "description": "Balanced risk-reward",
                "trading_rules": trading_rules,
                "management_rules": management_rules
            }
            
            variants = [variant_a, variant_b, variant_c]
            
            return variants
            
        except Exception as e:
            self.logger.error(f"Error creating A/B test variants: {e}")
            return []
    
    async def _create_adaptive_plan_strand(self, analysis: Dict[str, Any], 
                                         market_regime: MarketRegime,
                                         trading_rules: Dict[str, Any], 
                                         management_rules: Dict[str, Any],
                                         performance_expectations: Dict[str, Any],
                                         ab_variants: List[Dict[str, Any]]) -> Optional[str]:
        """
        Create and store adaptive trading plan strand in database.
        
        Args:
            analysis: Analysis data
            market_regime: Detected market regime
            trading_rules: Regime-specific trading rules
            management_rules: Adaptive management rules
            performance_expectations: Adaptive performance expectations
            ab_variants: A/B test variants
            
        Returns:
            ID of created strand, or None if failed
        """
        try:
            pattern_info = analysis.get('pattern_info', {})
            
            # Generate unique plan ID
            plan_id = f"ctp_adaptive_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Create adaptive trading plan data
            adaptive_plan_data = {
                "id": plan_id,
                "module": "ctp",
                "kind": "conditional_trading_plan",
                "symbol": pattern_info.get('asset', 'UNKNOWN'),
                "timeframe": pattern_info.get('timeframe', '1h'),
                "tags": ['ctp', 'trading_plan', 'conditional', 'adaptive', market_regime.value],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "braid_level": 1,
                "lesson": "",
                "content": {
                    "plan_id": plan_id,
                    "plan_type": "adaptive",
                    "market_regime": market_regime.value,
                    "trigger_conditions": {
                        "group_signature": pattern_info.get('group_signature', 'unknown'),
                        "min_confidence": pattern_info.get('confidence', 0.7),
                        "min_pattern_count": 2,
                        "regime_conditions": {
                            "required_regime": market_regime.value,
                            "regime_confidence_threshold": 0.6
                        }
                    },
                    "trading_rules": trading_rules,
                    "management_rules": management_rules,
                    "performance_expectations": performance_expectations,
                    "ab_test_variants": ab_variants,
                    "source_prediction_review": analysis.get('prediction_review_id'),
                    "created_at": datetime.now(timezone.utc).isoformat()
                },
                "module_intelligence": {
                    "plan_type": "adaptive_conditional_trading_plan",
                    "market_regime": market_regime.value,
                    "pattern_info": pattern_info,
                    "historical_performance": analysis.get('historical_performance', {}),
                    "regime_performance": performance_expectations,
                    "confidence": pattern_info.get('confidence', 0.0),
                    "adaptive_features": {
                        "regime_detection": True,
                        "dynamic_adaptation": True,
                        "ab_testing": len(ab_variants) > 0,
                        "risk_management": True
                    }
                },
                "cluster_key": []  # Will be populated by learning system if needed
            }
            
            # Store in database
            result = self.supabase_manager.insert_strand(adaptive_plan_data)
            
            if result:
                return plan_id
            else:
                self.logger.error(f"Failed to store adaptive trading plan: {plan_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating adaptive plan strand: {e}")
            return None
