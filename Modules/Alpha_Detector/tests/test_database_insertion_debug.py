"""
Database Insertion Debug Test

This test isolates the database insertion issue to see exactly what's failing.
"""

import pytest
from datetime import datetime, timezone
from src.utils.supabase_manager import SupabaseManager

class TestDatabaseInsertionDebug:
    """Debug database insertion issues"""
    
    def test_simple_strand_insertion(self):
        """Test simple strand insertion"""
        print(f"\n🔍 TESTING SIMPLE STRAND INSERTION")
        print("="*50)
        
        supabase_manager = SupabaseManager()
        
        # Create a simple strand
        simple_strand = {
            'id': f"test_simple_{int(datetime.now().timestamp())}",
            'kind': 'test_simple',
            'module': 'alpha',
            'agent_id': 'test_agent',
            'team_member': 'test_member',
            'symbol': 'BTC',
            'timeframe': '1m',
            'session_bucket': 'GLOBAL',
            'regime': 'unknown',
            'tags': ['test:simple'],
            'module_intelligence': {
                'test': True,
                'message': 'Simple test strand'
            },
            'sig_sigma': 1.0,
            'sig_confidence': 1.0,
            'sig_direction': 'neutral',
            'outcome_score': 0.0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Get initial count
            initial_strands = supabase_manager.get_recent_strands(days=1)
            initial_count = len(initial_strands) if initial_strands else 0
            print(f"📊 Initial strands: {initial_count}")
            
            # Insert strand
            result = supabase_manager.insert_strand(simple_strand)
            print(f"📊 Insert result: {result}")
            
            # Check final count
            final_strands = supabase_manager.get_recent_strands(days=1)
            final_count = len(final_strands) if final_strands else 0
            new_strands = final_count - initial_count
            
            print(f"📊 Final strands: {final_count}")
            print(f"📊 New strands: {new_strands}")
            
            if new_strands > 0:
                print("✅ Simple strand insertion successful")
            else:
                print("❌ Simple strand insertion failed")
                
        except Exception as e:
            print(f"❌ Simple strand insertion error: {e}")
            raise
    
    def test_raw_data_strand_insertion(self):
        """Test the exact strand format that Raw Data Intelligence is trying to insert"""
        print(f"\n🔍 TESTING RAW DATA STRAND INSERTION")
        print("="*50)
        
        supabase_manager = SupabaseManager()
        
        # Create the exact strand format that Raw Data Intelligence creates
        raw_data_strand = {
            'id': f"raw_data_volume_spike_{int(datetime.now().timestamp())}",
            'kind': 'raw_data_volume_spike',
            'module': 'alpha',
            'agent_id': 'raw_data_intelligence',
            'team_member': 'raw_data_intelligence_agent',
            'symbol': 'BTC',
            'timeframe': '1m',
            'session_bucket': 'GLOBAL',
            'regime': 'unknown',
            'tags': ['intelligence:raw_data:volume_spike:medium'],
            'module_intelligence': {
                'pattern_type': 'volume_spike',
                'severity': 'medium',
                'confidence': 0.933,
                'details': [{'test': 'detail'}],
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': 121,
                'symbols': ['BTC']
            },
            'sig_sigma': 0.933,
            'sig_confidence': 0.933,
            'sig_direction': 'neutral',
            'outcome_score': 0.0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Get initial count
            initial_strands = supabase_manager.get_recent_strands(days=1)
            initial_count = len(initial_strands) if initial_strands else 0
            print(f"📊 Initial strands: {initial_count}")
            
            # Insert strand
            result = supabase_manager.insert_strand(raw_data_strand)
            print(f"📊 Insert result: {result}")
            
            # Check final count
            final_strands = supabase_manager.get_recent_strands(days=1)
            final_count = len(final_strands) if final_strands else 0
            new_strands = final_count - initial_count
            
            print(f"📊 Final strands: {final_count}")
            print(f"📊 New strands: {new_strands}")
            
            if new_strands > 0:
                print("✅ Raw data strand insertion successful")
                
                # Show the inserted strand
                if final_strands:
                    latest_strand = final_strands[-1]
                    print(f"📊 Latest strand: {latest_strand.get('kind', 'unknown')} from {latest_strand.get('agent_id', 'unknown')}")
            else:
                print("❌ Raw data strand insertion failed")
                
        except Exception as e:
            print(f"❌ Raw data strand insertion error: {e}")
            raise
    
    def test_strand_schema_validation(self):
        """Test if the strand matches the expected schema"""
        print(f"\n🔍 TESTING STRAND SCHEMA VALIDATION")
        print("="*50)
        
        # Test the exact strand format
        raw_data_strand = {
            'id': f"raw_data_test_{int(datetime.now().timestamp())}",
            'kind': 'raw_data_test',
            'module': 'alpha',
            'agent_id': 'raw_data_intelligence',
            'team_member': 'raw_data_intelligence_agent',
            'symbol': 'BTC',
            'timeframe': '1m',
            'session_bucket': 'GLOBAL',
            'regime': 'unknown',
            'tags': ['intelligence:raw_data:test:medium'],
            'module_intelligence': {
                'pattern_type': 'test',
                'severity': 'medium',
                'confidence': 0.5,
                'details': [],
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': 1,
                'symbols': ['BTC']
            },
            'sig_sigma': 0.5,
            'sig_confidence': 0.5,
            'sig_direction': 'neutral',
            'outcome_score': 0.0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Check required fields
        required_fields = ['id', 'kind', 'module', 'agent_id', 'team_member', 'symbol', 'timeframe', 'session_bucket', 'regime', 'tags', 'module_intelligence', 'sig_sigma', 'sig_confidence', 'sig_direction', 'outcome_score', 'created_at']
        
        print("📊 Schema validation:")
        for field in required_fields:
            if field in raw_data_strand:
                print(f"   ✅ {field}: {raw_data_strand[field]}")
            else:
                print(f"   ❌ {field}: MISSING")
        
        # Check data types
        print("\n📊 Data type validation:")
        print(f"   id: {type(raw_data_strand['id'])} - {raw_data_strand['id']}")
        print(f"   tags: {type(raw_data_strand['tags'])} - {raw_data_strand['tags']}")
        print(f"   module_intelligence: {type(raw_data_strand['module_intelligence'])} - {raw_data_strand['module_intelligence']}")
        print(f"   created_at: {type(raw_data_strand['created_at'])} - {raw_data_strand['created_at']}")
        
        # Check if tags is a list
        if isinstance(raw_data_strand['tags'], list):
            print("   ✅ tags is a list")
        else:
            print("   ❌ tags is not a list")
        
        # Check if module_intelligence is a dict
        if isinstance(raw_data_strand['module_intelligence'], dict):
            print("   ✅ module_intelligence is a dict")
        else:
            print("   ❌ module_intelligence is not a dict")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
