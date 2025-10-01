from datetime import datetime, timezone
from typing import List, Dict
import yaml
import os


class EntryExitPlanner:
    @staticmethod
    def _load_config() -> Dict:
        """Load configuration from social_trading_config.yaml"""
        config_path = os.path.join(os.path.dirname(__file__), '../../config/social_trading_config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def build_entries(current_price: float, total_native: float) -> List[Dict]:
        """Build entries based on config file settings"""
        now = datetime.now(timezone.utc).isoformat()
        
        # Load config
        config = EntryExitPlanner._load_config()
        entry_strategy = config['position_management']['entry_strategy']
        
        entries = []
        for i, (entry_key, entry_config) in enumerate(entry_strategy.items(), 1):
            allocation_pct = entry_config['allocation_pct']
            amount_native = total_native * (allocation_pct / 100)
            
            if i == 1:  # Immediate entry
                price = current_price
                entry_type = 'immediate'
            else:  # Dip entries
                dip_pct = entry_config['dip_pct']
                price = current_price * (1 + dip_pct / 100)  # dip_pct is negative
                entry_type = f'dip_{abs(dip_pct)}'
            
            entries.append({
                'entry_number': i,
                'price': price,
                'amount_native': amount_native,
                'entry_type': entry_type,
                'status': 'pending',
                'created_at': now
            })
        
        return entries

    @staticmethod
    def build_exits(exit_rules: Dict, avg_entry_price: float, current_price: float = None) -> List[Dict]:
        """
        Build exits based on exit_rules and avg_entry_price
        
        Args:
            exit_rules: Dictionary with 'stages' containing gain_pct and exit_pct
            avg_entry_price: Average entry price to base exit prices on
            current_price: Fallback price if avg_entry_price is 0 (for backwards compatibility)
        
        Returns:
            List of exit dictionaries with prices and percentages (no pre-calculated token amounts)
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Use avg_entry_price if available, otherwise fallback to current_price
        base_price = avg_entry_price if avg_entry_price > 0 else current_price
        if not base_price or base_price <= 0:
            raise ValueError("Cannot build exits without valid base price")
        
        # Get exit stages from rules
        stages = exit_rules.get('stages', [])
        if not stages:
            raise ValueError("No exit stages found in exit_rules")
        
        exits = []
        for i, stage in enumerate(stages, 1):
            gain_pct = stage.get('gain_pct', 0)
            exit_pct = stage.get('exit_pct', 0)
            
            # Calculate exit price based on gain percentage
            exit_price = base_price * (1 + gain_pct / 100)
            
            # Store percentage only - actual token amounts calculated at execution time
            exits.append({
                'exit_number': i,
                'price': exit_price,
                'exit_pct': exit_pct,  # Percentage of holdings to sell
                'gain_pct': gain_pct,
                'status': 'pending',
                'created_at': now
            })
        
        return exits

    @staticmethod
    def build_trend_entries_from_standard_exit(exit_price: float, exit_native_amount: float, source_exit_id: str, batch_id: str) -> List[Dict]:
        """Create two trend dip entries funded by a standard exit.

        - Uses config.position_management.trend_strategy
        - Allocates entry_capital_pct of exit_native_amount
        - Splits equally per configured entry allocations
        """
        now = datetime.now(timezone.utc).isoformat()
        config = EntryExitPlanner._load_config()
        trend = config['position_management']['trend_strategy']
        entry_capital_pct = float(trend.get('entry_capital_pct', 30))
        entries_cfg = trend.get('entries', [])

        allocated_native_total = exit_native_amount * (entry_capital_pct / 100.0)
        trend_entries: List[Dict] = []

        for idx, e in enumerate(entries_cfg, start=1):
            dip_pct = float(e['dip_pct'])
            alloc_pct = float(e['allocation_pct'])
            entry_price = exit_price * (1.0 + dip_pct / 100.0)
            allocated_native = allocated_native_total * (alloc_pct / 100.0)
            trend_entries.append({
                'trend_entry_number': idx,
                'batch_id': batch_id,
                'source_exit_id': source_exit_id,
                'entry_price': entry_price,
                'allocated_native': allocated_native,
                'status': 'pending',
                'created_at': now,
                'tokens_bought': 0.0,
                'executed_at': None,
            })

        return trend_entries

    @staticmethod
    def build_trend_exits_for_batch(exit_price: float, batch_id: str) -> List[Dict]:
        """Create three trend exits for a given batch, priced off the standard exit price.

        Sells 70% in total across 3 configured gain levels (23.33/23.33/23.34 by default).
        Token sizing will be determined at execution time by remaining batch tokens.
        """
        now = datetime.now(timezone.utc).isoformat()
        config = EntryExitPlanner._load_config()
        trend = config['position_management']['trend_strategy']
        exits_cfg = trend.get('exits', [])

        trend_exits: List[Dict] = []
        for idx, x in enumerate(exits_cfg, start=1):
            gain_pct = float(x['gain_pct'])
            exit_pct = float(x['exit_pct'])
            price = exit_price * (1.0 + gain_pct / 100.0)
            trend_exits.append({
                'trend_exit_number': idx,
                'batch_id': batch_id,
                'price': price,
                'exit_pct': exit_pct,
                'gain_pct': gain_pct,
                'status': 'pending',
                'created_at': now,
                'tokens_sold': 0.0,
                'executed_at': None,
            })

        return trend_exits






