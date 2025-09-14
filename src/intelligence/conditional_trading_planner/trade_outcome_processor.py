"""
Trade Outcome Processor

Processes trade outcome strands from the Trader module and prepares them 
for learning system analysis.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class TradeOutcomeProcessor:
    """
    Processes trade outcome strands for learning analysis.
    
    Responsibilities:
    1. Process trade outcome data from Trader module
    2. Compare prediction vs actual performance
    3. Identify execution improvements
    4. Prepare data for learning system
    """
    
    def __init__(self, supabase_manager, llm_client):
        """
        Initialize trade outcome processor.
        
        Args:
            supabase_manager: Database manager for strand operations
            llm_client: LLM client for analysis
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.outcome_processor")
    
    async def process_trade_outcome(self, trade_outcome_id: str) -> Optional[Dict[str, Any]]:
        """
        Process a trade outcome strand and prepare it for learning.
        
        Args:
            trade_outcome_id: ID of the trade outcome strand
            
        Returns:
            Processed trade outcome data, or None if failed
        """
        try:
            self.logger.info(f"Processing trade outcome: {trade_outcome_id}")
            
            # Step 1: Get trade outcome strand
            trade_outcome = await self._get_trade_outcome(trade_outcome_id)
            if not trade_outcome:
                self.logger.error(f"Trade outcome not found: {trade_outcome_id}")
                return None
            
            # Step 2: Extract trade execution data
            execution_data = self._extract_execution_data(trade_outcome)
            
            # Step 3: Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(execution_data)
            
            # Step 4: Analyze execution quality
            execution_analysis = await self._analyze_execution_quality(execution_data, performance_metrics)
            
            # Step 5: Prepare processed data
            processed_data = {
                "trade_outcome_id": trade_outcome_id,
                "execution_data": execution_data,
                "performance_metrics": performance_metrics,
                "execution_analysis": execution_analysis,
                "processing_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.info(f"Trade outcome processed: {trade_outcome_id}")
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing trade outcome {trade_outcome_id}: {e}")
            return None
    
    async def _get_trade_outcome(self, trade_outcome_id: str) -> Optional[Dict[str, Any]]:
        """Get trade outcome strand from database."""
        try:
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('id', trade_outcome_id).eq('kind', 'trade_outcome').execute()
            
            if result.data:
                return result.data[0]
            else:
                self.logger.warning(f"Trade outcome not found: {trade_outcome_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting trade outcome {trade_outcome_id}: {e}")
            return None
    
    def _extract_execution_data(self, trade_outcome: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract trade execution data from trade outcome strand.
        
        Args:
            trade_outcome: Trade outcome strand data
            
        Returns:
            Dictionary with execution data
        """
        try:
            content = trade_outcome.get('content', {})
            module_intelligence = trade_outcome.get('module_intelligence', {})
            
            # Helper function to get value from either field
            def get_value(key: str, default=None):
                if content.get(key) is not None:
                    return content.get(key, default)
                return module_intelligence.get(key, default)
            
            # Extract execution data
            execution_data = {
                "trade_id": get_value('trade_id', 'unknown'),
                "ctp_id": get_value('ctp_id', 'unknown'),
                "asset": get_value('asset', 'unknown'),
                "timeframe": get_value('timeframe', 'unknown'),
                "entry_price": get_value('entry_price', 0.0),
                "entry_time": get_value('entry_time', ''),
                "exit_price": get_value('exit_price', 0.0),
                "exit_time": get_value('exit_time', ''),
                "stop_loss": get_value('stop_loss', 0.0),
                "target_price": get_value('target_price', 0.0),
                "position_size": get_value('position_size', 0.0),
                "execution_method": get_value('execution_method', 'unknown'),
                "slippage": get_value('slippage', 0.0),
                "fees": get_value('fees', 0.0)
            }
            
            return execution_data
            
        except Exception as e:
            self.logger.error(f"Error extracting execution data: {e}")
            return {}
    
    def _calculate_performance_metrics(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate performance metrics from execution data.
        
        Args:
            execution_data: Extracted execution data
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            entry_price = execution_data.get('entry_price', 0)
            exit_price = execution_data.get('exit_price', 0)
            stop_loss = execution_data.get('stop_loss', 0)
            target_price = execution_data.get('target_price', 0)
            
            if entry_price == 0 or exit_price == 0:
                return {"error": "Invalid price data"}
            
            # Calculate return percentage
            return_pct = ((exit_price - entry_price) / entry_price) * 100
            
            # Determine success
            success = return_pct > 0
            
            # Calculate R/R ratio
            if stop_loss > 0 and target_price > 0:
                risk = abs(entry_price - stop_loss) / entry_price * 100
                reward = abs(target_price - entry_price) / entry_price * 100
                rr_ratio = reward / risk if risk > 0 else 0
            else:
                rr_ratio = 0
            
            # Calculate duration
            entry_time = execution_data.get('entry_time', '')
            exit_time = execution_data.get('exit_time', '')
            duration_hours = self._calculate_duration(entry_time, exit_time)
            
            # Calculate max drawdown (simplified)
            max_drawdown = 0
            if stop_loss > 0 and entry_price > stop_loss:
                max_drawdown = abs(entry_price - stop_loss) / entry_price * 100
            
            return {
                "success": success,
                "return_pct": round(return_pct, 3),
                "rr_ratio": round(rr_ratio, 2),
                "duration_hours": round(duration_hours, 2),
                "max_drawdown": round(max_drawdown, 3),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "stop_loss": stop_loss,
                "target_price": target_price
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_duration(self, entry_time: str, exit_time: str) -> float:
        """Calculate trade duration in hours."""
        try:
            if not entry_time or not exit_time:
                return 0.0
            
            # Parse timestamps (assuming ISO format)
            entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            exit_dt = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            
            duration = exit_dt - entry_dt
            return duration.total_seconds() / 3600  # Convert to hours
            
        except Exception as e:
            self.logger.warning(f"Error calculating duration: {e}")
            return 0.0
    
    async def _analyze_execution_quality(self, execution_data: Dict[str, Any], performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze execution quality and identify improvements.
        
        Args:
            execution_data: Trade execution data
            performance_metrics: Calculated performance metrics
            
        Returns:
            Dictionary with execution analysis
        """
        try:
            analysis = {
                "execution_quality": "unknown",
                "improvements": [],
                "insights": []
            }
            
            # Analyze slippage
            slippage = execution_data.get('slippage', 0)
            if slippage > 0.1:  # 0.1% slippage threshold
                analysis["improvements"].append("High slippage detected - consider better execution timing")
                analysis["execution_quality"] = "poor"
            elif slippage < 0.05:
                analysis["execution_quality"] = "excellent"
            else:
                analysis["execution_quality"] = "good"
            
            # Analyze fees
            fees = execution_data.get('fees', 0)
            return_pct = performance_metrics.get('return_pct', 0)
            if fees > abs(return_pct) * 0.1:  # Fees > 10% of return
                analysis["improvements"].append("High fees relative to return - consider fee optimization")
            
            # Analyze timing
            duration_hours = performance_metrics.get('duration_hours', 0)
            if duration_hours > 24:
                analysis["insights"].append("Long duration trade - consider shorter timeframes")
            elif duration_hours < 1:
                analysis["insights"].append("Very short trade - may indicate overtrading")
            
            # Analyze R/R ratio
            rr_ratio = performance_metrics.get('rr_ratio', 0)
            if rr_ratio > 2:
                analysis["insights"].append("Excellent R/R ratio achieved")
            elif rr_ratio < 1:
                analysis["improvements"].append("Poor R/R ratio - review stop loss and target placement")
            
            # Analyze success
            success = performance_metrics.get('success', False)
            if success:
                analysis["insights"].append("Successful trade execution")
            else:
                analysis["improvements"].append("Trade failed - review entry conditions and market analysis")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing execution quality: {e}")
            return {"error": str(e)}
    
    async def get_trade_outcome_statistics(self) -> Dict[str, Any]:
        """
        Get overall trade outcome statistics.
        
        Returns:
            Dictionary with trade outcome statistics
        """
        try:
            # Get all trade outcomes
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'trade_outcome').execute()
            
            if not result.data:
                return {"total_trades": 0}
            
            trade_outcomes = result.data
            total_trades = len(trade_outcomes)
            
            # Calculate statistics
            successful_trades = 0
            total_return = 0
            total_duration = 0
            
            for trade in trade_outcomes:
                content = trade.get('content', {})
                module_intelligence = trade.get('module_intelligence', {})
                
                # Get performance data
                success = content.get('success') or module_intelligence.get('success', False)
                return_pct = content.get('return_pct') or module_intelligence.get('return_pct', 0)
                duration = content.get('duration_hours') or module_intelligence.get('duration_hours', 0)
                
                if success:
                    successful_trades += 1
                
                total_return += return_pct
                total_duration += duration
            
            success_rate = successful_trades / total_trades if total_trades > 0 else 0
            avg_return = total_return / total_trades if total_trades > 0 else 0
            avg_duration = total_duration / total_trades if total_trades > 0 else 0
            
            return {
                "total_trades": total_trades,
                "successful_trades": successful_trades,
                "success_rate": round(success_rate, 3),
                "avg_return": round(avg_return, 3),
                "avg_duration_hours": round(avg_duration, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting trade outcome statistics: {e}")
            return {"error": str(e)}
