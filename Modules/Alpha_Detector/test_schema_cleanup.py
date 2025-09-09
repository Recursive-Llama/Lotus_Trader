#!/usr/bin/env python3
"""
Test script to verify schema cleanup changes work correctly
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any
from src.utils.supabase_manager import SupabaseManager

class SchemaCleanupTest:
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        
    async def test_strand_creation_with_module_intelligence(self):
        """Test creating a strand with module_intelligence data"""
        print("🧪 Testing strand creation with module_intelligence...")
        
        try:
            # Create test strand with module_intelligence
            test_strand = {
                'id': f'test_strand_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'module': 'alpha',
                'kind': 'intelligence',
                'symbol': 'BTC',
                'timeframe': '1m',
                'session_bucket': 'test',
                'regime': 'bull',
                'tags': ['test', 'schema_cleanup'],
                'sig_sigma': 0.8,
                'sig_confidence': 0.75,
                'confidence': 0.8,
                'sig_direction': 'long',
                'module_intelligence': {
                    'invariants': ['volume_spike', 'price_momentum'],
                    'fails_when': ['low_volume', 'sideways_market'],
                    'contexts': {
                        'regimes': ['bull', 'uptrend'],
                        'sessions': ['asia', 'europe'],
                        'timeframes': ['1m', '5m']
                    },
                    'mechanism_hypothesis': 'Volume spikes indicate institutional interest',
                    'hypothesis_id': 'test_hypothesis_001',
                    'evidence_refs': ['strand_001', 'strand_002'],
                    'why_map': 'High volume + price momentum = institutional buying',
                    'lineage': ['parent_pattern_001'],
                    'experiment_shape': 'durability',
                    'experiment_grammar': {'duration': '1h', 'threshold': 0.8},
                    'lineage_parent_ids': ['parent_001', 'parent_002'],
                    'lineage_mutation_note': 'Enhanced with volume filter',
                    'prioritization_score': 0.85,
                    'directive_content': {'type': 'beacon', 'priority': 'high'},
                    'feedback_request': {'type': 'outcome', 'deadline': '1h'},
                    'governance_boundary': 'experimental',
                    'human_override_data': {'reason': 'test', 'timestamp': datetime.now().isoformat()},
                    'source_strands': ['source_001', 'source_002'],
                    'clustering_columns': ['symbol', 'timeframe', 'pattern_type']
                },
                'accumulated_score': 0.75,
                'lesson': 'Volume spikes work well in bull markets',
                'braid_level': 2,
                'status': 'active',
                'feature_version': 1,
                'derivation_spec_id': 'test_spec_v1'
            }
            
            # Insert test strand
            insert_query = """
                INSERT INTO AD_strands (
                    id, module, kind, symbol, timeframe, session_bucket, regime, tags,
                    sig_sigma, sig_confidence, confidence, sig_direction,
                    module_intelligence, accumulated_score, lesson, braid_level,
                    status, feature_version, derivation_spec_id
                ) VALUES (
                    %(id)s, %(module)s, %(kind)s, %(symbol)s, %(timeframe)s, %(session_bucket)s, %(regime)s, %(tags)s,
                    %(sig_sigma)s, %(sig_confidence)s, %(confidence)s, %(sig_direction)s,
                    %(module_intelligence)s, %(accumulated_score)s, %(lesson)s, %(braid_level)s,
                    %(status)s, %(feature_version)s, %(derivation_spec_id)s
                ) RETURNING id
            """
            
            result = await self.supabase_manager.execute_query(insert_query, test_strand)
            
            if result:
                print("✅ Test strand created successfully")
                return test_strand['id']
            else:
                print("❌ Failed to create test strand")
                return None
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return None
    
    async def test_strand_retrieval(self, strand_id: str):
        """Test retrieving a strand and accessing module_intelligence data"""
        print(f"🧪 Testing strand retrieval for {strand_id}...")
        
        try:
            query = """
                SELECT id, symbol, timeframe, module_intelligence,
                       accumulated_score, lesson, braid_level,
                       status, feature_version, derivation_spec_id
                FROM AD_strands 
                WHERE id = %s
            """
            
            result = await self.supabase_manager.execute_query(query, [strand_id])
            
            if result:
                strand = result[0]
                print("✅ Strand retrieved successfully")
                
                # Test accessing module_intelligence data
                module_intel = strand.get('module_intelligence', {})
                
                print(f"📊 Symbol: {strand['symbol']}")
                print(f"📊 Timeframe: {strand['timeframe']}")
                print(f"📊 Status: {strand['status']}")
                print(f"📊 Feature Version: {strand['feature_version']}")
                print(f"📊 Module Intelligence Keys: {list(module_intel.keys())}")
                
                # Test specific module_intelligence fields
                if 'invariants' in module_intel:
                    print(f"📊 Invariants: {module_intel['invariants']}")
                if 'mechanism_hypothesis' in module_intel:
                    print(f"📊 Mechanism Hypothesis: {module_intel['mechanism_hypothesis']}")
                if 'experiment_shape' in module_intel:
                    print(f"📊 Experiment Shape: {module_intel['experiment_shape']}")
                
                return True
            else:
                print("❌ Strand not found")
                return False
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    async def test_unified_clustering_fields(self, strand_id: str):
        """Test the new unified clustering fields"""
        print(f"🧪 Testing unified clustering fields for {strand_id}...")
        
        try:
            query = """
                SELECT status, feature_version, derivation_spec_id
                FROM AD_strands 
                WHERE id = %s
            """
            
            result = await self.supabase_manager.execute_query(query, [strand_id])
            
            if result:
                strand = result[0]
                print("✅ Unified clustering fields retrieved successfully")
                print(f"📊 Status: {strand['status']}")
                print(f"📊 Feature Version: {strand['feature_version']}")
                print(f"📊 Derivation Spec ID: {strand['derivation_spec_id']}")
                return True
            else:
                print("❌ Strand not found")
                return False
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    async def cleanup_test_data(self, strand_id: str):
        """Clean up test data"""
        print(f"🧹 Cleaning up test data for {strand_id}...")
        
        try:
            query = "DELETE FROM AD_strands WHERE id = %s"
            await self.supabase_manager.execute_query(query, [strand_id])
            print("✅ Test data cleaned up")
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")

async def main():
    """Run the schema cleanup tests"""
    test = SchemaCleanupTest()
    
    print("🚀 Starting Schema Cleanup Tests")
    print("=" * 50)
    
    # Test 1: Create strand with module_intelligence
    strand_id = await test.test_strand_creation_with_module_intelligence()
    
    if strand_id:
        # Test 2: Retrieve strand and access module_intelligence
        success = await test.test_strand_retrieval(strand_id)
        
        if success:
            # Test 3: Test unified clustering fields
            await test.test_unified_clustering_fields(strand_id)
        
        # Cleanup
        await test.cleanup_test_data(strand_id)
    
    print("=" * 50)
    print("🎉 Schema cleanup tests complete!")

if __name__ == "__main__":
    asyncio.run(main())
