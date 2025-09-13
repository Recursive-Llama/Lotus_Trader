
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

class MockSupabaseManager:
    def __init__(self):
        self.strands = []
        self.connected = True
    
    async def test_connection(self):
        return True
    
    async def create_strand(self, strand_data):
        strand_id = strand_data.get('id', f"mock_{len(self.strands)}")
        self.strands.append({**strand_data, 'id': strand_id})
        return strand_id
    
    async def get_strand(self, strand_id):
        for strand in self.strands:
            if strand['id'] == strand_id:
                return strand
        return None
    
    async def update_strand(self, strand_id, updates):
        for strand in self.strands:
            if strand['id'] == strand_id:
                strand.update(updates)
                return True
        return False
    
    async def delete_strand(self, strand_id):
        self.strands = [s for s in self.strands if s['id'] != strand_id]
        return True

class MockLLMClient:
    def __init__(self):
        self.call_count = 0
    
    async def generate_response(self, prompt, **kwargs):
        self.call_count += 1
        return {
            'content': f"Mock response for: {prompt[:50]}...",
            'usage': {'total_tokens': 100}
        }

class MockMarketDataProcessor:
    def __init__(self, supabase_manager):
        self.supabase_manager = supabase_manager
    
    async def process_market_data(self, data):
        return {
            'processed': True,
            'original_data': data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

class MockRawDataIntelligenceAgent:
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
    
    async def analyze_market_data(self, data):
        return [{
            'id': f"pattern_{len(self.supabase_manager.strands)}",
            'kind': 'pattern',
            'content': {
                'pattern_type': 'mock_pattern',
                'confidence': 0.8
            }
        }]
    
    async def start(self, discovery_system):
        return True

class MockSimplifiedCIL:
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
    
    async def process_patterns(self, patterns):
        return [{
            'id': f"prediction_{len(self.supabase_manager.strands)}",
            'kind': 'prediction_review',
            'content': {
                'group_signature': 'mock_prediction',
                'confidence': 0.85
            }
        }]
    
    async def start(self):
        return True

class MockAgentDiscoverySystem:
    def __init__(self, supabase_manager):
        self.supabase_manager = supabase_manager
    
    async def discover_agents(self):
        return ['mock_agent_1', 'mock_agent_2']

class MockInputProcessor:
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
    
    async def process_input(self, data):
        return {'processed_input': data}

class MockCILPlanComposer:
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
    
    async def compose_plan(self, data):
        return {'plan': 'mock_plan'}

class MockExperimentOrchestrationEngine:
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client

class MockPredictionOutcomeTracker:
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client

class MockLearningFeedbackEngine:
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client

class MockOutputDirectiveSystem:
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
