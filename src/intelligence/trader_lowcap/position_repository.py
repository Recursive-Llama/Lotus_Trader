from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


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

    def update_entries(self, position_id: str, entries: List[Dict[str, Any]]) -> bool:
        try:
            res = self.client.table('lowcap_positions').update({'entries': entries}).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating entries for {position_id}: {e}")
            return False

    def update_exits(self, position_id: str, exits: List[Dict[str, Any]]) -> bool:
        try:
            res = self.client.table('lowcap_positions').update({'exits': exits}).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating exits for {position_id}: {e}")
            return False

    def update_trend_entries(self, position_id: str, trend_entries: List[Dict[str, Any]]) -> bool:
        try:
            res = self.client.table('lowcap_positions').update({'trend_entries': trend_entries}).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating trend_entries for {position_id}: {e}")
            return False

    def update_trend_exits(self, position_id: str, trend_exits: List[Dict[str, Any]]) -> bool:
        try:
            res = self.client.table('lowcap_positions').update({'trend_exits': trend_exits}).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating trend_exits for {position_id}: {e}")
            return False

    def update_exit_rules(self, position_id: str, exit_rules: Dict[str, Any]) -> bool:
        """Update exit rules for a position"""
        try:
            res = self.client.table('lowcap_positions').update({'exit_rules': exit_rules}).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating exit_rules for {position_id}: {e}")
            return False

    def update_trend_exit_rules(self, position_id: str, trend_exit_rules: Dict[str, Any]) -> bool:
        """Update trend exit rules for a position"""
        try:
            res = self.client.table('lowcap_positions').update({'trend_exit_rules': trend_exit_rules}).eq('id', position_id).execute()
            return bool(res.data)
        except Exception as e:
            print(f"Error updating trend_exit_rules for {position_id}: {e}")
            return False

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

    def mark_trend_entry_executed(self, position_id: str, batch_id: str, trend_entry_number: int, tx_hash: str,
                                  cost_native: float, tokens_bought: float) -> bool:
        """Mark a specific trend entry as executed, updating costs and tokens bought."""
        try:
            position = self.get_position(position_id)
            if not position:
                return False

            trend_entries = position.get('trend_entries', []) or []
            for e in trend_entries:
                if e.get('batch_id') == batch_id and e.get('trend_entry_number') == trend_entry_number:
                    e['status'] = 'executed'
                    e['tx_hash'] = tx_hash
                    e['executed_at'] = datetime.now(timezone.utc).isoformat()
                    e['cost_native'] = cost_native
                    e['tokens_bought'] = tokens_bought
                    e['tokens_remaining'] = tokens_bought
                    break

            return self.update_trend_entries(position_id, trend_entries)
        except Exception as e:
            print(f"Error marking trend entry as executed: {e}")
            return False

    def mark_entry_failed(self, position_id: str, entry_number: int, reason: str) -> bool:
        """Mark a planned entry as failed with reason and timestamp."""
        try:
            position = self.get_position(position_id)
            if not position:
                return False

            entries = position.get('entries', []) or []
            for e in entries:
                if e.get('entry_number') == entry_number:
                    e['status'] = 'failed'
                    e['failed_reason'] = reason
                    e['failed_at'] = datetime.now(timezone.utc).isoformat()
                    break

            return self.update_entries(position_id, entries)
        except Exception as e:
            print(f"Error marking entry as failed: {e}")
            return False

    def mark_trend_entry_failed(self, position_id: str, batch_id: str, trend_entry_number: int, reason: str) -> bool:
        """Mark a trend entry as failed with reason and timestamp."""
        try:
            position = self.get_position(position_id)
            if not position:
                return False

            trend_entries = position.get('trend_entries', []) or []
            for e in trend_entries:
                if e.get('batch_id') == batch_id and e.get('trend_entry_number') == trend_entry_number:
                    e['status'] = 'failed'
                    e['failed_reason'] = reason
                    e['failed_at'] = datetime.now(timezone.utc).isoformat()
                    break

            return self.update_trend_entries(position_id, trend_entries)
        except Exception as e:
            print(f"Error marking trend entry as failed: {e}")
            return False

    def mark_trend_exit_executed(self, position_id: str, batch_id: str, trend_exit_number: int, tx_hash: str,
                                 tokens_sold: float, native_amount: float) -> bool:
        """Mark a specific trend exit as executed and decrement tokens from linked trend entries FIFO."""
        try:
            position = self.get_position(position_id)
            if not position:
                return False

            trend_exits = position.get('trend_exits', []) or []
            trend_entries = position.get('trend_entries', []) or []

            # Update exit record
            for x in trend_exits:
                if x.get('batch_id') == batch_id and x.get('trend_exit_number') == trend_exit_number:
                    x['status'] = 'executed'
                    x['tx_hash'] = tx_hash
                    x['executed_at'] = datetime.now(timezone.utc).isoformat()
                    x['tokens_sold'] = tokens_sold
                    x['native_amount'] = native_amount
                    break

            # Decrement tokens_remaining from matching batch entries FIFO
            remaining = tokens_sold
            for e in (e for e in trend_entries if e.get('batch_id') == batch_id and e.get('status') == 'executed'):
                tr = float(e.get('tokens_remaining', e.get('tokens_bought', 0.0)) or 0.0)
                if tr <= 0:
                    continue
                take = min(tr, remaining)
                e['tokens_remaining'] = tr - take
                remaining -= take
                if remaining <= 0:
                    break

            ok1 = self.update_trend_exits(position_id, trend_exits)
            ok2 = self.update_trend_entries(position_id, trend_entries)
            return ok1 and ok2
        except Exception as e:
            print(f"Error marking trend exit as executed: {e}")
            return False



