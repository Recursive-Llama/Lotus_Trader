"""
Learning System Configuration

This module provides configuration management for the learning system.
It includes thresholds, parameters, and settings for both universal and CIL learning.

Features:
1. Centralized configuration management
2. Environment-based configuration
3. Validation and defaults
4. Runtime configuration updates
"""

import logging
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class UniversalLearningConfig:
    """Configuration for universal learning system"""
    
    # Clustering thresholds
    min_strands_for_ml_clustering: int = 3
    min_strands_for_promotion: int = 5
    min_avg_persistence: float = 0.6
    min_avg_novelty: float = 0.5
    min_avg_surprise: float = 0.4
    
    # Clustering parameters
    max_clusters: int = 10
    min_cluster_size: int = 3
    
    # LLM settings
    llm_enabled: bool = True
    llm_temperature: float = 0.7
    llm_max_tokens: int = 500
    
    # Performance settings
    batch_size: int = 100
    max_processing_time: int = 300  # seconds


@dataclass
class CILLearningConfig:
    """Configuration for CIL learning system"""
    
    # Prediction tracking
    prediction_update_interval: int = 5  # minutes
    max_tracking_days: int = 7
    max_drawdown_threshold: float = 0.15
    
    # Analysis thresholds
    min_sample_size: int = 5
    min_success_rate: float = 0.6
    confidence_threshold: float = 0.7
    
    # Plan management
    max_plan_versions: int = 5
    plan_evolution_threshold: float = 0.8
    
    # R/R optimization
    min_rr_ratio: float = 1.5
    max_drawdown_limit: float = 0.2


@dataclass
class LearningSystemConfig:
    """Main configuration for learning system"""
    
    # Universal learning
    universal: UniversalLearningConfig
    
    # CIL learning
    cil: CILLearningConfig
    
    # Database settings
    database_batch_size: int = 50
    database_timeout: int = 30
    
    # Logging settings
    log_level: str = "INFO"
    log_learning_events: bool = True
    
    # Monitoring settings
    enable_metrics: bool = True
    metrics_interval: int = 60  # seconds
    
    # Error handling
    max_retries: int = 3
    retry_delay: int = 5  # seconds


class LearningConfigManager:
    """Manages learning system configuration"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config()
    
    def _load_config(self) -> LearningSystemConfig:
        """Load configuration from file or environment"""
        try:
            # Try to load from file first
            if self.config_file and os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                return self._parse_config(config_data)
            
            # Load from environment variables
            return self._load_from_environment()
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return self._get_default_config()
    
    def _load_from_environment(self) -> LearningSystemConfig:
        """Load configuration from environment variables"""
        try:
            # Universal learning config
            universal_config = UniversalLearningConfig(
                min_strands_for_ml_clustering=int(os.getenv('LEARNING_MIN_STRANDS_ML', 3)),
                min_strands_for_promotion=int(os.getenv('LEARNING_MIN_STRANDS_PROMOTION', 5)),
                min_avg_persistence=float(os.getenv('LEARNING_MIN_PERSISTENCE', 0.6)),
                min_avg_novelty=float(os.getenv('LEARNING_MIN_NOVELTY', 0.5)),
                min_avg_surprise=float(os.getenv('LEARNING_MIN_SURPRISE', 0.4)),
                max_clusters=int(os.getenv('LEARNING_MAX_CLUSTERS', 10)),
                min_cluster_size=int(os.getenv('LEARNING_MIN_CLUSTER_SIZE', 3)),
                llm_enabled=os.getenv('LEARNING_LLM_ENABLED', 'true').lower() == 'true',
                llm_temperature=float(os.getenv('LEARNING_LLM_TEMPERATURE', 0.7)),
                llm_max_tokens=int(os.getenv('LEARNING_LLM_MAX_TOKENS', 500)),
                batch_size=int(os.getenv('LEARNING_BATCH_SIZE', 100)),
                max_processing_time=int(os.getenv('LEARNING_MAX_PROCESSING_TIME', 300))
            )
            
            # CIL learning config
            cil_config = CILLearningConfig(
                prediction_update_interval=int(os.getenv('CIL_UPDATE_INTERVAL', 5)),
                max_tracking_days=int(os.getenv('CIL_MAX_TRACKING_DAYS', 7)),
                max_drawdown_threshold=float(os.getenv('CIL_MAX_DRAWDOWN_THRESHOLD', 0.15)),
                min_sample_size=int(os.getenv('CIL_MIN_SAMPLE_SIZE', 5)),
                min_success_rate=float(os.getenv('CIL_MIN_SUCCESS_RATE', 0.6)),
                confidence_threshold=float(os.getenv('CIL_CONFIDENCE_THRESHOLD', 0.7)),
                max_plan_versions=int(os.getenv('CIL_MAX_PLAN_VERSIONS', 5)),
                plan_evolution_threshold=float(os.getenv('CIL_PLAN_EVOLUTION_THRESHOLD', 0.8)),
                min_rr_ratio=float(os.getenv('CIL_MIN_RR_RATIO', 1.5)),
                max_drawdown_limit=float(os.getenv('CIL_MAX_DRAWDOWN_LIMIT', 0.2))
            )
            
            # Main config
            config = LearningSystemConfig(
                universal=universal_config,
                cil=cil_config,
                database_batch_size=int(os.getenv('LEARNING_DB_BATCH_SIZE', 50)),
                database_timeout=int(os.getenv('LEARNING_DB_TIMEOUT', 30)),
                log_level=os.getenv('LEARNING_LOG_LEVEL', 'INFO'),
                log_learning_events=os.getenv('LEARNING_LOG_EVENTS', 'true').lower() == 'true',
                enable_metrics=os.getenv('LEARNING_ENABLE_METRICS', 'true').lower() == 'true',
                metrics_interval=int(os.getenv('LEARNING_METRICS_INTERVAL', 60)),
                max_retries=int(os.getenv('LEARNING_MAX_RETRIES', 3)),
                retry_delay=int(os.getenv('LEARNING_RETRY_DELAY', 5))
            )
            
            self.logger.info("Loaded configuration from environment variables")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration from environment: {e}")
            return self._get_default_config()
    
    def _parse_config(self, config_data: Dict[str, Any]) -> LearningSystemConfig:
        """Parse configuration from dictionary"""
        try:
            # Parse universal config
            universal_data = config_data.get('universal', {})
            universal_config = UniversalLearningConfig(**universal_data)
            
            # Parse CIL config
            cil_data = config_data.get('cil', {})
            cil_config = CILLearningConfig(**cil_data)
            
            # Parse main config
            main_config = LearningSystemConfig(
                universal=universal_config,
                cil=cil_config,
                database_batch_size=config_data.get('database_batch_size', 50),
                database_timeout=config_data.get('database_timeout', 30),
                log_level=config_data.get('log_level', 'INFO'),
                log_learning_events=config_data.get('log_learning_events', True),
                enable_metrics=config_data.get('enable_metrics', True),
                metrics_interval=config_data.get('metrics_interval', 60),
                max_retries=config_data.get('max_retries', 3),
                retry_delay=config_data.get('retry_delay', 5)
            )
            
            self.logger.info("Loaded configuration from file")
            return main_config
            
        except Exception as e:
            self.logger.error(f"Error parsing configuration: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> LearningSystemConfig:
        """Get default configuration"""
        self.logger.info("Using default configuration")
        return LearningSystemConfig(
            universal=UniversalLearningConfig(),
            cil=CILLearningConfig()
        )
    
    def get_config(self) -> LearningSystemConfig:
        """Get current configuration"""
        return self.config
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration at runtime"""
        try:
            # Update universal config
            if 'universal' in updates:
                for key, value in updates['universal'].items():
                    if hasattr(self.config.universal, key):
                        setattr(self.config.universal, key, value)
            
            # Update CIL config
            if 'cil' in updates:
                for key, value in updates['cil'].items():
                    if hasattr(self.config.cil, key):
                        setattr(self.config.cil, key, value)
            
            # Update main config
            for key, value in updates.items():
                if key not in ['universal', 'cil'] and hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            self.logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
            return False
    
    def save_config(self, file_path: str) -> bool:
        """Save current configuration to file"""
        try:
            config_dict = {
                'universal': {
                    'min_strands_for_ml_clustering': self.config.universal.min_strands_for_ml_clustering,
                    'min_strands_for_promotion': self.config.universal.min_strands_for_promotion,
                    'min_avg_persistence': self.config.universal.min_avg_persistence,
                    'min_avg_novelty': self.config.universal.min_avg_novelty,
                    'min_avg_surprise': self.config.universal.min_avg_surprise,
                    'max_clusters': self.config.universal.max_clusters,
                    'min_cluster_size': self.config.universal.min_cluster_size,
                    'llm_enabled': self.config.universal.llm_enabled,
                    'llm_temperature': self.config.universal.llm_temperature,
                    'llm_max_tokens': self.config.universal.llm_max_tokens,
                    'batch_size': self.config.universal.batch_size,
                    'max_processing_time': self.config.universal.max_processing_time
                },
                'cil': {
                    'prediction_update_interval': self.config.cil.prediction_update_interval,
                    'max_tracking_days': self.config.cil.max_tracking_days,
                    'max_drawdown_threshold': self.config.cil.max_drawdown_threshold,
                    'min_sample_size': self.config.cil.min_sample_size,
                    'min_success_rate': self.config.cil.min_success_rate,
                    'confidence_threshold': self.config.cil.confidence_threshold,
                    'max_plan_versions': self.config.cil.max_plan_versions,
                    'plan_evolution_threshold': self.config.cil.plan_evolution_threshold,
                    'min_rr_ratio': self.config.cil.min_rr_ratio,
                    'max_drawdown_limit': self.config.cil.max_drawdown_limit
                },
                'database_batch_size': self.config.database_batch_size,
                'database_timeout': self.config.database_timeout,
                'log_level': self.config.log_level,
                'log_learning_events': self.config.log_learning_events,
                'enable_metrics': self.config.enable_metrics,
                'metrics_interval': self.config.metrics_interval,
                'max_retries': self.config.max_retries,
                'retry_delay': self.config.retry_delay
            }
            
            with open(file_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            self.logger.info(f"Configuration saved to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def validate_config(self) -> bool:
        """Validate current configuration"""
        try:
            # Validate universal config
            if self.config.universal.min_strands_for_promotion < 1:
                self.logger.error("min_strands_for_promotion must be >= 1")
                return False
            
            if not 0 <= self.config.universal.min_avg_persistence <= 1:
                self.logger.error("min_avg_persistence must be between 0 and 1")
                return False
            
            # Validate CIL config
            if self.config.cil.prediction_update_interval < 1:
                self.logger.error("prediction_update_interval must be >= 1")
                return False
            
            if not 0 <= self.config.cil.min_success_rate <= 1:
                self.logger.error("min_success_rate must be between 0 and 1")
                return False
            
            self.logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Test configuration manager
    config_manager = LearningConfigManager()
    
    # Get current config
    config = config_manager.get_config()
    print(f"Universal learning min strands: {config.universal.min_strands_for_promotion}")
    print(f"CIL learning update interval: {config.cil.prediction_update_interval}")
    
    # Validate config
    is_valid = config_manager.validate_config()
    print(f"Configuration valid: {is_valid}")
    
    # Update config
    updates = {
        'universal': {
            'min_strands_for_promotion': 10
        },
        'cil': {
            'prediction_update_interval': 10
        }
    }
    
    success = config_manager.update_config(updates)
    print(f"Configuration update success: {success}")
    
    # Save config
    success = config_manager.save_config('learning_config.json')
    print(f"Configuration save success: {success}")
