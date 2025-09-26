#!/usr/bin/env python3
"""
Centralized Allocation Manager

This module provides a single source of truth for all allocation percentages
across the trading system. All components should use this manager instead of
hardcoding allocation values.

Usage:
    from config.allocation_manager import AllocationManager
    
    manager = AllocationManager(config)
    allocation = manager.get_social_curator_allocation(curator_score, test_mode=False)
    gem_allocation = manager.get_gem_bot_allocation('conservative', test_mode=False)
"""

import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path


class AllocationManager:
    """
    Centralized allocation manager for all trading components.
    
    This class provides a single source of truth for allocation percentages,
    making it easy to adjust risk levels across the entire system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the allocation manager.
        
        Args:
            config: Optional config dict. If None, loads from social_trading_config.yaml
        """
        if config is None:
            config = self._load_config()
        
        self.config = config
        self.allocation_config = config.get('allocation_config', {})
        
        # Validate configuration
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = Path(__file__).parent / 'social_trading_config.yaml'
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _validate_config(self):
        """Validate that required allocation config exists."""
        required_sections = ['social_curators', 'gem_bot', 'test_mode']
        
        for section in required_sections:
            if section not in self.allocation_config:
                raise ValueError(f"Missing required allocation config section: {section}")
    
    def get_social_curator_allocation(self, curator_score: float, test_mode: bool = False) -> float:
        """
        Get allocation percentage for social media curators based on their score.
        
        Args:
            curator_score: Curator performance score (0.0 to 1.0)
            test_mode: If True, applies test mode multiplier
            
        Returns:
            Allocation percentage (e.g., 20.0 for 20%)
        """
        social_config = self.allocation_config['social_curators']
        
        # Determine base allocation based on score
        if curator_score >= social_config['excellent_score']:
            base_allocation = social_config['excellent_allocation']
        elif curator_score >= social_config['good_score']:
            base_allocation = social_config['good_allocation']
        else:
            base_allocation = social_config['acceptable_allocation']
        
        # Apply test mode multiplier if needed
        if test_mode:
            multiplier = self.allocation_config['test_mode']['social_curators_multiplier']
            return base_allocation * multiplier
        
        return base_allocation
    
    def get_gem_bot_allocation(self, column_type: str, test_mode: bool = False) -> float:
        """
        Get allocation percentage for gem bot signals based on column type.
        
        Args:
            column_type: Type of gem bot column ('conservative', 'balanced', 'risky')
            test_mode: If True, applies test mode multiplier
            
        Returns:
            Allocation percentage (e.g., 6.0 for 6%)
        """
        gem_config = self.allocation_config['gem_bot']
        
        # Map column types to allocation keys
        allocation_key = f"{column_type}_allocation"
        
        if allocation_key not in gem_config:
            raise ValueError(f"Unknown gem bot column type: {column_type}")
        
        base_allocation = gem_config[allocation_key]
        
        # Apply test mode multiplier if needed
        if test_mode:
            multiplier = self.allocation_config['test_mode']['gem_bot_multiplier']
            return base_allocation * multiplier
        
        return base_allocation
    
    def get_all_allocations(self, test_mode: bool = False) -> Dict[str, Any]:
        """
        Get all allocation configurations for debugging/inspection.
        
        Args:
            test_mode: If True, applies test mode multipliers
            
        Returns:
            Dictionary with all allocation values
        """
        social_config = self.allocation_config['social_curators']
        gem_config = self.allocation_config['gem_bot']
        
        result = {
            'social_curators': {
                'excellent': self.get_social_curator_allocation(0.9, test_mode),
                'good': self.get_social_curator_allocation(0.7, test_mode),
                'acceptable': self.get_social_curator_allocation(0.5, test_mode),
            },
            'gem_bot': {
                'conservative': self.get_gem_bot_allocation('conservative', test_mode),
                'balanced': self.get_gem_bot_allocation('balanced', test_mode),
                'risky': self.get_gem_bot_allocation('risky', test_mode),
            }
        }
        
        return result
    
    def update_allocation(self, category: str, key: str, value: float) -> None:
        """
        Update an allocation value in the config.
        
        Args:
            category: Category ('social_curators', 'gem_bot', 'test_mode')
            key: Key within the category
            value: New value
        """
        if category not in self.allocation_config:
            raise ValueError(f"Unknown category: {category}")
        
        if key not in self.allocation_config[category]:
            raise ValueError(f"Unknown key '{key}' in category '{category}'")
        
        self.allocation_config[category][key] = value
    
    def save_config(self, file_path: Optional[str] = None) -> None:
        """
        Save the current configuration to a YAML file.
        
        Args:
            file_path: Optional path to save to. If None, saves to social_trading_config.yaml
        """
        if file_path is None:
            file_path = Path(__file__).parent / 'social_trading_config.yaml'
        
        # Update the main config with our allocation config
        self.config['allocation_config'] = self.allocation_config
        
        with open(file_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)


# Convenience function for quick access
def get_allocation_manager(config: Optional[Dict[str, Any]] = None) -> AllocationManager:
    """
    Get a configured AllocationManager instance.
    
    Args:
        config: Optional config dict. If None, loads from file.
        
    Returns:
        Configured AllocationManager instance
    """
    return AllocationManager(config)


# Example usage and testing
if __name__ == "__main__":
    # Test the allocation manager
    manager = AllocationManager()
    
    print("=== Allocation Manager Test ===")
    print("\nSocial Curator Allocations:")
    print(f"Excellent (0.9): {manager.get_social_curator_allocation(0.9):.1f}%")
    print(f"Good (0.7): {manager.get_social_curator_allocation(0.7):.1f}%")
    print(f"Acceptable (0.5): {manager.get_social_curator_allocation(0.5):.1f}%")
    
    print("\nGem Bot Allocations:")
    print(f"Conservative: {manager.get_gem_bot_allocation('conservative'):.1f}%")
    print(f"Balanced: {manager.get_gem_bot_allocation('balanced'):.1f}%")
    print(f"Risky: {manager.get_gem_bot_allocation('risky'):.1f}%")
    
    print("\nTest Mode Allocations:")
    test_allocations = manager.get_all_allocations(test_mode=True)
    print(f"Social Curators (test): {test_allocations['social_curators']}")
    print(f"Gem Bot (test): {test_allocations['gem_bot']}")
