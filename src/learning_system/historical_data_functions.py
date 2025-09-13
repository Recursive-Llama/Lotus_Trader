"""
Historical Data Retrieval Functions

Provides historical data retrieval functions for each module type to support
module-specific resonance calculations and improvement tracking.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import json


class HistoricalDataRetriever:
    """
    Historical data retrieval for module-specific calculations
    
    Provides functions to retrieve historical performance data for each module
    to support accurate resonance calculations and improvement tracking.
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize historical data retriever
        
        Args:
            db_connection: Database connection for queries
        """
        self.db_connection = db_connection
        
        # Module-specific configuration
        self.module_configs = {
            'rdi': {
                'name': 'Raw Data Intelligence',
                'strand_kind': 'pattern',
                'historical_fields': ['sig_confidence', 'sig_sigma', 'pattern_type', 'motif_family'],
                'performance_metrics': ['accuracy', 'consistency', 'novelty']
            },
            'cil': {
                'name': 'Central Intelligence Layer',
                'strand_kind': 'prediction_review',
                'historical_fields': ['content', 'strategic_meta_type', 'prediction_score', 'outcome_score'],
                'performance_metrics': ['accuracy', 'consistency', 'method_diversity']
            },
            'ctp': {
                'name': 'Conditional Trading Planner',
                'strand_kind': 'conditional_trading_plan',
                'historical_fields': ['content', 'quality_score', 'profitability', 'risk_adjusted_return'],
                'performance_metrics': ['profitability', 'risk_management', 'strategy_diversity']
            },
            'dm': {
                'name': 'Decision Maker',
                'strand_kind': 'trading_decision',
                'historical_fields': ['content', 'outcome_quality', 'risk_management_effectiveness'],
                'performance_metrics': ['decision_quality', 'outcome_consistency', 'factor_diversity']
            },
            'td': {
                'name': 'Trader',
                'strand_kind': 'execution_outcome',
                'historical_fields': ['content', 'execution_success', 'slippage_minimization'],
                'performance_metrics': ['execution_success', 'slippage_control', 'strategy_diversity']
            }
        }
    
    async def get_historical_performance(self, module_type: str, pattern_type: str = None, 
                                       method: str = None, days_back: int = 30) -> Dict[str, float]:
        """
        Get historical performance data for module-specific calculations
        
        Args:
            module_type: Module type ('rdi', 'cil', 'ctp', 'dm', 'td')
            pattern_type: Pattern type for RDI (optional)
            method: Method for CIL (optional)
            days_back: Number of days to look back
            
        Returns:
            Dictionary with historical performance metrics
        """
        try:
            if not self.db_connection:
                return self._get_default_historical_data(module_type)
            
            if module_type == 'rdi':
                return await self._get_rdi_historical_data(pattern_type, days_back)
            elif module_type == 'cil':
                return await self._get_cil_historical_data(method, days_back)
            elif module_type == 'ctp':
                return await self._get_ctp_historical_data(days_back)
            elif module_type == 'dm':
                return await self._get_dm_historical_data(days_back)
            elif module_type == 'td':
                return await self._get_td_historical_data(days_back)
            else:
                return self._get_default_historical_data(module_type)
                
        except Exception as e:
            print(f"Error getting historical performance for {module_type}: {e}")
            return self._get_default_historical_data(module_type)
    
    def _get_default_historical_data(self, module_type: str) -> Dict[str, float]:
        """Get default historical data when database is not available"""
        return {
            'accuracy': 0.5,
            'consistency': 0.5,
            'novelty': 0.5,
            'sample_size': 100,
            'improvement_rate': 0.0
        }
    
    # ============================================================================
    # RDI (Raw Data Intelligence) Historical Data
    # ============================================================================
    
    async def _get_rdi_historical_data(self, pattern_type: str = None, days_back: int = 30) -> Dict[str, float]:
        """Get RDI historical performance data"""
        try:
            # Query historical pattern data
            query = """
            SELECT 
                sig_confidence,
                sig_sigma,
                pattern_type,
                motif_family,
                created_at
            FROM AD_strands 
            WHERE kind = 'pattern'
            AND created_at >= NOW() - INTERVAL '%s days'
            """
            
            if pattern_type:
                query += " AND module_intelligence->>'pattern_type' = %s"
                params = (days_back, pattern_type)
            else:
                params = (days_back,)
            
            query += " ORDER BY created_at DESC LIMIT 1000"
            
            # Execute query (this would be implemented with actual database connection)
            # For now, return calculated values
            return await self._calculate_rdi_metrics(pattern_type, days_back)
            
        except Exception as e:
            print(f"Error getting RDI historical data: {e}")
            return self._get_default_historical_data('rdi')
    
    async def _calculate_rdi_metrics(self, pattern_type: str = None, days_back: int = 30) -> Dict[str, float]:
        """Calculate RDI historical metrics"""
        try:
            # This would calculate actual metrics from database data
            # For now, return realistic estimates
            
            base_accuracy = 0.6
            base_consistency = 0.7
            base_novelty = 0.4
            
            # Adjust based on pattern type
            if pattern_type:
                if pattern_type in ['diagonal_breakout', 'horizontal_breakout']:
                    base_accuracy += 0.1
                    base_consistency += 0.1
                elif pattern_type in ['volume_spike', 'microstructure']:
                    base_novelty += 0.2
            
            return {
                'accuracy': min(base_accuracy, 1.0),
                'consistency': min(base_consistency, 1.0),
                'novelty': min(base_novelty, 1.0),
                'sample_size': 150,
                'improvement_rate': 0.05
            }
            
        except Exception as e:
            print(f"Error calculating RDI metrics: {e}")
            return self._get_default_historical_data('rdi')
    
    # ============================================================================
    # CIL (Central Intelligence Layer) Historical Data
    # ============================================================================
    
    async def _get_cil_historical_data(self, method: str = None, days_back: int = 30) -> Dict[str, float]:
        """Get CIL historical performance data"""
        try:
            # Query historical prediction data
            query = """
            SELECT 
                content,
                strategic_meta_type,
                prediction_score,
                outcome_score,
                created_at
            FROM AD_strands 
            WHERE kind = 'prediction_review'
            AND created_at >= NOW() - INTERVAL '%s days'
            """
            
            if method:
                query += " AND content->>'method' = %s"
                params = (days_back, method)
            else:
                params = (days_back,)
            
            query += " ORDER BY created_at DESC LIMIT 1000"
            
            # Execute query (this would be implemented with actual database connection)
            # For now, return calculated values
            return await self._calculate_cil_metrics(method, days_back)
            
        except Exception as e:
            print(f"Error getting CIL historical data: {e}")
            return self._get_default_historical_data('cil')
    
    async def _calculate_cil_metrics(self, method: str = None, days_back: int = 30) -> Dict[str, float]:
        """Calculate CIL historical metrics"""
        try:
            # This would calculate actual metrics from database data
            # For now, return realistic estimates
            
            base_accuracy = 0.65
            base_consistency = 0.6
            base_method_diversity = 0.7
            
            # Adjust based on method
            if method:
                if method in ['ensemble', 'meta_learning']:
                    base_accuracy += 0.1
                    base_consistency += 0.1
                elif method in ['novel_approach', 'experimental']:
                    base_method_diversity += 0.2
            
            return {
                'accuracy': min(base_accuracy, 1.0),
                'consistency': min(base_consistency, 1.0),
                'method_diversity': min(base_method_diversity, 1.0),
                'sample_size': 120,
                'improvement_rate': 0.03
            }
            
        except Exception as e:
            print(f"Error calculating CIL metrics: {e}")
            return self._get_default_historical_data('cil')
    
    # ============================================================================
    # CTP (Conditional Trading Planner) Historical Data
    # ============================================================================
    
    async def _get_ctp_historical_data(self, days_back: int = 30) -> Dict[str, float]:
        """Get CTP historical performance data"""
        try:
            # Query historical trading plan data
            query = """
            SELECT 
                content,
                quality_score,
                profitability,
                risk_adjusted_return,
                created_at
            FROM AD_strands 
            WHERE kind = 'conditional_trading_plan'
            AND created_at >= NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC 
            LIMIT 1000
            """
            
            # Execute query (this would be implemented with actual database connection)
            # For now, return calculated values
            return await self._calculate_ctp_metrics(days_back)
            
        except Exception as e:
            print(f"Error getting CTP historical data: {e}")
            return self._get_default_historical_data('ctp')
    
    async def _calculate_ctp_metrics(self, days_back: int = 30) -> Dict[str, float]:
        """Calculate CTP historical metrics"""
        try:
            # This would calculate actual metrics from database data
            # For now, return realistic estimates
            
            return {
                'profitability': 0.55,
                'risk_management': 0.7,
                'strategy_diversity': 0.6,
                'sample_size': 80,
                'improvement_rate': 0.04
            }
            
        except Exception as e:
            print(f"Error calculating CTP metrics: {e}")
            return self._get_default_historical_data('ctp')
    
    # ============================================================================
    # DM (Decision Maker) Historical Data
    # ============================================================================
    
    async def _get_dm_historical_data(self, days_back: int = 30) -> Dict[str, float]:
        """Get DM historical performance data"""
        try:
            # Query historical decision data
            query = """
            SELECT 
                content,
                outcome_quality,
                risk_management_effectiveness,
                created_at
            FROM AD_strands 
            WHERE kind = 'trading_decision'
            AND created_at >= NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC 
            LIMIT 1000
            """
            
            # Execute query (this would be implemented with actual database connection)
            # For now, return calculated values
            return await self._calculate_dm_metrics(days_back)
            
        except Exception as e:
            print(f"Error getting DM historical data: {e}")
            return self._get_default_historical_data('dm')
    
    async def _calculate_dm_metrics(self, days_back: int = 30) -> Dict[str, float]:
        """Calculate DM historical metrics"""
        try:
            # This would calculate actual metrics from database data
            # For now, return realistic estimates
            
            return {
                'decision_quality': 0.7,
                'outcome_consistency': 0.65,
                'factor_diversity': 0.5,
                'sample_size': 60,
                'improvement_rate': 0.02
            }
            
        except Exception as e:
            print(f"Error calculating DM metrics: {e}")
            return self._get_default_historical_data('dm')
    
    # ============================================================================
    # TD (Trader) Historical Data
    # ============================================================================
    
    async def _get_td_historical_data(self, days_back: int = 30) -> Dict[str, float]:
        """Get TD historical performance data"""
        try:
            # Query historical execution data
            query = """
            SELECT 
                content,
                execution_success,
                slippage_minimization,
                created_at
            FROM AD_strands 
            WHERE kind = 'execution_outcome'
            AND created_at >= NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC 
            LIMIT 1000
            """
            
            # Execute query (this would be implemented with actual database connection)
            # For now, return calculated values
            return await self._calculate_td_metrics(days_back)
            
        except Exception as e:
            print(f"Error getting TD historical data: {e}")
            return self._get_default_historical_data('td')
    
    async def _calculate_td_metrics(self, days_back: int = 30) -> Dict[str, float]:
        """Calculate TD historical metrics"""
        try:
            # This would calculate actual metrics from database data
            # For now, return realistic estimates
            
            return {
                'execution_success': 0.8,
                'slippage_control': 0.75,
                'strategy_diversity': 0.4,
                'sample_size': 200,
                'improvement_rate': 0.01
            }
            
        except Exception as e:
            print(f"Error calculating TD metrics: {e}")
            return self._get_default_historical_data('td')
    
    # ============================================================================
    # Cross-Module Historical Analysis
    # ============================================================================
    
    async def get_cross_module_performance(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Get cross-module performance analysis
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Dictionary with cross-module performance metrics
        """
        try:
            # Get performance data for all modules
            module_performance = {}
            
            for module_type in ['rdi', 'cil', 'ctp', 'dm', 'td']:
                module_performance[module_type] = await self.get_historical_performance(
                    module_type, days_back=days_back
                )
            
            # Calculate cross-module metrics
            total_accuracy = sum(
                perf.get('accuracy', 0.5) for perf in module_performance.values()
            ) / len(module_performance)
            
            total_consistency = sum(
                perf.get('consistency', 0.5) for perf in module_performance.values()
            ) / len(module_performance)
            
            total_improvement = sum(
                perf.get('improvement_rate', 0.0) for perf in module_performance.values()
            ) / len(module_performance)
            
            return {
                'module_performance': module_performance,
                'overall_accuracy': total_accuracy,
                'overall_consistency': total_consistency,
                'overall_improvement_rate': total_improvement,
                'analysis_period_days': days_back
            }
            
        except Exception as e:
            print(f"Error getting cross-module performance: {e}")
            return {
                'module_performance': {},
                'overall_accuracy': 0.5,
                'overall_consistency': 0.5,
                'overall_improvement_rate': 0.0,
                'analysis_period_days': days_back
            }
    
    async def get_improvement_trends(self, module_type: str, days_back: int = 90) -> Dict[str, Any]:
        """
        Get improvement trends for a specific module
        
        Args:
            module_type: Module type ('rdi', 'cil', 'ctp', 'dm', 'td')
            days_back: Number of days to look back
            
        Returns:
            Dictionary with improvement trend data
        """
        try:
            # This would analyze trends over time
            # For now, return estimated trends
            
            return {
                'module_type': module_type,
                'trend_period_days': days_back,
                'accuracy_trend': 'improving',
                'consistency_trend': 'stable',
                'novelty_trend': 'increasing',
                'overall_trend': 'positive',
                'confidence_level': 0.7
            }
            
        except Exception as e:
            print(f"Error getting improvement trends for {module_type}: {e}")
            return {
                'module_type': module_type,
                'trend_period_days': days_back,
                'accuracy_trend': 'unknown',
                'consistency_trend': 'unknown',
                'novelty_trend': 'unknown',
                'overall_trend': 'unknown',
                'confidence_level': 0.0
            }
