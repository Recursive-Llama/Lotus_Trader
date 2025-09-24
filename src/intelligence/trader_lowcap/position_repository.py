from typing import Dict, Any, Optional, List


class PositionRepository:
    def __init__(self, supabase_manager):
        self.supabase = supabase_manager

    def create_position(self, position: Dict[str, Any]) -> bool:
        res = self.supabase.client.table('lowcap_positions').insert(position).execute()
        return bool(res.data)

    def update_entries(self, position_id: str, entries: List[Dict[str, Any]]) -> bool:
        res = self.supabase.client.table('lowcap_positions').update({'entries': entries}).eq('id', position_id).execute()
        return bool(res.data)

    def update_exits(self, position_id: str, exits: List[Dict[str, Any]]) -> bool:
        res = self.supabase.client.table('lowcap_positions').update({'exits': exits}).eq('id', position_id).execute()
        return bool(res.data)

    def get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get a position by ID"""
        res = self.supabase.client.table('lowcap_positions').select('*').eq('id', position_id).execute()
        return res.data[0] if res.data else None

    def update_position(self, position_id: str, position: Dict[str, Any]) -> bool:
        """Update a position with new data"""
        res = self.supabase.client.table('lowcap_positions').update(position).eq('id', position_id).execute()
        return bool(res.data)

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

    def mark_entry_executed(self, position_id: str, entry_number: int, tx_hash: str) -> bool:
        """Mark a specific entry as executed with transaction hash"""
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
                    break
            
            # Update the position with modified entries
            return self.update_entries(position_id, entries)
        except Exception as e:
            print(f"Error marking entry as executed: {e}")
            return False



