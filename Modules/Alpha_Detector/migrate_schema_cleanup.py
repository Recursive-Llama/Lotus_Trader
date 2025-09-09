#!/usr/bin/env python3
"""
Migration script for schema cleanup - Option A
Moves data from removed columns to module_intelligence JSONB
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from src.utils.supabase_manager import SupabaseManager

class SchemaCleanupMigration:
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        
    async def migrate_strands_to_module_intelligence(self):
        """Migrate data from removed columns to module_intelligence"""
        print("🔄 Starting schema cleanup migration...")
        
        try:
            # Get all strands that need migration
            query = """
                SELECT id, 
                       hypothesis_id, invariants, fails_when, contexts, evidence_refs, why_map, lineage,
                       mechanism_hypothesis, mechanism_supports, mechanism_fails_when, confluence_graph_data,
                       experiment_shape, experiment_grammar, lineage_parent_ids, lineage_mutation_note,
                       prioritization_score, directive_content, feedback_request, governance_boundary,
                       human_override_data, source_strands, clustering_columns,
                       module_intelligence
                FROM AD_strands 
                WHERE module_intelligence IS NULL OR module_intelligence = '{}'
                LIMIT 1000
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            if not result:
                print("✅ No strands need migration")
                return
                
            print(f"📊 Found {len(result)} strands to migrate")
            
            migrated_count = 0
            
            for strand in result:
                # Build module_intelligence from existing columns
                module_intelligence = strand.get('module_intelligence', {}) or {}
                
                # Add motif card data
                if strand.get('hypothesis_id'):
                    module_intelligence['hypothesis_id'] = strand['hypothesis_id']
                if strand.get('invariants'):
                    module_intelligence['invariants'] = strand['invariants']
                if strand.get('fails_when'):
                    module_intelligence['fails_when'] = strand['fails_when']
                if strand.get('contexts'):
                    module_intelligence['contexts'] = strand['contexts']
                if strand.get('evidence_refs'):
                    module_intelligence['evidence_refs'] = strand['evidence_refs']
                if strand.get('why_map'):
                    module_intelligence['why_map'] = strand['why_map']
                if strand.get('lineage'):
                    module_intelligence['lineage'] = strand['lineage']
                
                # Add CIL core functionality data
                if strand.get('mechanism_hypothesis'):
                    module_intelligence['mechanism_hypothesis'] = strand['mechanism_hypothesis']
                if strand.get('mechanism_supports'):
                    module_intelligence['mechanism_supports'] = strand['mechanism_supports']
                if strand.get('mechanism_fails_when'):
                    module_intelligence['mechanism_fails_when'] = strand['mechanism_fails_when']
                if strand.get('confluence_graph_data'):
                    module_intelligence['confluence_graph_data'] = strand['confluence_graph_data']
                if strand.get('experiment_shape'):
                    module_intelligence['experiment_shape'] = strand['experiment_shape']
                if strand.get('experiment_grammar'):
                    module_intelligence['experiment_grammar'] = strand['experiment_grammar']
                if strand.get('lineage_parent_ids'):
                    module_intelligence['lineage_parent_ids'] = strand['lineage_parent_ids']
                if strand.get('lineage_mutation_note'):
                    module_intelligence['lineage_mutation_note'] = strand['lineage_mutation_note']
                if strand.get('prioritization_score'):
                    module_intelligence['prioritization_score'] = strand['prioritization_score']
                if strand.get('directive_content'):
                    module_intelligence['directive_content'] = strand['directive_content']
                if strand.get('feedback_request'):
                    module_intelligence['feedback_request'] = strand['feedback_request']
                if strand.get('governance_boundary'):
                    module_intelligence['governance_boundary'] = strand['governance_boundary']
                if strand.get('human_override_data'):
                    module_intelligence['human_override_data'] = strand['human_override_data']
                
                # Add learning data
                if strand.get('source_strands'):
                    module_intelligence['source_strands'] = strand['source_strands']
                if strand.get('clustering_columns'):
                    module_intelligence['clustering_columns'] = strand['clustering_columns']
                
                # Update the strand
                update_query = """
                    UPDATE AD_strands 
                    SET module_intelligence = %s,
                        updated_at = %s
                    WHERE id = %s
                """
                
                await self.supabase_manager.execute_query(update_query, [
                    json.dumps(module_intelligence),
                    datetime.now(timezone.utc),
                    strand['id']
                ])
                
                migrated_count += 1
                
                if migrated_count % 100 == 0:
                    print(f"📈 Migrated {migrated_count} strands...")
            
            print(f"✅ Migration complete! Migrated {migrated_count} strands")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise
    
    async def verify_migration(self):
        """Verify that migration was successful"""
        print("🔍 Verifying migration...")
        
        try:
            # Check that module_intelligence has data
            query = """
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN module_intelligence IS NOT NULL AND module_intelligence != '{}' THEN 1 END) as with_data
                FROM AD_strands
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            if result:
                total = result[0]['total']
                with_data = result[0]['with_data']
                
                print(f"📊 Total strands: {total}")
                print(f"📊 Strands with module_intelligence data: {with_data}")
                print(f"📊 Migration success rate: {(with_data/total)*100:.1f}%")
                
                if with_data > 0:
                    print("✅ Migration verification successful!")
                else:
                    print("⚠️ No strands have module_intelligence data")
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            raise

async def main():
    """Run the migration"""
    migration = SchemaCleanupMigration()
    
    print("🚀 Starting Schema Cleanup Migration (Option A)")
    print("=" * 50)
    
    # Run migration
    await migration.migrate_strands_to_module_intelligence()
    
    # Verify migration
    await migration.verify_migration()
    
    print("=" * 50)
    print("🎉 Schema cleanup migration complete!")

if __name__ == "__main__":
    asyncio.run(main())
