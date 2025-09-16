"""
Strand Processor

Identifies strand type and learning requirements for the centralized learning system.
Processes any strand type and determines the appropriate learning configuration.
"""

from typing import Dict, Any, Optional
from enum import Enum


class StrandType(Enum):
    """Supported strand types for learning"""
    PATTERN = "pattern"
    PREDICTION_REVIEW = "prediction_review"
    CONDITIONAL_TRADING_PLAN = "conditional_trading_plan"
    TRADE_OUTCOME = "trade_outcome"
    TRADING_DECISION = "trading_decision"
    PORTFOLIO_OUTCOME = "portfolio_outcome"
    EXECUTION_OUTCOME = "execution_outcome"
    SOCIAL_LOWCAP = "social_lowcap"
    DECISION_LOWCAP = "decision_lowcap"


class LearningConfig:
    """Learning configuration for a specific strand type"""
    
    def __init__(
        self,
        strand_type: StrandType,
        learning_focus: str,
        cluster_types: list,
        prompt_template: str,
        min_cluster_size: int = 3,
        max_cluster_size: int = 50
    ):
        self.strand_type = strand_type
        self.learning_focus = learning_focus
        self.cluster_types = cluster_types
        self.prompt_template = prompt_template
        self.min_cluster_size = min_cluster_size
        self.max_cluster_size = max_cluster_size


class StrandProcessor:
    """Processes strands and determines learning requirements"""
    
    def __init__(self):
        self.learning_configs = self._initialize_learning_configs()
    
    def _initialize_learning_configs(self) -> Dict[StrandType, LearningConfig]:
        """Initialize learning configurations for each strand type"""
        return {
            StrandType.PATTERN: LearningConfig(
                strand_type=StrandType.PATTERN,
                learning_focus="Pattern recognition and market intelligence",
                cluster_types=[
                    "pattern_type", "asset", "timeframe", "market_conditions"
                ],
                prompt_template="pattern_braiding",
                min_cluster_size=3
            ),
            
            StrandType.PREDICTION_REVIEW: LearningConfig(
                strand_type=StrandType.PREDICTION_REVIEW,
                learning_focus="Prediction accuracy and pattern analysis",
                cluster_types=[
                    "group_signature", "asset", "timeframe", "outcome", "method"
                ],
                prompt_template="prediction_review_braiding",
                min_cluster_size=3
            ),
            
            StrandType.CONDITIONAL_TRADING_PLAN: LearningConfig(
                strand_type=StrandType.CONDITIONAL_TRADING_PLAN,
                learning_focus="Trading plan effectiveness and strategy refinement",
                cluster_types=[
                    "plan_type", "asset", "timeframe", "performance", "market_conditions"
                ],
                prompt_template="conditional_trading_plan_braiding",
                min_cluster_size=3
            ),
            
            StrandType.TRADE_OUTCOME: LearningConfig(
                strand_type=StrandType.TRADE_OUTCOME,
                learning_focus="Execution quality and trading plan performance",
                cluster_types=[
                    "asset", "timeframe", "outcome", "execution_method", "performance"
                ],
                prompt_template="trade_outcome_braiding",
                min_cluster_size=3
            ),
            
            StrandType.TRADING_DECISION: LearningConfig(
                strand_type=StrandType.TRADING_DECISION,
                learning_focus="Decision quality and strategy effectiveness",
                cluster_types=[
                    "decision_type", "asset", "timeframe", "outcome", "method"
                ],
                prompt_template="trading_decision_braiding",
                min_cluster_size=3
            ),
            
            StrandType.PORTFOLIO_OUTCOME: LearningConfig(
                strand_type=StrandType.PORTFOLIO_OUTCOME,
                learning_focus="Portfolio performance and risk management",
                cluster_types=[
                    "portfolio_type", "asset", "timeframe", "performance", "risk_metrics"
                ],
                prompt_template="portfolio_outcome_braiding",
                min_cluster_size=3
            ),
            
            StrandType.EXECUTION_OUTCOME: LearningConfig(
                strand_type=StrandType.EXECUTION_OUTCOME,
                learning_focus="Execution quality and trading efficiency",
                cluster_types=[
                    "execution_type", "asset", "timeframe", "performance", "efficiency_metrics"
                ],
                prompt_template="execution_outcome_braiding",
                min_cluster_size=3
            ),
            
            StrandType.SOCIAL_LOWCAP: LearningConfig(
                strand_type=StrandType.SOCIAL_LOWCAP,
                learning_focus="Social signal quality and curator performance",
                cluster_types=[
                    "curator_id", "platform", "token_chain", "sentiment", "confidence"
                ],
                prompt_template="social_lowcap_braiding",
                min_cluster_size=2
            ),
            
            StrandType.DECISION_LOWCAP: LearningConfig(
                strand_type=StrandType.DECISION_LOWCAP,
                learning_focus="Lowcap decision quality and allocation strategy",
                cluster_types=[
                    "curator_id", "token_chain", "allocation_pct", "action", "reasoning"
                ],
                prompt_template="decision_lowcap_braiding",
                min_cluster_size=2
            )
        }
    
    def process_strand(self, strand: Dict[str, Any]) -> Optional[LearningConfig]:
        """
        Process a strand and return its learning configuration
        
        Args:
            strand: Strand data from database
            
        Returns:
            LearningConfig if strand type is supported, None otherwise
        """
        try:
            strand_type_str = strand.get('kind', '').lower()
            strand_type = StrandType(strand_type_str)
            
            if strand_type in self.learning_configs:
                return self.learning_configs[strand_type]
            else:
                print(f"Warning: Unsupported strand type: {strand_type_str}")
                return None
                
        except (ValueError, KeyError) as e:
            print(f"Error processing strand: {e}")
            return None
    
    def get_learning_config(self, strand_type: StrandType) -> Optional[LearningConfig]:
        """
        Get learning configuration for a specific strand type
        
        Args:
            strand_type: The strand type
            
        Returns:
            LearningConfig if supported, None otherwise
        """
        return self.learning_configs.get(strand_type)
    
    def is_learning_supported(self, strand_type: str) -> bool:
        """
        Check if learning is supported for a strand type
        
        Args:
            strand_type: The strand type string
            
        Returns:
            True if supported, False otherwise
        """
        try:
            strand_type_enum = StrandType(strand_type.lower())
            return strand_type_enum in self.learning_configs
        except ValueError:
            return False
    
    def get_supported_strand_types(self) -> list:
        """
        Get list of supported strand types
        
        Returns:
            List of supported strand type strings
        """
        return [strand_type.value for strand_type in self.learning_configs.keys()]
