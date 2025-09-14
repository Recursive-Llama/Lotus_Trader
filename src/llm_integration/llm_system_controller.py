"""
LLM System Controller - The actual mechanism for LLMs to control and change the system
This is where LLMs read system state, make decisions, and execute changes
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
import json
import yaml
from pathlib import Path

from .openrouter_client import OpenRouterClient
from .prompt_manager import PromptManager
from src.utils.supabase_manager import SupabaseManager

logger = logging.getLogger(__name__)

class LLMSystemController:
    """
    The actual mechanism for LLMs to control and change the system
    This is where LLMs read system state, make decisions, and execute changes
    """
    
    def __init__(self, db_manager: SupabaseManager, config_path: str = None):
        """
        Initialize the LLM System Controller
        
        Args:
            db_manager: Database manager for system state access
            config_path: Path to system configuration files
        """
        self.db_manager = db_manager
        self.llm_client = OpenRouterClient()
        self.prompt_manager = PromptManager()
        
        # System configuration paths
        self.config_path = Path(config_path) if config_path else Path(__file__).parent.parent / "config"
        
        # System state cache
        self.system_state_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info("LLMSystemController initialized")
    
    def read_system_state(self, state_type: str = "full") -> Dict[str, Any]:
        """
        Read current system state for LLM analysis
        
        Args:
            state_type: Type of state to read (full, parameters, performance, market)
            
        Returns:
            Dict containing system state
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            if state_type == "full":
                return self._read_full_system_state()
            elif state_type == "parameters":
                return self._read_parameter_state()
            elif state_type == "performance":
                return self._read_performance_state()
            elif state_type == "market":
                return self._read_market_state()
            else:
                logger.error(f"Unknown state type: {state_type}")
                return {}
                
        except Exception as e:
            logger.error(f"Error reading system state: {e}")
            return {}
    
    def _read_full_system_state(self) -> Dict[str, Any]:
        """Read complete system state"""
        try:
            state = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parameters": self._read_parameter_state(),
                "performance": self._read_performance_state(),
                "market": self._read_market_state(),
                "recent_strands": self._get_recent_strands(),
                "active_signals": self._get_active_signals(),
                "system_health": self._get_system_health()
            }
            
            return state
            
        except Exception as e:
            logger.error(f"Error reading full system state: {e}")
            return {}
    
    def _read_parameter_state(self) -> Dict[str, Any]:
        """Read current system parameters"""
        try:
            # Read configuration files
            config_files = [
                "trading_plans.yaml",
                "llm_integration.yaml",
                "signal_thresholds.yaml"
            ]
            
            parameters = {}
            for config_file in config_files:
                config_path = self.config_path / config_file
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config_data = yaml.safe_load(f)
                        parameters[config_file.replace('.yaml', '')] = config_data
            
            # Read database parameters
            db_params = self._get_database_parameters()
            parameters["database"] = db_params
            
            return parameters
            
        except Exception as e:
            logger.error(f"Error reading parameter state: {e}")
            return {}
    
    def _read_performance_state(self) -> Dict[str, Any]:
        """Read system performance metrics"""
        try:
            # Get recent performance data from database
            query = """
                SELECT 
                    COUNT(*) as total_signals,
                    AVG(CASE WHEN outcome = 'success' THEN 1.0 ELSE 0.0 END) as success_rate,
                    AVG(return_pct) as avg_return,
                    AVG(risk_score) as avg_risk,
                    MAX(created_at) as last_signal_time
                FROM AD_strands 
                WHERE created_at >= NOW() - INTERVAL '7 days'
                AND signal_type IS NOT NULL
            """
            
            result = self.db_manager.execute_query(query)
            performance = result[0] if result else {}
            
            # Add additional performance metrics
            performance.update({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system_uptime": self._get_system_uptime(),
                "error_rate": self._get_error_rate(),
                "response_time": self._get_avg_response_time()
            })
            
            return performance
            
        except Exception as e:
            logger.error(f"Error reading performance state: {e}")
            return {}
    
    def _read_market_state(self) -> Dict[str, Any]:
        """Read current market conditions"""
        try:
            # Get latest market data
            query = """
                SELECT 
                    symbol,
                    close_price,
                    volume,
                    price_change_24h,
                    volatility,
                    market_cap_rank
                FROM alpha_market_data_1m 
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
                ORDER BY timestamp DESC
                LIMIT 10
            """
            
            market_data = self.db_manager.execute_query(query)
            
            # Get market regime
            regime_query = """
                SELECT regime_type, confidence, created_at
                FROM AD_strands 
                WHERE regime_type IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            regime_result = self.db_manager.execute_query(regime_query)
            current_regime = regime_result[0] if regime_result else {}
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data": market_data,
                "current_regime": current_regime,
                "market_volatility": self._calculate_market_volatility(market_data),
                "volume_profile": self._analyze_volume_profile(market_data)
            }
            
        except Exception as e:
            logger.error(f"Error reading market state: {e}")
            return {}
    
    def make_system_decision(self, decision_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Have LLM make a system decision based on current state
        
        Args:
            decision_type: Type of decision (parameter_adjustment, strategy_change, risk_management)
            context: Additional context for the decision
            
        Returns:
            Dict containing the decision and reasoning
        """
        try:
            # Get current system state
            system_state = self.read_system_state()
            
            # Get appropriate prompt for decision type
            prompt = self.prompt_manager.get_prompt("system_controller", decision_type)
            
            # Prepare context for LLM
            llm_context = {
                "system_state": system_state,
                "decision_context": context,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Format prompt with context
            formatted_prompt = prompt.format(**llm_context)
            
            # Get LLM decision
            response = self.llm_client.complete(
                prompt=formatted_prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            # Parse LLM response
            decision = self._parse_llm_decision(response, decision_type)
            
            # Log decision
            logger.info(f"LLM made {decision_type} decision: {decision.get('action', 'unknown')}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error making system decision: {e}")
            return {"error": str(e), "action": "none"}
    
    def execute_system_change(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a system change based on LLM decision
        
        Args:
            change: Change to execute (from LLM decision)
            
        Returns:
            Dict containing execution results
        """
        try:
            change_type = change.get("type", "unknown")
            action = change.get("action", "none")
            
            if change_type == "parameter_adjustment":
                return self._execute_parameter_change(change)
            elif change_type == "strategy_change":
                return self._execute_strategy_change(change)
            elif change_type == "risk_management":
                return self._execute_risk_change(change)
            elif change_type == "database_update":
                return self._execute_database_change(change)
            else:
                logger.error(f"Unknown change type: {change_type}")
                return {"error": f"Unknown change type: {change_type}"}
                
        except Exception as e:
            logger.error(f"Error executing system change: {e}")
            return {"error": str(e)}
    
    def _execute_parameter_change(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parameter changes"""
        try:
            parameters = change.get("parameters", {})
            results = {}
            
            for param_name, param_value in parameters.items():
                if param_name.endswith("_threshold"):
                    # Update threshold in database
                    success = self._update_threshold_parameter(param_name, param_value)
                    results[param_name] = success
                elif param_name.endswith("_weight"):
                    # Update weight in database
                    success = self._update_weight_parameter(param_name, param_value)
                    results[param_name] = success
                else:
                    # Update configuration file
                    success = self._update_config_parameter(param_name, param_value)
                    results[param_name] = success
            
            return {
                "type": "parameter_adjustment",
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing parameter change: {e}")
            return {"error": str(e)}
    
    def _execute_strategy_change(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Execute strategy changes"""
        try:
            strategy_updates = change.get("strategy_updates", {})
            results = {}
            
            for strategy_name, strategy_config in strategy_updates.items():
                # Update strategy in database
                success = self._update_strategy_config(strategy_name, strategy_config)
                results[strategy_name] = success
            
            return {
                "type": "strategy_change",
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing strategy change: {e}")
            return {"error": str(e)}
    
    def _execute_risk_change(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Execute risk management changes"""
        try:
            risk_updates = change.get("risk_updates", {})
            results = {}
            
            for risk_param, risk_value in risk_updates.items():
                # Update risk parameter
                success = self._update_risk_parameter(risk_param, risk_value)
                results[risk_param] = success
            
            return {
                "type": "risk_management",
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing risk change: {e}")
            return {"error": str(e)}
    
    def _execute_database_change(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database changes"""
        try:
            db_updates = change.get("database_updates", {})
            results = {}
            
            for table, updates in db_updates.items():
                # Execute database update
                success = self._execute_database_update(table, updates)
                results[table] = success
            
            return {
                "type": "database_update",
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing database change: {e}")
            return {"error": str(e)}
    
    def learn_from_outcome(self, decision_id: str, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """
        Learn from the outcome of a previous decision
        
        Args:
            decision_id: ID of the decision to learn from
            outcome: Outcome data (success/failure, metrics, etc.)
            
        Returns:
            Dict containing learning results
        """
        try:
            # Get the original decision
            original_decision = self._get_decision_by_id(decision_id)
            if not original_decision:
                return {"error": "Decision not found"}
            
            # Prepare learning context
            learning_context = {
                "original_decision": original_decision,
                "outcome": outcome,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Get learning prompt
            prompt = self.prompt_manager.get_prompt("system_controller", "learning_from_outcome")
            formatted_prompt = prompt.format(**learning_context)
            
            # Get LLM learning insights
            response = self.llm_client.complete(
                prompt=formatted_prompt,
                max_tokens=1500,
                temperature=0.4
            )
            
            # Parse learning insights
            learning_insights = self._parse_learning_insights(response)
            
            # Store learning insights in database
            self._store_learning_insights(decision_id, learning_insights)
            
            # Apply learning to future decisions
            self._apply_learning_to_system(learning_insights)
            
            return {
                "decision_id": decision_id,
                "learning_insights": learning_insights,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error learning from outcome: {e}")
            return {"error": str(e)}
    
    # Helper methods for system state reading
    def _get_recent_strands(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent strands from database"""
        try:
            query = """
                SELECT * FROM AD_strands 
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC 
                LIMIT %s
            """
            return self.db_manager.execute_query(query, (limit,))
        except Exception as e:
            logger.error(f"Error getting recent strands: {e}")
            return []
    
    def _get_active_signals(self) -> List[Dict[str, Any]]:
        """Get currently active signals"""
        try:
            query = """
                SELECT * FROM AD_strands 
                WHERE signal_type IS NOT NULL 
                AND status = 'active'
                ORDER BY created_at DESC
            """
            return self.db_manager.execute_query(query)
        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics"""
        try:
            # Check database connection
            db_healthy = self.db_manager.test_connection()
            
            # Check LLM service
            llm_healthy = self.llm_client.test_connection()
            
            # Check recent error rate
            error_rate = self._get_error_rate()
            
            return {
                "database_healthy": db_healthy,
                "llm_healthy": llm_healthy,
                "error_rate": error_rate,
                "overall_health": "healthy" if db_healthy and llm_healthy and error_rate < 0.1 else "degraded"
            }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {"overall_health": "unknown"}
    
    def _get_database_parameters(self) -> Dict[str, Any]:
        """Get parameters stored in database"""
        try:
            query = """
                SELECT parameter_name, parameter_value, parameter_type
                FROM system_parameters 
                WHERE active = true
            """
            results = self.db_manager.execute_query(query)
            
            parameters = {}
            for row in results:
                param_name = row['parameter_name']
                param_value = row['parameter_value']
                param_type = row['parameter_type']
                
                # Convert value based on type
                if param_type == 'float':
                    parameters[param_name] = float(param_value)
                elif param_type == 'int':
                    parameters[param_name] = int(param_value)
                elif param_type == 'bool':
                    parameters[param_name] = param_value.lower() == 'true'
                else:
                    parameters[param_name] = param_value
            
            return parameters
        except Exception as e:
            logger.error(f"Error getting database parameters: {e}")
            return {}
    
    def _get_system_uptime(self) -> str:
        """Get system uptime"""
        # This would be implemented based on your system monitoring
        return "24h 15m 30s"  # Placeholder
    
    def _get_error_rate(self) -> float:
        """Get current error rate"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_operations,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                FROM system_logs 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
            """
            result = self.db_manager.execute_query(query)
            if result and result[0]['total_operations'] > 0:
                return result[0]['error_count'] / result[0]['total_operations']
            return 0.0
        except Exception as e:
            logger.error(f"Error getting error rate: {e}")
            return 0.0
    
    def _get_avg_response_time(self) -> float:
        """Get average response time"""
        try:
            query = """
                SELECT AVG(response_time_ms) as avg_response_time
                FROM system_logs 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                AND response_time_ms IS NOT NULL
            """
            result = self.db_manager.execute_query(query)
            return result[0]['avg_response_time'] if result and result[0]['avg_response_time'] else 0.0
        except Exception as e:
            logger.error(f"Error getting average response time: {e}")
            return 0.0
    
    def _calculate_market_volatility(self, market_data: List[Dict]) -> float:
        """Calculate market volatility from recent data"""
        if not market_data:
            return 0.0
        
        prices = [float(row['close_price']) for row in market_data if row['close_price']]
        if len(prices) < 2:
            return 0.0
        
        # Simple volatility calculation
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        volatility = (sum([r**2 for r in returns]) / len(returns))**0.5
        return volatility
    
    def _analyze_volume_profile(self, market_data: List[Dict]) -> Dict[str, Any]:
        """Analyze volume profile from market data"""
        if not market_data:
            return {"avg_volume": 0, "volume_trend": "unknown"}
        
        volumes = [float(row['volume']) for row in market_data if row['volume']]
        if not volumes:
            return {"avg_volume": 0, "volume_trend": "unknown"}
        
        avg_volume = sum(volumes) / len(volumes)
        
        # Simple trend analysis
        if len(volumes) >= 2:
            recent_avg = sum(volumes[:len(volumes)//2]) / (len(volumes)//2)
            older_avg = sum(volumes[len(volumes)//2:]) / (len(volumes) - len(volumes)//2)
            trend = "increasing" if recent_avg > older_avg else "decreasing"
        else:
            trend = "stable"
        
        return {
            "avg_volume": avg_volume,
            "volume_trend": trend,
            "max_volume": max(volumes),
            "min_volume": min(volumes)
        }
    
    # Helper methods for executing changes
    def _update_threshold_parameter(self, param_name: str, param_value: float) -> bool:
        """Update threshold parameter in database"""
        try:
            query = """
                INSERT INTO system_parameters (parameter_name, parameter_value, parameter_type, updated_at)
                VALUES (%s, %s, 'float', NOW())
                ON CONFLICT (parameter_name) 
                DO UPDATE SET 
                    parameter_value = EXCLUDED.parameter_value,
                    updated_at = NOW()
            """
            self.db_manager.execute_update(query, (param_name, str(param_value)))
            return True
        except Exception as e:
            logger.error(f"Error updating threshold parameter {param_name}: {e}")
            return False
    
    def _update_weight_parameter(self, param_name: str, param_value: float) -> bool:
        """Update weight parameter in database"""
        try:
            query = """
                INSERT INTO system_parameters (parameter_name, parameter_value, parameter_type, updated_at)
                VALUES (%s, %s, 'float', NOW())
                ON CONFLICT (parameter_name) 
                DO UPDATE SET 
                    parameter_value = EXCLUDED.parameter_value,
                    updated_at = NOW()
            """
            self.db_manager.execute_update(query, (param_name, str(param_value)))
            return True
        except Exception as e:
            logger.error(f"Error updating weight parameter {param_name}: {e}")
            return False
    
    def _update_config_parameter(self, param_name: str, param_value: Any) -> bool:
        """Update configuration file parameter"""
        try:
            # This would update the appropriate YAML config file
            # Implementation depends on your config structure
            logger.info(f"Would update config parameter {param_name} to {param_value}")
            return True
        except Exception as e:
            logger.error(f"Error updating config parameter {param_name}: {e}")
            return False
    
    def _update_strategy_config(self, strategy_name: str, strategy_config: Dict[str, Any]) -> bool:
        """Update strategy configuration"""
        try:
            query = """
                INSERT INTO strategy_configs (strategy_name, config_data, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (strategy_name) 
                DO UPDATE SET 
                    config_data = EXCLUDED.config_data,
                    updated_at = NOW()
            """
            self.db_manager.execute_update(query, (strategy_name, json.dumps(strategy_config)))
            return True
        except Exception as e:
            logger.error(f"Error updating strategy config {strategy_name}: {e}")
            return False
    
    def _update_risk_parameter(self, risk_param: str, risk_value: Any) -> bool:
        """Update risk management parameter"""
        try:
            query = """
                INSERT INTO risk_parameters (parameter_name, parameter_value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (parameter_name) 
                DO UPDATE SET 
                    parameter_value = EXCLUDED.parameter_value,
                    updated_at = NOW()
            """
            self.db_manager.execute_update(query, (risk_param, str(risk_value)))
            return True
        except Exception as e:
            logger.error(f"Error updating risk parameter {risk_param}: {e}")
            return False
    
    def _execute_database_update(self, table: str, updates: Dict[str, Any]) -> bool:
        """Execute database update"""
        try:
            # This would execute the specific database update
            # Implementation depends on the specific update needed
            logger.info(f"Would execute database update on {table}: {updates}")
            return True
        except Exception as e:
            logger.error(f"Error executing database update on {table}: {e}")
            return False
    
    # Helper methods for learning
    def _get_decision_by_id(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get decision by ID"""
        try:
            query = """
                SELECT * FROM llm_decisions 
                WHERE decision_id = %s
            """
            result = self.db_manager.execute_query(query, (decision_id,))
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting decision by ID: {e}")
            return None
    
    def _parse_llm_decision(self, response: str, decision_type: str) -> Dict[str, Any]:
        """Parse LLM decision response"""
        try:
            # Try to parse as JSON first
            if response.strip().startswith('{'):
                return json.loads(response)
            
            # Otherwise, extract key information
            decision = {
                "type": decision_type,
                "action": "none",
                "reasoning": response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Extract action from response
            if "increase" in response.lower():
                decision["action"] = "increase"
            elif "decrease" in response.lower():
                decision["action"] = "decrease"
            elif "change" in response.lower():
                decision["action"] = "change"
            
            return decision
            
        except Exception as e:
            logger.error(f"Error parsing LLM decision: {e}")
            return {
                "type": decision_type,
                "action": "none",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _parse_learning_insights(self, response: str) -> Dict[str, Any]:
        """Parse learning insights from LLM response"""
        try:
            # Try to parse as JSON first
            if response.strip().startswith('{'):
                return json.loads(response)
            
            # Otherwise, create basic insights structure
            return {
                "insights": response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing learning insights: {e}")
            return {
                "insights": "Error parsing insights",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _store_learning_insights(self, decision_id: str, learning_insights: Dict[str, Any]) -> bool:
        """Store learning insights in database"""
        try:
            query = """
                INSERT INTO learning_insights (decision_id, insights_data, created_at)
                VALUES (%s, %s, NOW())
            """
            self.db_manager.execute_update(query, (decision_id, json.dumps(learning_insights)))
            return True
        except Exception as e:
            logger.error(f"Error storing learning insights: {e}")
            return False
    
    def _apply_learning_to_system(self, learning_insights: Dict[str, Any]) -> bool:
        """Apply learning insights to system"""
        try:
            # This would apply the learning insights to improve future decisions
            # Implementation depends on the specific insights
            logger.info(f"Applying learning insights: {learning_insights}")
            return True
        except Exception as e:
            logger.error(f"Error applying learning to system: {e}")
            return False
