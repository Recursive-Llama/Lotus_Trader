from datetime import datetime, timezone
from typing import List, Dict


class EntryExitPlanner:
    @staticmethod
    def build_entries(current_price: float, total_native: float) -> List[Dict]:
        now = datetime.now(timezone.utc).isoformat()
        e_amt = total_native / 3.0
        return [
            {'entry_number': 1, 'price': current_price, 'amount_native': e_amt, 'entry_type': 'immediate', 'status': 'pending', 'created_at': now},
            {'entry_number': 2, 'price': current_price * 0.7, 'amount_native': e_amt, 'entry_type': 'dip_30', 'status': 'pending', 'created_at': now},
            {'entry_number': 3, 'price': current_price * 0.4, 'amount_native': e_amt, 'entry_type': 'dip_60', 'status': 'pending', 'created_at': now},
        ]

    @staticmethod
    def build_exits(exit_rules: Dict, avg_entry_price: float, total_quantity: float, 
                    current_price: float = None) -> List[Dict]:
        """
        Build exits based on exit_rules and avg_entry_price
        
        Args:
            exit_rules: Dictionary with 'stages' containing gain_pct and exit_pct
            avg_entry_price: Average entry price to base exit prices on
            total_quantity: Current total token quantity
            current_price: Fallback price if avg_entry_price is 0 (for backwards compatibility)
        
        Returns:
            List of exit dictionaries
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
            
            # Calculate tokens to sell based on exit percentage
            tokens_to_sell = total_quantity * (exit_pct / 100)
            
            exits.append({
                'exit_number': i,
                'price': exit_price,
                'tokens': tokens_to_sell,
                'gain_pct': gain_pct,
                'exit_pct': exit_pct,
                'status': 'pending',
                'created_at': now
            })
        
        return exits






