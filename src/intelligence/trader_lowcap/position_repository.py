from typing import Dict, Any, Optional


class PositionRepository:
    def __init__(self, supabase_manager):
        self.supabase = supabase_manager
        # Handle both DirectTableCommunicator and SupabaseManager
        if hasattr(supabase_manager, 'db_manager'):
            self.client = supabase_manager.db_manager.client
        else:
            self.client = supabase_manager.client

    def create_position(self, position: Dict[str, Any]) -> bool:
        res = self.client.table('lowcap_positions').insert(position).execute()
        return bool(res.data)

    def get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get a position by ID"""
        res = self.client.table('lowcap_positions').select('*').eq('id', position_id).execute()
        return res.data[0] if res.data else None

    def update_position(self, position_id: str, position: Dict[str, Any]) -> bool:
        """Update a position with new data"""
        try:
            res = self.client.table('lowcap_positions').update(position).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating position {position_id}: {e}")
            return False

    def get_position_by_book_id(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent position created from a specific decision/strand (book_id)."""
        try:
            res = (
                self.client
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
            res = self.client.table('lowcap_positions').update({'tax_pct': tax_pct}).eq('token_contract', token_contract).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating tax percentage: {e}")
            return False

    def get_position_by_token(self, token_contract: str) -> Optional[Dict[str, Any]]:
        """Get a position by token contract address"""
        res = self.client.table('lowcap_positions').select('*').eq('token_contract', token_contract).order('created_at', desc=True).limit(1).execute()
        return res.data[0] if res.data else None



