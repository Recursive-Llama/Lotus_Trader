from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


class PositionRepository:
    def __init__(self, supabase_manager):
        self.supabase = supabase_manager

    def create_position(self, position: Dict[str, Any]) -> bool:
        res = self.supabase.client.table('lowcap_positions').insert(position).execute()
        return bool(res.data)

    def update_entries(self, position_id: str, entries: List[Dict[str, Any]]) -> bool:
        try:
            res = self.supabase.client.table('lowcap_positions').update({'entries': entries}).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating entries for {position_id}: {e}")
            return False

    def update_exits(self, position_id: str, exits: List[Dict[str, Any]]) -> bool:
        try:
            res = self.supabase.client.table('lowcap_positions').update({'exits': exits}).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating exits for {position_id}: {e}")
            return False

    def update_exit_rules(self, position_id: str, exit_rules: Dict[str, Any]) -> bool:
        """Update exit rules for a position"""
        try:
            res = self.supabase.client.table('lowcap_positions').update({'exit_rules': exit_rules}).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating exit_rules for {position_id}: {e}")
            return False

    def get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get a position by ID"""
        res = self.supabase.client.table('lowcap_positions').select('*').eq('id', position_id).execute()
        return res.data[0] if res.data else None

    def update_position(self, position_id: str, position: Dict[str, Any]) -> bool:
        """Update a position with new data"""
        try:
            res = self.supabase.client.table('lowcap_positions').update(position).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating position {position_id}: {e}")
            return False

    def get_position_by_book_id(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent position created from a specific decision/strand (book_id)."""
        try:
            res = (
                self.supabase.client
                .table('lowcap_positions')
                .select('*')
                .eq('book_id', book_id)
                .order('created_at', desc=True)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception:
            return None

    def update_tax_percentage(self, token_contract: str, tax_pct: float) -> bool:
        """Update tax percentage for a token across all positions"""
        try:
            res = self.supabase.client.table('lowcap_positions').update({'tax_pct': tax_pct}).eq('token_contract', token_contract).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating tax percentage: {e}")
            return False

    def get_position_by_token(self, token_contract: str) -> Optional[Dict[str, Any]]:
        """Get a position by token contract address"""
        res = self.supabase.client.table('lowcap_positions').select('*').eq('token_contract', token_contract).order('created_at', desc=True).limit(1).execute()
        return res.data[0] if res.data else None

    def mark_entry_executed(self, position_id: str, entry_number: int, tx_hash: str, 
                          cost_native: float = None, cost_usd: float = None, tokens_bought: float = None) -> bool:
        """Mark a specific entry as executed with transaction hash and cost tracking"""
        try:
            # Get the current position
            position = self.get_position(position_id)
            if not position:
                return False
            
            # Update the specific entry
            entries = position.get('entries', [])
            for entry in entries:
                if entry.get('entry_number') == entry_number:
                    entry['status'] = 'executed'
                    entry['tx_hash'] = tx_hash
                    entry['executed_at'] = datetime.now(timezone.utc).isoformat()
                    
                    # Add cost tracking if provided
                    if cost_native is not None:
                        entry['cost_native'] = cost_native
                    if cost_usd is not None:
                        entry['cost_usd'] = cost_usd
                    if tokens_bought is not None:
                        entry['tokens_bought'] = tokens_bought
                    break
            
            # Update the position with modified entries
            return self.update_entries(position_id, entries)
        except Exception as e:
            print(f"Error marking entry as executed: {e}")
            return False



