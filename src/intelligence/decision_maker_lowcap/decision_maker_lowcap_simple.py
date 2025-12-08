"""
Decision Maker Lowcap - Simplified Version

Simple 4-step decision process:
1. Do we already have this token?
2. How well has this trader performed?
3. How much capital do we have to buy?
4. Decision: allocate 2-6% (4% default)
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from intelligence.universal_learning.coefficient_reader import CoefficientReader
from intelligence.universal_learning.bucket_vocabulary import BucketVocabulary
from src.intelligence.lowcap_portfolio_manager.regime.bucket_context import fetch_bucket_phase_snapshot
from src.intelligence.lowcap_portfolio_manager.jobs.regime_ae_calculator import BUCKET_DRIVERS

logger = logging.getLogger(__name__)


class DecisionMakerLowcapSimple:
    """
    Simplified Decision Maker Lowcap
    
    Simple 4-step decision process for social lowcap trading.
    """
    
    def __init__(self, supabase_manager, config: Dict[str, Any] = None, learning_system=None):
        """
        Initialize Simplified Decision Maker Lowcap
        
        Args:
            supabase_manager: Database manager for positions and curators
            config: Configuration dictionary
            learning_system: Reference to Universal Learning System for callbacks
        """
        self.supabase_manager = supabase_manager
        self.learning_system = learning_system
        self.logger = logging.getLogger(__name__)
        
        # Simple configuration
        self.config = config or self._get_default_config()
        self.default_allocation_pct = float(self.config.get('default_allocation_pct', 10.0))
        self.book_id = self.config.get('book_id', 'social')
        
        # Initialize learning system components
        self.coefficient_reader = CoefficientReader(supabase_manager.client)
        self.bucket_vocab = BucketVocabulary()
        
        # Get trading config section
        trading_config = self.config.get('trading', {})
        
        # No need for dollar amounts - we work with percentages only
        self.min_curator_score = trading_config.get('min_curator_score', 0.1)
        self.max_exposure_pct = trading_config.get('max_exposure_pct', 100.0)  # 100% max exposure for lowcap portfolio
        self.max_positions = trading_config.get('max_positions', 69)  # Maximum number of active positions
        
        # Note: Token ignore list moved to Social Ingest for early filtering
        
        # Minimum volume requirements by chain
        self.min_volume_requirements = self.config.get('min_volume_requirements', {
            'solana': 100000,    # $100k on Solana
            'ethereum': 25000,   # $25k on Ethereum
            'base': 25000,       # $25k on Base
        })
        
        self.logger.info(f"Simplified Decision Maker Lowcap initialized for book: {self.book_id}")
    
    def _get_regime_context(self) -> Dict[str, Dict[str, Any]]:
        """
        Get bucket snapshots for regime_context (used for bucket rank/leader).
        """
        regime_context = {}
        
        bucket_snapshot = fetch_bucket_phase_snapshot(self.supabase_manager.client)
        regime_context["bucket_phases"] = bucket_snapshot.get("bucket_phases", {})
        regime_context["bucket_population"] = bucket_snapshot.get("bucket_population", {})
        regime_context["bucket_rank"] = bucket_snapshot.get("bucket_rank", [])

        return regime_context

    def _get_regime_driver_states(self, driver: Optional[str]) -> Dict[str, str]:
        """Fetch S-states (S0-S4) for a regime driver across macro/meso/micro."""
        default_state = {"macro": "S4", "meso": "S4", "micro": "S4"}
        if not driver:
            return default_state
        tf_mapping = {"macro": "1d", "meso": "1h", "micro": "1m"}
        try:
            states: Dict[str, str] = {}
            for horizon, pos_tf in tf_mapping.items():
                result = (
                    self.supabase_manager.client.table("lowcap_positions")
                    .select("state, features")
                    .eq("status", "regime_driver")
                    .eq("token_ticker", driver)
                    .eq("timeframe", pos_tf)
                    .order("updated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    row = result.data[0]
                    features = row.get("features") or {}
                    uptrend = features.get("uptrend_engine_v4") or {}
                    state = uptrend.get("state") or row.get("state", "S4")
                    states[horizon] = str(state)
                else:
                    states[horizon] = "S4"
            return states
        except Exception as e:
            self.logger.warning(f"Error fetching regime states for driver {driver}: {e}")
            return default_state

    def _get_regime_states_bundle(self, token_bucket: Optional[str]) -> Dict[str, str]:
        """Build full regime bundle (btc/alt/bucket/btcd/usdtd × macro/meso/micro)."""
        drivers = {
            "btc": "BTC",
            "alt": "ALT",
            "btcd": "BTC.d",
            "usdtd": "USDT.d",
        }
        bucket_driver = None
        if token_bucket:
            bucket_driver = BUCKET_DRIVERS.get(token_bucket, token_bucket)
        drivers["bucket"] = bucket_driver

        bundle: Dict[str, str] = {}
        for prefix, driver in drivers.items():
            states = self._get_regime_driver_states(driver)
            bundle[f"{prefix}_macro"] = states.get("macro", "S4")
            bundle[f"{prefix}_meso"] = states.get("meso", "S4")
            bundle[f"{prefix}_micro"] = states.get("micro", "S4")
        return bundle
    
    def _augment_dm_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        regime_context = self._get_regime_context()
        # Legacy phase fields removed; regime states handled elsewhere
        
        if not context.get('bucket') and context.get('mcap_bucket'):
            context['bucket'] = context['mcap_bucket']
        
        bucket_rank = regime_context.get('bucket_rank', [])
        if bucket_rank:
            context['bucket_leader'] = bucket_rank[0]
            bucket = context.get('bucket') or context.get('mcap_bucket')
            if bucket and bucket in bucket_rank:
                context['bucket_rank_position'] = bucket_rank.index(bucket) + 1
        return context
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'book_id': 'social',
            # No dollar amounts needed - percentage-based only
            'min_curator_score': 0.1,  # Minimum curator score to approve
            'max_exposure_pct': 100.0,  # 100% max exposure for lowcap portfolio
            'max_positions': 69,  # Maximum number of active positions
            'chain_multipliers': {
                'ethereum': 2.0,  # 2x boost for Ethereum
                'base': 2.0,      # 2x boost for Base
                'solana': 1.0,    # No boost for Solana
                'bsc': 1.0        # No boost for BSC
            }
        }
    
    async def make_decision(self, social_signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make simple allocation decision based on 4-step process with a visible checklist
        """
        try:
            curator_id = social_signal['signal_pack']['curator']['id']
            token_data = social_signal['signal_pack']['token']
            venue_data = social_signal['signal_pack']['venue']
            
            token_ticker = token_data.get('ticker', 'UNKNOWN').upper()
            chain = token_data.get('chain', '').lower()
            volume_24h = venue_data.get('vol24h_usd', 0)
            min_volume = self.min_volume_requirements.get(chain, 0)
            supported_chains = ['solana', 'ethereum', 'base', 'bsc']

            self.logger.info(f"Making decision for {curator_id} -> {token_ticker}")

            # Evaluate all criteria
            criteria = []

            # Note: Token ignore filtering now handled in Social Ingest (early filtering)

            # 1) Supported chain
            chain_pass = chain in supported_chains
            criteria.append({
                'name': 'supported_chain',
                'passed': chain_pass,
                'detail': f"Chain {chain} not supported; allowed: {supported_chains}" if not chain_pass else f"Chain {chain} supported"
            })

            # Volume check removed - handled in social ingest

            # 2) Not already holding token (informational only - we log intent but don't duplicate positions)
            already_holding = await self._already_has_token(token_data.get('contract', ''), token_data.get('chain', ''))
            if already_holding:
                self.logger.info(f"Already holding {token_ticker} - logging intent but not creating duplicate position")
                # Still approve to log the intent, but won't create duplicate positions

            # 3) Curator score >= min
            curator_score = await self._get_curator_score(curator_id)
            score_pass = curator_score >= self.min_curator_score
            criteria.append({
                'name': 'curator_score',
                'passed': score_pass,
                'detail': f"Curator {curator_score:.2f} < {self.min_curator_score}" if not score_pass else f"Curator {curator_score:.2f} >= {self.min_curator_score}"
            })

            # Intent analysis removed - no longer blocks approval
            intent_analysis = social_signal.get('signal_pack', {}).get('intent_analysis')
            intent_type = 'unknown'
            if intent_analysis:
                intent_data = intent_analysis.get('intent_analysis', {})
                intent_type = intent_data.get('intent_type', 'unknown')
            # Log intent for telemetry but don't block
            if intent_analysis:
                self.logger.debug(f"Intent type: {intent_type} (informational only)")

            # Portfolio capacity removed - positions go to waitlist if capacity is full

            failed = [c for c in criteria if not c['passed']]

            # Checklist summary at INFO; full details at DEBUG
            passed_count = sum(1 for c in criteria if c['passed'])
            failed = [c for c in criteria if not c['passed']]
            if failed:
                failed_names = ", ".join(c['name'] for c in failed)
                print(f"decision | Checklist: {passed_count}/{len(criteria)} passed (failed: {failed_names})")
                # Detailed reasons at DEBUG
                for c in criteria:
                    self.logger.debug(f"check {c['name']}: {'pass' if c['passed'] else 'fail'} - {c['detail']}")
            else:
                print(f"decision | Checklist: {passed_count}/{len(criteria)} passed (chain: {chain}, curator {curator_score:.2f}, intent: {intent_type})")
                for c in criteria:
                    self.logger.debug(f"check {c['name']}: pass - {c['detail']}")

            if failed:
                reason_text = "; ".join(c['detail'] for c in failed)
                print(f"decision | REJECTED {token_ticker} ({chain}) reasons: {reason_text}")
                return await self._create_rejection_decision(social_signal, reason_text)

            # All checks passed → approve
            # Extract intent analysis from signal pack
            intent_analysis = social_signal.get('signal_pack', {}).get('intent_analysis')
            # DM now uses a single base allocation percentage (configurable)
            allocation_pct = self.default_allocation_pct
            decision = await self._create_approval_decision(social_signal, allocation_pct, curator_score, intent_analysis)
            
            # Enhanced logging with intent information
            if intent_analysis:
                intent_data = intent_analysis.get('intent_analysis', {})
                intent_type = intent_data.get('intent_type', 'unknown')
                multiplier = intent_data.get('allocation_multiplier', 1.0)
                reasoning = intent_data.get('reasoning', '')
                # Show reasoning if available (LLM review of the tweet/message)
                if reasoning:
                    # Truncate reasoning if too long for console output
                    reasoning_short = reasoning[:60] + '...' if len(reasoning) > 60 else reasoning
                    print(f"decision | APPROVED {token_ticker} alloc {allocation_pct}% (curator {curator_score:.2f}, intent: {intent_type}, {multiplier}x) | {reasoning_short}")
                else:
                    print(f"decision | APPROVED {token_ticker} alloc {allocation_pct}% (curator {curator_score:.2f}, intent: {intent_type}, {multiplier}x)")
            else:
                print(f"decision | APPROVED {token_ticker} alloc {allocation_pct}% (curator {curator_score:.2f})")
            return decision
            
        except Exception as e:
            print(f"❌ Decision Maker Error: {e}")
            self.logger.error(f"Failed to make decision: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _already_has_token(self, token_contract: str, token_chain: str) -> bool:
        """
        Step 1: Check if we already have this token
        
        Args:
            token_contract: Token contract address
            token_chain: Token chain (solana, ethereum, etc.)
            
        Returns:
            True if we already have this token
        """
        try:
            # Query active positions for this token using execute_query
            query = """
                SELECT * FROM lowcap_positions 
                WHERE token_contract = %s AND token_chain = %s AND status = 'active'
            """
            result = await self.supabase_manager.execute_query(query, [token_contract, token_chain])
            
            has_position = len(result) > 0
            
            if has_position:
                self.logger.info(f"Already holding {token_contract} on {token_chain}")
            
            return has_position
            
        except Exception as e:
            self.logger.error(f"Error checking existing token: {e}")
            return False  # Assume we don't have it if we can't check
    
    async def _get_curator_score(self, curator_id: str) -> float:
        """
        Step 2: Get curator performance score
        
        Args:
            curator_id: Curator identifier
            
        Returns:
            Curator performance score (0.0 to 1.0)
        """
        try:
            # Get curator performance from database using execute_query
            query = """
                SELECT final_weight, win_rate, total_signals 
                FROM curators 
                WHERE curator_id = %s
            """
            result = await self.supabase_manager.execute_query(query, [curator_id])
            
            if not result:
                self.logger.warning(f"Curator {curator_id} not found in database")
                return 0.5  # Default score for unknown curators
            
            curator = result[0]
            
            # Handle nested result structure from execute_query
            if 'result' in curator:
                curator = curator['result']
            
            # Use final_weight as primary score, fallback to win_rate
            score = curator.get('final_weight', curator.get('win_rate', 0.5))
            
            # Ensure score is between 0 and 1
            score = max(0.0, min(1.0, score))
            
            self.logger.info(f"Curator {curator_id} score: {score:.2f}")
            return score
            
        except Exception as e:
            self.logger.error(f"Error getting curator score for {curator_id}: {e}")
            return 0.5  # Default score on error
    
    async def _has_capital_for_allocation(self) -> bool:
        """
        Step 3: Check if we have capital for new allocation
        
        Returns:
            True if we have capital available
        """
        try:
            # Get current portfolio exposure
            # Use execute_query instead of rpc
            query = "SELECT * FROM lowcap_positions WHERE book_id = %s AND status = 'active'"
            result = await self.supabase_manager.execute_query(query, [self.book_id])
            
            if not result:
                self.logger.warning("Could not get portfolio summary")
                return True  # Assume we have capital if we can't check
            
            # For now, just check if we have fewer than max_positions
            current_positions = len(result)
            has_capital = current_positions < self.max_positions
            
            if not has_capital:
                self.logger.info(f"Portfolio at max positions: {current_positions} >= {self.max_positions}")
            
            return has_capital
            
        except Exception as e:
            self.logger.error(f"Error checking portfolio capacity: {e}")
            return True  # Assume we have capital if we can't check
    
    # Legacy allocation-learning helpers removed; DM now uses a single configurable base percentage.
    
    def _build_entry_context_for_learning(
        self,
        curator_score: float,
        intent_analysis: Dict[str, Any] = None,
        token_data: Dict[str, Any] = None,
        venue_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Build entry context with buckets for learning system.
        
        Args:
            curator_score: Curator performance score
            intent_analysis: Intent analysis (optional)
            token_data: Token data (optional)
            venue_data: Venue data (optional) - used for volume information
            
        Returns:
            Entry context dictionary with buckets
        """
        entry_context = {}
        
        # Get curator ID (we'll need to pass this in, but for now use curator_score as proxy)
        # Note: We'll need to get actual curator ID from the signal
        # For now, we'll use a placeholder - this should be passed from make_decision()
        entry_context['curator'] = None  # Will be set by caller
        
        # Chain
        if token_data:
            chain = token_data.get('chain', '').lower()
            entry_context['chain'] = chain
            
            # Market cap bucket
            market_cap = token_data.get('market_cap')
            if market_cap and market_cap > 0:
                entry_context['mcap_bucket'] = self.bucket_vocab.get_mcap_bucket(market_cap)
                entry_context['mcap_at_entry'] = market_cap
            
            # Volume bucket (check token_data and venue_data)
            volume_24h = None
            if venue_data:
                volume_24h = venue_data.get('vol24h_usd') or venue_data.get('volume_24h')
            if not volume_24h and token_data:
                volume_24h = token_data.get('vol24h_usd') or token_data.get('volume_24h')
            if volume_24h and volume_24h > 0:
                entry_context['vol_bucket'] = self.bucket_vocab.get_vol_bucket(volume_24h)
                entry_context['vol_at_entry'] = volume_24h
            
            # Age bucket
            age_days = token_data.get('age_days')
            if age_days is not None:
                entry_context['age_bucket'] = self.bucket_vocab.get_age_bucket(age_days)
                entry_context['age_at_entry'] = age_days
            
            # Mcap/Vol ratio bucket
            if market_cap and volume_24h and volume_24h > 0:
                entry_context['mcap_vol_ratio_bucket'] = self.bucket_vocab.get_mcap_vol_ratio_bucket(
                    market_cap, volume_24h
                )
            
            # Mapping confidence
            mapping_confidence = token_data.get('mapping_confidence', 'high')
            entry_context['mapping_confidence'] = mapping_confidence
        
        # Intent
        if intent_analysis:
            intent_data = intent_analysis.get('intent_analysis', {})
            intent_type = intent_data.get('intent_type', 'unknown')
            entry_context['intent'] = intent_type
        else:
            entry_context['intent'] = 'unknown'
        
        return entry_context
    
    
    async def _create_approval_decision(self, social_signal: Dict[str, Any], allocation_pct: float, curator_score: float, intent_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create approval decision strand"""
        token_data = social_signal['signal_pack']['token']
        venue_data = social_signal['signal_pack']['venue']
        
        # Get regime context (macro/meso/micro phases)
        regime_context = self._get_regime_context()
        
        decision = {
            "id": str(uuid.uuid4()),
            "module": "decision_maker_lowcap",
            "kind": "decision_lowcap",
            "symbol": social_signal.get('symbol'),
            "session_bucket": social_signal.get('session_bucket'),
            "parent_id": social_signal.get('id'),
            "signal_pack": social_signal.get('signal_pack'),
            "module_intelligence": social_signal.get('module_intelligence'),
            "regime_context": regime_context,  # Macro/meso/micro phases
            "content": {
                "source_kind": "social_lowcap",
                "source_strand_id": social_signal.get('id'),
                "curator_id": social_signal['signal_pack']['curator']['id'],
                "token": token_data,
                "venue": venue_data,
                "action": "approve",
                "allocation_pct": allocation_pct,  # DM only provides percentage - PM calculates USD at execution time
                "curator_confidence": curator_score,
                "reasoning": self._build_approval_reasoning(curator_score, allocation_pct, intent_analysis)
            },
            "tags": ["decision", "social_lowcap", "approved", "simple"],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Create strand in database
        try:
            created_decision = await self.supabase_manager.create_strand(decision)
            self.logger.info(f"✅ APPROVED: {social_signal['signal_pack']['curator']['id']} -> {allocation_pct}%")
            
            # v4: Create 4 positions per token (one per timeframe: 1m, 15m, 1h, 4h)
            await self._create_positions_for_token(created_decision, allocation_pct, token_data, curator_score, intent_analysis, decision_id=created_decision.get('id'))
            
            # Trigger learning system to process the decision strand
            # Trigger learning system callback if available (silent unless error)
            self.logger.debug("Decision Maker: Checking if learning system is available...")
            
            # Check if learning system is available and has the process_strand_event method
            if (hasattr(self, 'learning_system') and 
                self.learning_system and 
                hasattr(self.learning_system, 'process_strand_event') and
                callable(getattr(self.learning_system, 'process_strand_event', None))):
                self.logger.debug(f"Triggering learning system for decision strand: {created_decision.get('id')}")
                try:
                    # Use await for sequential processing - wait for completion
                    result = await self.learning_system.process_strand_event(created_decision)
                    self.logger.debug(f"Learning system completed for strand {created_decision.get('id')}")
                except Exception as e:
                    self.logger.error(f"❌ Error calling learning system: {e}", exc_info=True)
            else:
                self.logger.debug(f"No learning system available for decision strand callback")
            
            return created_decision
        except Exception as e:
            self.logger.error(f"Failed to create approval decision: {e}")
            return None
    
    def _build_approval_reasoning(self, curator_score: float, allocation_pct: float, intent_analysis: Dict[str, Any] = None) -> str:
        """Build detailed reasoning for approval decision including intent analysis"""
        try:
            base_reasoning = f"Approved: Curator score {curator_score:.2f}, allocating {allocation_pct}%"
            
            if intent_analysis:
                intent_data = intent_analysis.get('intent_analysis', {})
                intent_type = intent_data.get('intent_type', 'unknown')
                multiplier = intent_data.get('allocation_multiplier', 1.0)
                
                if multiplier != 1.0:
                    base_reasoning += f" (Intent: {intent_type}, {multiplier}x multiplier applied)"
                else:
                    base_reasoning += f" (Intent: {intent_type})"
            
            return base_reasoning
            
        except Exception as e:
            self.logger.error(f"Error building approval reasoning: {e}")
            return f"Approved: Curator score {curator_score:.2f}, allocating {allocation_pct}%"
    
    async def _create_rejection_decision(self, social_signal: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Create rejection decision strand"""
        # Get regime context (macro/meso/micro phases)
        regime_context = self._get_regime_context()
        
        decision = {
            "id": str(uuid.uuid4()),
            "module": "decision_maker_lowcap",
            "kind": "decision_lowcap",
            "symbol": social_signal.get('symbol'),
            "session_bucket": social_signal.get('session_bucket'),
            "parent_id": social_signal.get('id'),
            "signal_pack": social_signal.get('signal_pack'),
            "module_intelligence": social_signal.get('module_intelligence'),
            "regime_context": regime_context,  # Macro/meso/micro phases
            "content": {
                "source_kind": "social_lowcap",
                "source_strand_id": social_signal.get('id'),
                "curator_id": social_signal['signal_pack']['curator']['id'],
                "token": social_signal['signal_pack']['token'],
                "venue": social_signal['signal_pack']['venue'],
                "action": "reject",
                "allocation_pct": 0,
                "curator_confidence": 0,
                "reasoning": reason
            },
            "tags": ["decision", "social_lowcap", "rejected", "simple"],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Create strand in database
        try:
            created_decision = await self.supabase_manager.create_strand(decision)
            self.logger.info(f"❌ REJECTED: {social_signal['signal_pack']['curator']['id']} -> {reason}")
            return created_decision
        except Exception as e:
            self.logger.error(f"Failed to create rejection decision: {e}")
            return None
    
    async def _check_bars_count(self, token_contract: str, chain: str, timeframe: str) -> int:
        """
        Check how many OHLC bars are available for a token/timeframe
        
        Args:
            token_contract: Token contract address
            chain: Chain (solana, ethereum, base, bsc)
            timeframe: Timeframe (1m, 15m, 1h, 4h)
            
        Returns:
            Number of bars available (0 if none)
        """
        try:
            result = self.supabase_manager.client.table('lowcap_price_data_ohlc').select(
                'timestamp', count='exact'
            ).eq('token_contract', token_contract).eq('chain', chain).eq('timeframe', timeframe).execute()
            
            bars_count = result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
            return bars_count
            
        except Exception as e:
            self.logger.warning(f"Error checking bars_count for {token_contract} {timeframe}: {e}")
            return 0
    
    async def _create_positions_for_token(
        self, 
        decision: Dict[str, Any], 
        allocation_pct: float,
        token_data: Dict[str, Any],
        curator_score: float,
        intent_analysis: Optional[Dict[str, Any]] = None,
        decision_id: Optional[str] = None
    ) -> bool:
        """
        Create 4 positions per token (one per timeframe: 1m, 15m, 1h, 4h)
        If already holding, skip position creation but still log intent via decision strand.
        
        Args:
            decision: Approved decision strand
            allocation_pct: Total allocation percentage
            token_data: Token data from signal
            curator_score: Curator performance score
            intent_analysis: Intent analysis (optional)
            
        Returns:
            True if all positions created successfully (or skipped due to already holding)
        """
        try:
            token_contract = token_data.get('contract', '')
            token_chain = token_data.get('chain', '').lower()
            token_ticker = token_data.get('ticker', 'UNKNOWN')
            token_name = token_data.get('name', token_ticker)
            
            # Check if already holding - if so, skip position creation but decision strand already logged intent
            already_holding = await self._already_has_token(token_contract, token_chain)
            if already_holding:
                self.logger.info(f"Skipping position creation for {token_ticker} - already holding (intent logged via decision strand)")
                return True  # Return success since intent was logged
            
            # Note: We no longer calculate fixed USD amounts here
            # PM will calculate USD amounts at execution time based on current portfolio size
            
            # Get learned timeframe weights (Phase 3)
            try:
                timeframe_weights = self.coefficient_reader.get_timeframe_weights(module='dm')
                normalized_weights = self.coefficient_reader.normalize_timeframe_weights(timeframe_weights)
                
                # Check if we have actual learned data (not just default 1.0 weights)
                # If all weights are 1.0, it means no learned data exists, so use defaults
                has_learned_data = any(w != 1.0 for w in timeframe_weights.values())
                
                # Use learned weights if available and we have actual learned data, otherwise fallback to defaults
                if normalized_weights and all(w > 0 for w in normalized_weights.values()) and has_learned_data:
                    timeframe_splits = normalized_weights
                    self.logger.info(f"Using learned timeframe weights: {timeframe_splits}")
                else:
                    # Fallback to default splits
                    timeframe_splits = {
                        '1m': 0.05,   # 5%
                        '15m': 0.125, # 12.5%
                        '1h': 0.70,   # 70%
                        '4h': 0.125   # 12.5%
                    }
                    self.logger.info(f"Using default timeframe splits: {timeframe_splits}")
            except Exception as e:
                self.logger.warning(f"Error getting learned timeframe weights, using defaults: {e}")
                # Fallback to default splits
                timeframe_splits = {
                    '1m': 0.05,   # 5%
                    '15m': 0.125, # 12.5%
                    '1h': 0.70,   # 70%
                    '4h': 0.125   # 12.5%
                }
            
            # Build entry_context for learning system (with buckets)
            # Note: venue_data not available here, volume will be from token_data if available
            entry_context = self._build_entry_context_for_learning(
                curator_score, intent_analysis, token_data, venue_data=None
            )
            # Add curator ID and additional metadata
            entry_context['curator'] = decision['content'].get('curator_id')
            entry_context['curator_id'] = decision['content'].get('curator_id')
            entry_context['curator_score'] = curator_score
            entry_context['token_contract'] = token_contract
            entry_context['token_ticker'] = token_ticker
            entry_context['allocation_pct'] = allocation_pct
            entry_context['timeframe_splits'] = timeframe_splits  # Store splits per timeframe
            entry_context['created_at'] = datetime.now(timezone.utc).isoformat()
            # Add regime state bundle at entry time
            token_bucket = entry_context.get('mcap_bucket')
            regime_bundle = self._get_regime_states_bundle(token_bucket)
            entry_context['regime_states_entry'] = regime_bundle
            
            # Create alloc_policy JSONB (only percentages, no fixed USD)
            alloc_policy = {
                'timeframe_splits': timeframe_splits,
                'total_allocation_pct': allocation_pct,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            positions_created = []
            timeframes = ['1m', '15m', '1h', '4h']
            
            for timeframe in timeframes:
                # Get timeframe-specific allocation percentage
                timeframe_pct = timeframe_splits[timeframe]
                
                # Check bars_count to determine initial status
                bars_count = await self._check_bars_count(token_contract, token_chain, timeframe)
                initial_status = 'watchlist' if bars_count >= 333 else 'dormant'  # Minimum 333 bars
                
                # Create position (no fixed USD amounts - PM will calculate at execution time)
                position = {
                    'token_chain': token_chain,
                    'token_contract': token_contract,
                    'token_ticker': token_ticker,
                    'timeframe': timeframe,
                    'status': initial_status,
                    'bars_count': bars_count,
                    'bars_threshold': 333,  # Updated to match new minimum
                    'alloc_policy': alloc_policy,
                    'total_allocation_pct': allocation_pct * timeframe_pct,  # Store timeframe-specific allocation %
                    'total_allocation_usd': 0.0,  # PM will update this on execution
                    'book_id': self.book_id,
                    'entry_context': entry_context,
                    'curator_sources': [{
                        'curator_id': decision['content'].get('curator_id'),
                        'confidence': curator_score,
                        'is_primary': True,
                        'signal_id': decision['content'].get('source_strand_id'),
                        'added_at': datetime.now(timezone.utc).isoformat()
                    }],
                    'source_tweet_url': token_data.get('source_tweet_url'),
                    'features': {},
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Check if position already exists before inserting
                existing = (
                    self.supabase_manager.client.table('lowcap_positions')
                    .select('id,status,curator_sources')
                    .eq('token_contract', token_contract)
                    .eq('token_chain', token_chain)
                    .eq('timeframe', timeframe)
                    .limit(1)
                    .execute()
                )
                
                if existing.data:
                    # Position already exists - update curator_sources to append new curator
                    existing_position = existing.data[0]
                    existing_id = existing_position.get('id')
                    existing_status = existing_position.get('status', 'unknown')
                    
                    # Get existing curator_sources (JSONB array)
                    existing_sources = existing_position.get('curator_sources') or []
                    if not isinstance(existing_sources, list):
                        existing_sources = []
                    
                    # Check if this curator already in sources
                    curator_id = decision['content'].get('curator_id')
                    already_added = any(src.get('curator_id') == curator_id for src in existing_sources)
                    
                    if not already_added:
                        # Append new curator source
                        new_source = {
                            'curator_id': curator_id,
                            'confidence': curator_score,
                            'is_primary': False,  # First curator is primary
                            'signal_id': decision['content'].get('source_strand_id'),
                            'added_at': datetime.now(timezone.utc).isoformat()
                        }
                        existing_sources.append(new_source)
                        
                        # Update position with new curator_sources
                        try:
                            self.supabase_manager.client.table('lowcap_positions').update({
                                'curator_sources': existing_sources,
                                'updated_at': datetime.now(timezone.utc).isoformat()
                            }).eq('id', existing_id).execute()
                            self.logger.info(f"Updated curator_sources for {token_ticker}/{timeframe}: added {curator_id}")
                        except Exception as e:
                            self.logger.error(f"Error updating curator_sources for {token_ticker}/{timeframe}: {e}")
                    else:
                        self.logger.debug(f"Curator {curator_id} already in sources for {token_ticker}/{timeframe}")
                    
                    self.logger.debug(f"Position already exists for {token_ticker}/{timeframe} (status: {existing_status}) - curator_sources updated")
                else:
                    # Insert position
                    try:
                        result = self.supabase_manager.client.table('lowcap_positions').insert(position).execute()
                        if result.data:
                            positions_created.append(timeframe)
                            self.logger.info(f"Created {timeframe} position for {token_ticker}: {allocation_pct * timeframe_pct:.2f}% (status: {initial_status}, bars: {bars_count})")
                        else:
                            self.logger.error(f"Failed to create {timeframe} position for {token_ticker}")
                    except Exception as e:
                        # Check if it's a duplicate key error (position was created between check and insert)
                        if 'duplicate key' in str(e).lower() or '23505' in str(e):
                            self.logger.debug(f"Position already exists for {token_ticker}/{timeframe} (race condition) - skipping")
                        else:
                            self.logger.error(f"Error creating {timeframe} position for {token_ticker}: {e}")
            
            # Backfill position_id to decision_lowcap strand after positions are created
            if len(positions_created) > 0:
                try:
                    # Get all position IDs that were just created
                    position_ids = []
                    for tf in positions_created:
                        # Query for the position we just created
                        pos_result = (
                            self.supabase_manager.client.table('lowcap_positions')
                            .select('id')
                            .eq('token_contract', token_contract)
                            .eq('token_chain', token_chain)
                            .eq('timeframe', tf)
                            .eq('book_id', self.book_id)
                            .order('created_at', desc=True)
                            .limit(1)
                            .execute()
                        )
                        if pos_result.data:
                            position_ids.append(pos_result.data[0]['id'])
                    
                    # Update decision_lowcap strand with position_id (use first position as primary)
                    decision_strand_id = decision_id or decision.get('id')
                    if position_ids and decision_strand_id:
                        # Store all position IDs in content, and primary position_id in top-level column
                        primary_position_id = position_ids[0]  # Use first position as primary
                        
                        # Get current content to merge with new position_ids
                        current_strand = (
                            self.supabase_manager.client.table('ad_strands')
                            .select('content')
                            .eq('id', decision_strand_id)
                            .limit(1)
                            .execute()
                        )
                        current_content = current_strand.data[0].get('content', {}) if current_strand.data else {}
                        
                        # Update decision strand with position_id
                        update_result = (
                            self.supabase_manager.client.table('ad_strands')
                            .update({
                                'position_id': primary_position_id,
                                'content': {
                                    **current_content,
                                    'position_ids': position_ids,  # Store all 4 position IDs
                                    'primary_position_id': primary_position_id
                                },
                                'updated_at': datetime.now(timezone.utc).isoformat()
                            })
                            .eq('id', decision_strand_id)
                            .execute()
                        )
                        
                        if update_result.data:
                            self.logger.info(f"✅ Backfilled position_id to decision_lowcap strand: {primary_position_id} (total positions: {len(position_ids)})")
                        else:
                            self.logger.warning(f"⚠️  Failed to backfill position_id to decision_lowcap strand")
                except Exception as e:
                    self.logger.error(f"Error backfilling position_id to decision_lowcap strand: {e}")
            
            # Trigger backfill for all 4 timeframes (synchronous, blocking)
            if len(positions_created) == 4:
                self.logger.info(f"✅ Created all 4 positions for {token_ticker} (total allocation: {allocation_pct}%)")
                
                # Trigger backfill sequentially (synchronous, blocking)
                try:
                    from intelligence.lowcap_portfolio_manager.jobs.geckoterminal_backfill import (
                        backfill_token_timeframe
                    )
                    
                    lookback_minutes = 20160  # 14 days
                    timeframes_to_backfill = ['1m', '15m', '1h', '4h']
                    
                    self.logger.info(f"🔄 Starting backfill for {token_ticker} (4 timeframes, sequential, synchronous)")
                    
                    # Run backfills sequentially and collect results
                    backfill_results = {}
                    for tf in timeframes_to_backfill:
                        try:
                            result = backfill_token_timeframe(
                                token_contract,
                                token_chain,
                                tf,
                                lookback_minutes
                            )
                            inserted = result.get('inserted_rows', 0)
                            error = result.get('error')
                            if error == 'token_not_found':
                                backfill_results[tf] = 'ERR'
                            else:
                                backfill_results[tf] = inserted
                        except Exception as e:
                            self.logger.error(f"Backfill {tf} failed for {token_ticker}: {e}")
                            backfill_results[tf] = 'ERR'
                    
                    # Single line summary: Backfill TOKEN: 1m/15m/1h/4h bars
                    bars_summary = f"{backfill_results.get('1m', 0)}/{backfill_results.get('15m', 0)}/{backfill_results.get('1h', 0)}/{backfill_results.get('4h', 0)}"
                    self.logger.info(f"Backfill {token_ticker}: {bars_summary}")
                    
                    # Trigger TA Tracker and Uptrend Engine immediately (don't wait for schedule)
                    try:
                        from intelligence.lowcap_portfolio_manager.jobs.ta_tracker import TATracker
                        from intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import UptrendEngineV4
                        
                        self.logger.info(f"🔄 Triggering TA Tracker and Uptrend Engine for {token_ticker}...")
                        
                        # Run TA Tracker for all timeframes that have enough bars
                        for tf in timeframes_to_backfill:
                            try:
                                ta_tracker = TATracker(timeframe=tf)
                                updated = ta_tracker.run()
                                if updated > 0:
                                    self.logger.info(f"✅ TA Tracker {tf} updated {updated} positions for {token_ticker}")
                            except Exception as e:
                                self.logger.warning(f"⚠️ TA Tracker {tf} failed for {token_ticker}: {e}")
                        
                        # Run Uptrend Engine for all timeframes
                        for tf in timeframes_to_backfill:
                            try:
                                uptrend_engine = UptrendEngineV4(timeframe=tf)
                                updated = uptrend_engine.run()
                                if updated > 0:
                                    self.logger.info(f"✅ Uptrend Engine {tf} updated {updated} positions for {token_ticker}")
                            except Exception as e:
                                self.logger.warning(f"⚠️ Uptrend Engine {tf} failed for {token_ticker}: {e}")
                        
                        self.logger.info(f"✅ TA Tracker and Uptrend Engine complete for {token_ticker}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to trigger TA Tracker/Uptrend Engine for {token_ticker}: {e}")
                        # Don't fail the whole process if this fails - scheduled jobs will catch up
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to trigger backfill for {token_ticker}: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                
                return True
            else:
                # Some positions already existed (duplicate key) - this is expected
                if len(positions_created) == 0:
                    self.logger.info(f"𐄷 All positions already exist for {token_ticker} (using existing positions)")
                else:
                    self.logger.info(f"ℹ️  Created {len(positions_created)}/4 new positions for {token_ticker} ({4 - len(positions_created)} already existed)")
                return True  # Still return True - existing positions are valid
                
        except Exception as e:
            self.logger.error(f"Error creating positions for token: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get simple portfolio summary"""
        try:
            # Use execute_query instead of rpc
            query = "SELECT * FROM lowcap_positions WHERE book_id = %s AND status = 'active'"
            result = await self.supabase_manager.execute_query(query, [self.book_id])
            
            if result.data:
                portfolio = result.data[0]
                return {
                    "book_id": self.book_id,
                    "book_nav": self.book_nav,
                    "total_positions": portfolio.get('total_positions', 0),
                    "active_positions": portfolio.get('active_positions', 0),
                    "current_exposure_pct": portfolio.get('current_exposure_pct', 0.0),
                    "total_pnl_usd": portfolio.get('total_pnl_usd', 0.0),
                    "avg_pnl_pct": portfolio.get('avg_pnl_pct', 0.0)
                }
            else:
                return {
                    "book_id": self.book_id,
                    "book_nav": self.book_nav,
                    "total_positions": 0,
                    "active_positions": 0,
                    "current_exposure_pct": 0.0,
                    "total_pnl_usd": 0.0,
                    "avg_pnl_pct": 0.0
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get portfolio summary: {e}")
            return {"error": str(e)}


# Example usage
if __name__ == "__main__":
    # Mock supabase manager for testing
    class MockSupabaseManager:
        def rpc(self, function_name, params):
            print(f"RPC call: {function_name} with params: {params}")
            return {'data': []}
        
        def table(self, table_name):
            class MockTable:
                def select(self, columns):
                    return self
                def eq(self, column, value):
                    return self
                def execute(self):
                    return {'data': []}
            return MockTable()
        
        def create_strand(self, strand):
            print(f"Created strand: {strand['kind']} - {strand['content']['action']}")
            return strand
    
    # Test the simplified decision maker
    dml = DecisionMakerLowcapSimple(MockSupabaseManager())
    
    # Mock social signal
    social_signal = {
        'id': 'test_strand_123',
        'content': {
            'curator_id': '0xdetweiler',
            'token': {
                'ticker': 'PEPE',
                'contract': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                'chain': 'solana'
            },
            'venue': {
                'dex': 'Raydium',
                'chain': 'solana',
                'liq_usd': 50000
            }
        }
    }
    
    # Make decision
    decision = dml.make_decision(social_signal)
    print(f"Decision result: {decision}")
