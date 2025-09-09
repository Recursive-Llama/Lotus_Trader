"""
Test the new schema columns: agent_id, prediction_score, outcome_score, content
"""

import pytest
from datetime import datetime, timezone
from src.utils.supabase_manager import SupabaseManager


class TestSchemaColumns:
    """Test the new schema columns"""
    
    @pytest.fixture
    def supabase_manager(self):
        """Create SupabaseManager instance"""
        return SupabaseManager()
    
    def test_insert_strand_with_new_columns(self, supabase_manager):
        """Test inserting a strand with the new columns"""
        test_strand = {
            'id': f"test_schema_{int(datetime.now().timestamp())}",
            'kind': 'test_signal',
            'module': 'alpha',
            'symbol': 'BTC',
            'timeframe': '1h',
            'session_bucket': 'US',
            'regime': 'test',
            'tags': ['test:schema:columns'],
            'sig_sigma': 0.8,
            'sig_confidence': 0.7,
            'sig_direction': 'long',
            
            # New columns
            'agent_id': 'raw_data_intelligence',
            'prediction_score': 0.85,
            'outcome_score': 0.9,
            'content': {
                'message': 'Test message',
                'data': {'key': 'value'}
            },
            
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert the strand
        result = supabase_manager.insert_strand(test_strand)
        
        # Verify insertion was successful
        assert result is not None
        assert 'id' in result
        
        # Retrieve the strand to verify all columns
        retrieved_strand = supabase_manager.get_strand_by_id(test_strand['id'])
        
        assert retrieved_strand is not None
        assert retrieved_strand['agent_id'] == 'raw_data_intelligence'
        assert retrieved_strand['prediction_score'] == 0.85
        assert retrieved_strand['outcome_score'] == 0.9
        assert retrieved_strand['content']['message'] == 'Test message'
        assert retrieved_strand['content']['data']['key'] == 'value'
        
        print("✅ All new schema columns working correctly!")
    
    def test_update_prediction_score(self, supabase_manager):
        """Test updating prediction_score on existing strand"""
        # Create initial strand
        test_strand = {
            'id': f"test_update_{int(datetime.now().timestamp())}",
            'kind': 'test_signal',
            'module': 'alpha',
            'symbol': 'ETH',
            'timeframe': '4h',
            'session_bucket': 'EU',
            'regime': 'test',
            'tags': ['test:update:prediction'],
            'sig_sigma': 0.6,
            'sig_confidence': 0.5,
            'sig_direction': 'short',
            'agent_id': 'central_intelligence_layer',
            'prediction_score': None,  # Initially null
            'outcome_score': None,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert initial strand
        supabase_manager.insert_strand(test_strand)
        
        # Update prediction_score
        update_data = {
            'prediction_score': 0.75,
            'outcome_score': 0.8
        }
        
        result = supabase_manager.update_strand(test_strand['id'], update_data)
        assert result is not None
        
        # Verify update
        updated_strand = supabase_manager.get_strand_by_id(test_strand['id'])
        assert updated_strand['prediction_score'] == 0.75
        assert updated_strand['outcome_score'] == 0.8
        
        print("✅ Prediction and outcome score updates working correctly!")
    
    def test_content_field_flexibility(self, supabase_manager):
        """Test that content field can handle various data types"""
        test_cases = [
            {
                'content': {'simple': 'string'},
                'description': 'simple string'
            },
            {
                'content': {'nested': {'data': [1, 2, 3]}},
                'description': 'nested data with arrays'
            },
            {
                'content': {'complex': {'metrics': {'accuracy': 0.95, 'precision': 0.87}}},
                'description': 'complex nested metrics'
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            test_strand = {
                'id': f"test_content_{i}_{int(datetime.now().timestamp())}",
                'kind': 'test_signal',
                'module': 'alpha',
                'symbol': 'BTC',
                'timeframe': '1h',
                'session_bucket': 'US',
                'regime': 'test',
                'tags': ['test:content:flexibility'],
                'sig_sigma': 0.5,
                'sig_confidence': 0.5,
                'sig_direction': 'neutral',
                'agent_id': 'test_agent',
                'content': test_case['content'],
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert and verify
            result = supabase_manager.insert_strand(test_strand)
            assert result is not None
            
            retrieved = supabase_manager.get_strand_by_id(test_strand['id'])
            assert retrieved['content'] == test_case['content']
            
            print(f"✅ Content field test passed: {test_case['description']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
