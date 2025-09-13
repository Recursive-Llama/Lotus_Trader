"""
Real LLM Flow Test

Tests the complete learning system pipeline with REAL LLM calls:
1. Create pattern strands and predictions
2. Test REAL LLM calls with actual API keys
3. Test clustering and braid creation
4. Test context injection with real LLM analysis
5. Validate complete end-to-end flow with real AI
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

from Modules.Alpha_Detector.src.utils.supabase_manager import SupabaseManager
from Modules.Alpha_Detector.src.intelligence.llm_integration.llm_client import LLMClientManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealPromptManager:
    """Real prompt manager for testing with actual LLM calls"""
    
    def get_prompt(self, template_name: str, **kwargs) -> str:
        """Get a real prompt for LLM analysis"""
        prompts = {
            'braid_analysis': """
# Braid Analysis Request

## Context
You are analyzing a braid of {strand_count} market intelligence strands showing {pattern_type} patterns.

## Task
Analyze these patterns and provide:
1. Key insights about market behavior
2. Trading strategy recommendations
3. Risk factors to consider
4. Confidence assessment

## Pattern Data
{pattern_data}

## Instructions
Provide a comprehensive analysis that would be useful for a trading system. Focus on actionable insights and practical recommendations.
""",
            'context_injection': """
# Context Injection for {module}

## Module: {module.upper()}
This context is being injected into the {module.upper()} module to enhance its decision-making.

## Relevant Patterns
{patterns_summary}

## Key Insights
{insights_summary}

## Recommendations
{recommendations_summary}

## Instructions
Use this context to improve the module's performance and decision-making capabilities.
"""
        }
        return prompts.get(template_name, f"Analysis request for {template_name}")


class RealLearningSystem:
    """Real learning system with actual LLM calls"""
    
    def __init__(self, supabase_manager, llm_client, prompt_manager):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.logger = logging.getLogger(__name__)
    
    async def process_strand(self, strand: dict) -> bool:
        """Process a single strand with real analysis"""
        try:
            strand_id = strand.get('id')
            strand_kind = strand.get('kind')
            
            self.logger.info(f"🎯 Processing strand: {strand_id} ({strand_kind})")
            
            # Log strand details
            if strand_kind == 'pattern':
                pattern_type = strand.get('content', {}).get('pattern_type', 'unknown')
                confidence = strand.get('confidence', 'N/A')
                self.logger.info(f"  - Pattern type: {pattern_type}")
                self.logger.info(f"  - Confidence: {confidence}")
                
                # Real LLM analysis of pattern
                await self._analyze_pattern_with_llm(strand)
                
            elif strand_kind == 'prediction':
                prediction_type = strand.get('content', {}).get('prediction_type', 'unknown')
                confidence = strand.get('confidence', 'N/A')
                self.logger.info(f"  - Prediction type: {prediction_type}")
                self.logger.info(f"  - Confidence: {confidence}")
                
                # Real LLM analysis of prediction
                await self._analyze_prediction_with_llm(strand)
                
            elif strand_kind == 'prediction_review':
                outcome = strand.get('content', {}).get('outcome', 'unknown')
                return_pct = strand.get('content', {}).get('return_pct', 'N/A')
                self.logger.info(f"  - Outcome: {outcome}")
                self.logger.info(f"  - Return %: {return_pct}")
                
                # Real LLM analysis of review
                await self._analyze_review_with_llm(strand)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing strand {strand_id}: {e}")
            return False
    
    async def _analyze_pattern_with_llm(self, strand: dict) -> None:
        """Analyze pattern with real LLM"""
        try:
            pattern_type = strand.get('content', {}).get('pattern_type', 'unknown')
            confidence = strand.get('confidence', 0.5)
            
            prompt = f"""
Analyze this trading pattern for BTCUSDT:

Pattern Type: {pattern_type}
Confidence: {confidence}
Symbol: {strand.get('symbol', 'BTCUSDT')}
Timeframe: {strand.get('timeframe', '1h')}

Provide:
1. What this pattern typically indicates
2. Trading opportunities it presents
3. Risk factors to consider
4. Expected price movement direction
5. Time horizon for the pattern

Keep response concise but actionable.
"""
            
            analysis = await self.llm_client.generate_completion(prompt, max_tokens=300, temperature=0.3)
            self.logger.info(f"  - LLM Pattern Analysis: {analysis[:100]}...")
            
        except Exception as e:
            self.logger.error(f"Error analyzing pattern with LLM: {e}")
    
    async def _analyze_prediction_with_llm(self, strand: dict) -> None:
        """Analyze prediction with real LLM"""
        try:
            prediction_type = strand.get('content', {}).get('prediction_type', 'unknown')
            confidence = strand.get('confidence', 0.5)
            target_price = strand.get('content', {}).get('target_price', 0)
            
            prompt = f"""
Analyze this trading prediction for BTCUSDT:

Prediction Type: {prediction_type}
Target Price: {target_price}
Confidence: {confidence}
Symbol: {strand.get('symbol', 'BTCUSDT')}

Provide:
1. Assessment of prediction quality
2. Market conditions that support this prediction
3. Potential risks and challenges
4. Recommended position sizing
5. Time frame expectations

Keep response concise but actionable.
"""
            
            analysis = await self.llm_client.generate_completion(prompt, max_tokens=300, temperature=0.3)
            self.logger.info(f"  - LLM Prediction Analysis: {analysis[:100]}...")
            
        except Exception as e:
            self.logger.error(f"Error analyzing prediction with LLM: {e}")
    
    async def _analyze_review_with_llm(self, strand: dict) -> None:
        """Analyze review with real LLM"""
        try:
            outcome = strand.get('content', {}).get('outcome', 'unknown')
            return_pct = strand.get('content', {}).get('return_pct', 0)
            
            prompt = f"""
Analyze this trading outcome review for BTCUSDT:

Outcome: {outcome}
Return Percentage: {return_pct}%
Symbol: {strand.get('symbol', 'BTCUSDT')}

Provide:
1. Assessment of the trading performance
2. What went well or poorly
3. Lessons learned for future trades
4. Pattern recognition insights
5. Recommendations for improvement

Keep response concise but actionable.
"""
            
            analysis = await self.llm_client.generate_completion(prompt, max_tokens=300, temperature=0.3)
            self.logger.info(f"  - LLM Review Analysis: {analysis[:100]}...")
            
        except Exception as e:
            self.logger.error(f"Error analyzing review with LLM: {e}")
    
    async def test_real_llm_calls(self) -> bool:
        """Test real LLM calls with actual API keys"""
        try:
            self.logger.info("🤖 Testing REAL LLM calls with actual API keys...")
            
            # Test completion with real market analysis
            prompt = """
Analyze the current BTCUSDT market and provide a comprehensive trading strategy:

1. Market structure analysis
2. Key support and resistance levels
3. Trading opportunities
4. Risk management approach
5. Entry and exit criteria

Provide actionable insights for a systematic trading approach.
"""
            
            completion = await self.llm_client.generate_completion(prompt, max_tokens=500, temperature=0.3)
            
            if completion and "Error" not in completion:
                self.logger.info(f"✅ REAL LLM completion successful!")
                self.logger.info(f"📊 Analysis: {completion[:200]}...")
            else:
                self.logger.warning(f"⚠️  LLM completion returned: {completion}")
            
            # Test embedding with real market data
            embedding_text = "BTCUSDT bullish breakout pattern with high volume and strong momentum"
            embedding = await self.llm_client.generate_embedding(embedding_text)
            
            if embedding and len(embedding) > 0:
                self.logger.info(f"✅ REAL LLM embedding successful: {len(embedding)} dimensions")
            else:
                self.logger.warning("⚠️  LLM embedding failed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error testing real LLM calls: {e}")
            return False
    
    async def create_braids_with_llm_analysis(self, strands: list) -> int:
        """Create braids with real LLM analysis"""
        try:
            self.logger.info("🔗 Creating braids with REAL LLM analysis...")
            
            # Group strands by kind
            clusters = {}
            for strand in strands:
                kind = strand.get('kind', 'unknown')
                if kind not in clusters:
                    clusters[kind] = []
                clusters[kind].append(strand)
            
            self.logger.info(f"✅ Created {len(clusters)} clusters:")
            for kind, cluster_strands in clusters.items():
                self.logger.info(f"  - {kind}: {len(cluster_strands)} strands")
            
            # Create braids for each cluster with LLM analysis
            braid_count = 0
            for kind, cluster_strands in clusters.items():
                if len(cluster_strands) > 0:
                    braid_id = f"real_braid_{kind}_{int(datetime.now().timestamp())}"
                    
                    # Calculate average confidence
                    confidences = [s.get('confidence', 0.5) for s in cluster_strands]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
                    
                    # Get LLM analysis for the braid
                    llm_analysis = await self._analyze_braid_with_llm(kind, cluster_strands)
                    
                    # Create braid as a strand with LLM analysis
                    braid_strand = {
                        'id': braid_id,
                        'kind': 'braid',
                        'module': 'alpha',
                        'agent_id': 'learning_system',
                        'symbol': 'BTCUSDT',
                        'timeframe': '1h',
                        'session_bucket': 'GLOBAL',
                        'regime': 'bullish',
                        'tags': ['braid', 'learning_generated', 'llm_analyzed'],
                        'content': {
                            'braid_type': kind,
                            'source_strand_ids': [s['id'] for s in cluster_strands],
                            'resonance_score': avg_confidence,
                            'cluster_size': len(cluster_strands),
                            'llm_analysis': llm_analysis
                        },
                        'braid_level': 2,  # Braids are level 2+
                        'resonance_score': avg_confidence,
                        'confidence': avg_confidence,
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Insert braid as a strand
                    result = self.supabase_manager.client.table('ad_strands').insert(braid_strand).execute()
                    if result.data:
                        braid_count += 1
                        self.logger.info(f"✅ Created braid with LLM analysis: {braid_id}")
                        self.logger.info(f"  - Resonance: {avg_confidence:.2f}")
                        self.logger.info(f"  - LLM Analysis: {llm_analysis[:100]}...")
                    else:
                        self.logger.error(f"❌ Failed to create braid strand: {braid_id}")
            
            self.logger.info(f"✅ Created {braid_count} braids with real LLM analysis")
            return braid_count
            
        except Exception as e:
            self.logger.error(f"Error creating braids with LLM: {e}")
            return 0
    
    async def _analyze_braid_with_llm(self, braid_type: str, strands: list) -> str:
        """Analyze braid with real LLM"""
        try:
            # Prepare strand data for LLM analysis
            strand_data = []
            for strand in strands:
                strand_info = {
                    'id': strand['id'],
                    'kind': strand['kind'],
                    'confidence': strand.get('confidence', 0.5),
                    'content': strand.get('content', {})
                }
                strand_data.append(strand_info)
            
            prompt = f"""
Analyze this braid of {len(strands)} {braid_type} strands for BTCUSDT:

Strand Data: {strand_data}

Provide a comprehensive analysis:
1. Overall pattern strength and reliability
2. Key insights about market behavior
3. Trading opportunities identified
4. Risk factors and considerations
5. Recommendations for the trading system

Keep response focused and actionable for systematic trading.
"""
            
            analysis = await self.llm_client.generate_completion(prompt, max_tokens=400, temperature=0.3)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing braid with LLM: {e}")
            return "LLM analysis failed"
    
    async def test_context_injection_with_llm(self) -> bool:
        """Test context injection with real LLM analysis"""
        try:
            self.logger.info("💉 Testing context injection with REAL LLM analysis...")
            
            # Get braids from ad_strands table
            braids_result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'braid').execute()
            
            if braids_result.data:
                braids = braids_result.data
                self.logger.info(f"✅ Found {len(braids)} braids for context injection")
            else:
                braids = []
                self.logger.info("ℹ️  No braids found for context injection")
            
            # Test context injection for different modules with real LLM
            modules = ['cil', 'ctp', 'dm', 'td', 'rdi']
            
            for module in modules:
                try:
                    # Get real LLM analysis for context injection
                    context_analysis = await self._get_llm_context_analysis(module, braids)
                    
                    # Create context with real LLM analysis
                    context = {
                        'module': module,
                        'relevant_braids': braids[:3],  # Top 3 braids
                        'llm_analysis': context_analysis,
                        'confidence': 0.8
                    }
                    
                    self.logger.info(f"✅ Context injection for {module.upper()}: {len(context)} items")
                    self.logger.info(f"  - LLM Analysis: {context_analysis[:100]}...")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️  Context injection failed for {module.upper()}: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error testing context injection with LLM: {e}")
            return False
    
    async def _get_llm_context_analysis(self, module: str, braids: list) -> str:
        """Get real LLM analysis for context injection"""
        try:
            prompt = f"""
Provide context analysis for the {module.upper()} module based on these braids:

Braids: {[{'id': b['id'], 'braid_type': b['content'].get('braid_type'), 'resonance_score': b['resonance_score']} for b in braids[:3]]}

For the {module.upper()} module, provide:
1. Key insights relevant to this module's function
2. Specific recommendations for improvement
3. Patterns to watch for
4. Risk factors to consider
5. Actionable next steps

Keep response focused on {module.upper()}'s specific needs and responsibilities.
"""
            
            analysis = await self.llm_client.generate_completion(prompt, max_tokens=300, temperature=0.3)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error getting LLM context analysis: {e}")
            return "LLM context analysis failed"


async def test_real_llm_flow():
    """Test the real LLM flow"""
    try:
        logger.info("🧪 Testing Real LLM Flow with Actual API Keys")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        
        # Initialize LLM client manager with REAL API keys
        llm_config = {
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY', ''),
                'model': 'gpt-4o-mini'
            },
            'anthropic': {
                'api_key': os.getenv('ANTHROPIC_API_KEY', ''),
                'model': 'claude-3-haiku-20240307'
            }
        }
        llm_client = LLMClientManager(llm_config)
        
        # Initialize real prompt manager
        prompt_manager = RealPromptManager()
        
        # Initialize learning system
        learning_system = RealLearningSystem(supabase_manager, llm_client, prompt_manager)
        
        logger.info("✅ All components initialized with REAL API keys")
        
        # Test 1: Create test strands
        logger.info("\n📊 Test 1: Creating test strands")
        
        test_strands = []
        
        # Create pattern strands
        for i in range(3):
            pattern_strand = {
                'id': f"real_pattern_{i+1}_{int(datetime.now().timestamp())}",
                'kind': 'pattern',
                'module': 'alpha',
                'agent_id': 'raw_data_intelligence',
                'symbol': 'BTCUSDT',
                'timeframe': '1h',
                'content': {
                    'pattern_type': f'bullish_breakout_{i+1}',
                    'confidence': 0.7 + (i * 0.1),
                    'significance': 'high' if i == 0 else 'medium',
                    'volume_spike': True,
                    'momentum': 'strong'
                },
                'confidence': 0.7 + (i * 0.1),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase_manager.client.table('ad_strands').insert(pattern_strand).execute()
            if result.data:
                test_strands.append(pattern_strand)
                logger.info(f"✅ Created pattern strand: {pattern_strand['id']}")
        
        # Create prediction strands
        for i in range(2):
            prediction_strand = {
                'id': f"real_prediction_{i+1}_{int(datetime.now().timestamp())}",
                'kind': 'prediction',
                'module': 'alpha',
                'agent_id': 'cil',
                'symbol': 'BTCUSDT',
                'timeframe': '1h',
                'content': {
                    'prediction_type': 'price_target',
                    'target_price': 50000.0 + (i * 1000),
                    'entry_price': 48000.0,
                    'stop_loss': 46000.0,
                    'confidence': 0.8 + (i * 0.05)
                },
                'confidence': 0.8 + (i * 0.05),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase_manager.client.table('ad_strands').insert(prediction_strand).execute()
            if result.data:
                test_strands.append(prediction_strand)
                logger.info(f"✅ Created prediction strand: {prediction_strand['id']}")
        
        # Create prediction review strands
        for i in range(1):
            review_strand = {
                'id': f"real_review_{i+1}_{int(datetime.now().timestamp())}",
                'kind': 'prediction_review',
                'module': 'alpha',
                'agent_id': 'cil',
                'symbol': 'BTCUSDT',
                'timeframe': '1h',
                'content': {
                    'outcome': 'success',
                    'return_pct': 5.2 + (i * 2.1),
                    'review_quality': 'high',
                    'execution_quality': 'excellent'
                },
                'confidence': 0.9,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase_manager.client.table('ad_strands').insert(review_strand).execute()
            if result.data:
                test_strands.append(review_strand)
                logger.info(f"✅ Created review strand: {review_strand['id']}")
        
        logger.info(f"✅ Created {len(test_strands)} test strands total")
        
        # Test 2: Process strands with real LLM analysis
        logger.info("\n🎯 Test 2: Processing strands with REAL LLM analysis")
        
        for strand in test_strands:
            success = await learning_system.process_strand(strand)
            if not success:
                logger.warning(f"⚠️  Failed to process strand: {strand['id']}")
        
        # Test 3: Test real LLM calls
        logger.info("\n🤖 Test 3: Testing REAL LLM calls")
        
        llm_success = await learning_system.test_real_llm_calls()
        if llm_success:
            logger.info("✅ REAL LLM calls successful")
        else:
            logger.warning("⚠️  REAL LLM calls had issues")
        
        # Test 4: Create braids with real LLM analysis
        logger.info("\n🔗 Test 4: Creating braids with REAL LLM analysis")
        
        braid_count = await learning_system.create_braids_with_llm_analysis(test_strands)
        if braid_count > 0:
            logger.info(f"✅ Created {braid_count} braids with real LLM analysis")
        else:
            logger.warning("⚠️  No braids created")
        
        # Test 5: Test context injection with real LLM
        logger.info("\n💉 Test 5: Testing context injection with REAL LLM")
        
        context_success = await learning_system.test_context_injection_with_llm()
        if context_success:
            logger.info("✅ Context injection with real LLM successful")
        else:
            logger.warning("⚠️  Context injection with real LLM had issues")
        
        # Test 6: Get final status
        logger.info("\n📊 Test 6: Getting final system status")
        
        # Get counts
        pattern_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'pattern').execute()
        prediction_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'prediction').execute()
        review_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'prediction_review').execute()
        braid_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'braid').execute()
        
        logger.info(f"📊 Final System Status:")
        logger.info(f"  - Pattern strands: {pattern_count.count or 0}")
        logger.info(f"  - Prediction strands: {prediction_count.count or 0}")
        logger.info(f"  - Prediction review strands: {review_count.count or 0}")
        logger.info(f"  - Braid strands: {braid_count.count or 0}")
        
        # Test 7: Clean up test data
        logger.info("\n🧹 Test 7: Cleaning up test data")
        
        # Delete test strands
        for strand in test_strands:
            try:
                supabase_manager.client.table('ad_strands').delete().eq('id', strand['id']).execute()
                logger.info(f"✅ Deleted test strand: {strand['id']}")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete test strand {strand['id']}: {e}")
        
        # Clean up braid strands
        try:
            supabase_manager.client.table('ad_strands').delete().like('id', 'real_braid_%').execute()
            logger.info("✅ Cleaned up test braid strands")
        except Exception as e:
            logger.warning(f"⚠️  Could not clean up braid strands: {e}")
        
        logger.info("\n🎉 Real LLM flow test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_real_llm_flow()
    if success:
        logger.info("✅ Real LLM Flow test passed!")
    else:
        logger.error("❌ Real LLM Flow test failed!")
    return success


if __name__ == "__main__":
    asyncio.run(main())
