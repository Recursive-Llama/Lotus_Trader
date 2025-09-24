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
    def build_exits(current_price: float, total_native: float) -> List[Dict]:
        now = datetime.now(timezone.utc).isoformat()
        total_tokens = total_native / current_price
        return [
            {'exit_number': 1, 'price': current_price * 1.3, 'tokens': total_tokens * 0.30, 'gain_pct': 30, 'status': 'pending', 'created_at': now},
            {'exit_number': 2, 'price': current_price * 3.0, 'tokens': total_tokens * 0.70 * 0.30, 'gain_pct': 200, 'status': 'pending', 'created_at': now},
            {'exit_number': 3, 'price': current_price * 4.0, 'tokens': total_tokens * 0.70 * 0.70 * 0.30, 'gain_pct': 300, 'status': 'pending', 'created_at': now},
        ]






