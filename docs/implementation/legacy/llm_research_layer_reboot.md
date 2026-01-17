LLM Research Layer – End‑State Blueprint
This document defines the complete architecture for the LLM research stack. The system follows a hierarchical investigation model:

Perceive → Think → Zoom → Think → Investigate → Verify

Where Level 1 provides zoomable perception, Overseer provides active intelligence, Level 6 provides data provisioning, Levels 2-5 provide targeted investigation, and Math provides verification.

v5 MVP Scope
This document describes the end-state blueprint. For v5 launch, implement a minimal viable slice:

v5 Must-Have
Level 1: Overview + one zoom flow (e.g., "zoom into anomalies")
Level 2: Basic semantic tagging + one investigation recipe (e.g., "investigate semantic differences in these tokens")
Level 3: Stubbed or manual (scope delta analysis can be done manually initially)
Level 4/5: Placeholders or single simple recipe each
Math Integration: Only for a couple of flows (e.g., validate Level 2 semantic proposals, validate Level 3 scope proposals)
v5 Nice-to-Have (Post-Launch)
Full Level 3 automation
Multiple Level 2 investigation types
Level 4 cross-domain synthesis
Level 5 comprehensive tuning copilot
Full math feedback loop integration
The architecture is designed to scale incrementally—start with the MVP and add capabilities as they prove valuable.

---

# Phase 1: System Observer (Foundation)

**Goal**: Build a unified "ask the system" interface that can answer any question about the trading system. This is the foundation that evolves into the full blueprint.

**Philosophy**: You are the Overseer initially. By asking questions manually, you discover what questions are valuable, what data is needed to answer them, and what patterns emerge. Recipes are learned, not designed upfront.

## Phase 1 Scope

### What We Build
1. **Data Access Layer** - Functions to pull from database and logs
2. **Log Aggregator** - Parse and search log files
3. **Context Assembler** - Bundle relevant data for a question
4. **System Observer** - Single `ask()` endpoint that answers questions
5. **CLI Interface** - `lotus ask "..."` command
6. **Proactive Digests** - Scheduled health checks and alerts
7. **Storage** - Save all interactions to `llm_learning`

### What We DON'T Build Yet
- Formal recipes (emerge from usage)
- Structured output schemas (add when patterns stabilize)
- L2-L5 investigators (add when needed)
- Math validation loop (add when we have hypotheses)
- Automated Overseer (you are the Overseer)

## Available Data Sources

### Database Tables (Supabase)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `lowcap_positions` | All positions (active, watchlist, closed) | status, state, total_pnl_usd, features, token_ticker, timeframe |
| `ad_strands` | All strands (social, decision, pm_action, position_closed) | kind, content, signal_pack, trade_id, position_id |
| `pattern_trade_events` | Fact table for trades | pattern_key, action_category, scope, rr, pnl_usd |
| `learning_lessons` | Mined lessons with edge stats | pattern_key, scope_subset, stats (edge_raw, avg_rr, n) |
| `pm_overrides` | Active runtime overrides | pattern_key, scope_subset, multiplier |
| `llm_learning` | LLM outputs (hypotheses, reports) | kind, level, content, status |
| `learning_configs` | System configuration | module_id, config_data |
| `lowcap_price_data_ohlc` | OHLC price data | token_contract, chain, timeframe, ohlc |

### Chart Generation (Visual)

| Source | Purpose | Output |
|--------|---------|--------|
| `generate_position_chart(id)` | Full chart with EMAs, S/R, state | PNG image path |
| `generate_ticker_chart(ticker, tf)` | Chart by ticker/timeframe | PNG image path |
| `generate_state_charts(S3)` | All positions in a state | List of PNG paths |

Uses existing `tools/live_charts/generate_live_chart.py` which includes:
- OHLC candlestick data
- EMAs (20, 30, 60, 144, 250, 333)
- S/R levels from geometry
- Current state marker (S0-S3)
- EMA verification (stored vs computed)

### Log Files (Local)

| Log File | Purpose | Format |
|----------|---------|--------|
| `pm_core.log` | PM Core Tick execution | Standard: `TIMESTAMP - pm_core - LEVEL - MESSAGE` |
| `uptrend_engine.log` | State transitions, errors | Standard |
| `trading_executions.log` | Structured trading logs | JSON: `{ts, level, event, correlation, action, state, error}` |
| `trading_errors.log` | Trading errors | Standard |
| `trading_positions.log` | Position changes | Standard |
| `decision_maker.log` | Decision maker | Standard |
| `learning_system.log` | Learning system | Standard |
| `pm_executor.log` | Trade execution | Standard |
| `rollup.log` | OHLC rollup | Standard |
| `regime_price_collector.log` | Regime data collection | Standard |
| `schedulers.log` | Scheduler jobs | Standard |
| `social_ingest.log` | Social ingestion | Standard |
| `system.log` | System level | Standard |
| `trader.log` | Trader service | Standard |

### Log Format Examples

**Standard log format:**
```
2025-12-21 12:12:04,328 - pm_core - INFO - PLAN ACTIONS: trim_flag → trim | Mappin/solana tf=1m | state=S2 qty=41991.125260
```

**Structured JSON log (trading_executions.log):**
```json
{
  "ts": "2025-12-21T12:00:00Z",
  "level": "INFO",
  "event": "ENTRY_SUCCESS",
  "correlation": {"position_id": "abc", "chain": "solana", "token": "PEPE"},
  "action": {"type": "entry", "tokens_bought": 1000, "price": 0.0001},
  "state": {"total_quantity_after": 1000, "pnl_pct": 0},
  "performance": {"duration_ms": 1500, "venue": "jupiter"}
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INTERFACE LAYER                               │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│  CLI            │  Scheduled      │  (Future: Web UI, Telegram)     │
│  lotus ask      │  Digests        │                                 │
└────────┬────────┴────────┬────────┴─────────────────────────────────┘
         │                 │
         └────────┬────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SYSTEM OBSERVER                                 │
│                                                                      │
│  ask(question: str) → Answer                                         │
│  • Infers what data sources are needed                               │
│  • Assembles context                                                 │
│  • Calls LLM with context + question                                 │
│  • Parses response                                                   │
│  • Stores interaction                                                │
│  • Suggests follow-up questions                                      │
└────────────────────────────────────┬────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CONTEXT ASSEMBLER                               │
│                                                                      │
│  assemble(sources: List[str]) → Dict[str, Any]                       │
│                                                                      │
│  Source Registry:                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │ Database Sources │  │ Log Sources      │  │ Computed Sources │   │
│  │ • positions      │  │ • logs_1h        │  │ • system_health  │   │
│  │ • closed_today   │  │ • logs_24h       │  │ • pnl_summary    │   │
│  │ • lessons        │  │ • errors         │  │ • edge_summary   │   │
│  │ • overrides      │  │ • warnings       │  │ • position_debug │   │
│  │ • recent_trades  │  │ • by_position    │  │                  │   │
│  │ • strands        │  │                  │  │                  │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘   │
└────────────────────────────────────┬────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA ACCESS LAYER                               │
│                                                                      │
│  Database Access (SupabaseManager):                                  │
│  • get_active_positions()                                            │
│  • get_closed_positions(since)                                       │
│  • get_position_by_id(id)                                            │
│  • get_recent_lessons()                                              │
│  • get_active_overrides()                                            │
│  • get_recent_strands(kind, limit)                                   │
│  • get_pattern_events(filters)                                       │
│                                                                      │
│  Log Access (LogAggregator):                                         │
│  • get_recent_logs(hours, log_names)                                 │
│  • get_errors(hours)                                                 │
│  • get_warnings(hours)                                               │
│  • search_logs(pattern, hours)                                       │
│  • get_logs_for_position(position_id)                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Log Aggregator (`src/intelligence/system_observer/log_aggregator.py`)

```python
class LogAggregator:
    """Aggregates and searches log files"""
    
    LOG_DIR = "logs"
    LOG_FILES = [
        "pm_core.log", "uptrend_engine.log", "trading_executions.log",
        "trading_errors.log", "decision_maker.log", "pm_executor.log",
        "rollup.log", "schedulers.log", "social_ingest.log", "system.log"
    ]
    
    def get_recent_logs(self, hours: int = 1, log_names: List[str] = None) -> str:
        """Get recent log entries from specified logs"""
        
    def get_errors(self, hours: int = 24) -> List[Dict]:
        """Extract ERROR level entries from all logs"""
        
    def get_warnings(self, hours: int = 24) -> List[Dict]:
        """Extract WARNING level entries from all logs"""
        
    def search_logs(self, pattern: str, hours: int = 24) -> List[Dict]:
        """Search logs for pattern (regex supported)"""
        
    def get_logs_for_position(self, position_id: str, hours: int = 24) -> str:
        """Get all log entries mentioning a position"""
        
    def parse_log_line(self, line: str) -> Optional[Dict]:
        """Parse standard log format: TIMESTAMP - LOGGER - LEVEL - MESSAGE"""
```

### 2. Data Access Layer (`src/intelligence/system_observer/data_access.py`)

```python
class DataAccess:
    """Database access functions for the observer"""
    
    def __init__(self, sb_client: Client):
        self.sb = sb_client
    
    # Position queries
    def get_active_positions(self) -> List[Dict]:
        """Get all positions with status='active'"""
        
    def get_watchlist_positions(self) -> List[Dict]:
        """Get all positions with status='watchlist'"""
        
    def get_closed_positions(self, since: datetime = None, limit: int = 20) -> List[Dict]:
        """Get recently closed positions"""
        
    def get_position_by_id(self, position_id: str) -> Optional[Dict]:
        """Get full position details"""
        
    def get_positions_in_profit(self) -> List[Dict]:
        """Get positions with positive PnL"""
        
    def get_positions_in_loss(self) -> List[Dict]:
        """Get positions with negative PnL"""
    
    # PnL queries
    def get_total_pnl(self, period: str = "24h") -> Dict:
        """Get aggregate PnL for period"""
        
    def get_pnl_by_position(self) -> List[Dict]:
        """Get PnL breakdown by position"""
    
    # Learning queries
    def get_recent_lessons(self, limit: int = 50) -> List[Dict]:
        """Get recent lessons with edge stats"""
        
    def get_lessons_for_pattern(self, pattern_key: str) -> List[Dict]:
        """Get lessons for specific pattern"""
        
    def get_active_overrides(self) -> List[Dict]:
        """Get all active pm_overrides"""
        
    def get_recent_overrides(self, hours: int = 24) -> List[Dict]:
        """Get recently created/updated overrides"""
    
    # Strand queries
    def get_recent_strands(self, kind: str = None, limit: int = 50) -> List[Dict]:
        """Get recent strands, optionally filtered by kind"""
        
    def get_strands_for_position(self, position_id: str) -> List[Dict]:
        """Get all strands for a position"""
    
    # Event queries
    def get_pattern_events(self, pattern_key: str = None, hours: int = 24) -> List[Dict]:
        """Get pattern_trade_events"""
    
    # System queries
    def get_system_health(self) -> Dict:
        """Run v5_learning_validator and return results"""
```

### 3. Context Assembler (`src/intelligence/system_observer/context_assembler.py`)

```python
class ContextAssembler:
    """Assembles context bundles for questions"""
    
    def __init__(self, data_access: DataAccess, log_aggregator: LogAggregator):
        self.data = data_access
        self.logs = log_aggregator
        
        # Source registry: name → (function, default_kwargs)
        self.sources = {
            # Database sources
            "active_positions": (self.data.get_active_positions, {}),
            "closed_today": (self.data.get_closed_positions, {"since": "today"}),
            "closed_24h": (self.data.get_closed_positions, {"hours": 24}),
            "positions_in_profit": (self.data.get_positions_in_profit, {}),
            "positions_in_loss": (self.data.get_positions_in_loss, {}),
            "total_pnl": (self.data.get_total_pnl, {}),
            "lessons": (self.data.get_recent_lessons, {}),
            "overrides": (self.data.get_active_overrides, {}),
            "recent_overrides": (self.data.get_recent_overrides, {}),
            "recent_strands": (self.data.get_recent_strands, {}),
            "system_health": (self.data.get_system_health, {}),
            
            # Log sources
            "logs_1h": (self.logs.get_recent_logs, {"hours": 1}),
            "logs_24h": (self.logs.get_recent_logs, {"hours": 24}),
            "errors": (self.logs.get_errors, {"hours": 24}),
            "warnings": (self.logs.get_warnings, {"hours": 24}),
        }
    
    def assemble(self, source_names: List[str], **kwargs) -> Dict[str, Any]:
        """Assemble context from requested sources"""
        context = {}
        for name in source_names:
            if name in self.sources:
                func, defaults = self.sources[name]
                merged_kwargs = {**defaults, **kwargs.get(name, {})}
                context[name] = func(**merged_kwargs)
        return context
    
    def infer_sources(self, question: str) -> List[str]:
        """Infer what sources are needed from the question"""
        q = question.lower()
        sources = []
        
        # Position questions
        if any(w in q for w in ["position", "holding", "trade"]):
            if "closed" in q:
                sources.append("closed_24h")
            elif "active" in q or "current" in q:
                sources.append("active_positions")
            elif "loss" in q:
                sources.append("positions_in_loss")
            elif "profit" in q:
                sources.append("positions_in_profit")
            else:
                sources.extend(["active_positions", "closed_24h"])
        
        # PnL questions
        if any(w in q for w in ["profit", "pnl", "money", "made", "lost"]):
            sources.append("total_pnl")
        
        # Error questions
        if any(w in q for w in ["error", "issue", "problem", "fail", "wrong"]):
            sources.extend(["errors", "warnings", "logs_1h"])
        
        # Learning questions
        if any(w in q for w in ["edge", "pattern", "lesson", "learn"]):
            sources.append("lessons")
        
        # Override questions
        if "override" in q:
            sources.extend(["overrides", "recent_overrides"])
        
        # Health questions
        if any(w in q for w in ["health", "status", "running", "system"]):
            sources.append("system_health")
        
        # Default: give some context
        if not sources:
            sources = ["active_positions", "errors", "system_health"]
        
        return list(set(sources))
```

### 4. System Observer (`src/intelligence/system_observer/observer.py`)

```python
class SystemObserver:
    """Main entry point for asking questions about the system"""
    
    SYSTEM_PROMPT = """You are a trading system assistant. You answer questions about a crypto trading system.

You have access to:
- Position data (active, closed, PnL)
- Trading logs (actions, errors, state transitions)
- Learning data (lessons, overrides, edge statistics)
- System health metrics

Guidelines:
- Be concise and specific
- Use actual numbers from the data provided
- If you can't answer fully, say what's missing
- Suggest relevant follow-up questions
- For errors, explain what they mean and if they're concerning
- For positions, include key metrics (PnL, state, quantity)
"""
    
    def __init__(self, sb_client: Client, llm_client: OpenRouterClient, log_dir: str = "logs"):
        self.data = DataAccess(sb_client)
        self.logs = LogAggregator(log_dir)
        self.context = ContextAssembler(self.data, self.logs)
        self.llm = llm_client
        self.sb = sb_client
    
    async def ask(self, question: str, sources: List[str] = None) -> Dict[str, Any]:
        """Ask a question about the system"""
        
        # 1. Determine what sources we need
        if sources is None:
            sources = self.context.infer_sources(question)
        
        # 2. Assemble context
        context = self.context.assemble(sources)
        
        # 3. Build prompt
        prompt = self._build_prompt(question, context)
        
        # 4. Call LLM
        response = await self.llm.generate_async(
            prompt=prompt,
            system_message=self.SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2000
        )
        
        # 5. Parse response
        result = {
            "question": question,
            "sources_used": sources,
            "answer": response,
            "context_summary": self._summarize_context(context),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # 6. Store interaction
        self._store_interaction(result)
        
        # 7. Add follow-up suggestions
        result["suggested_followups"] = self._extract_followups(response)
        
        return result
    
    async def position(self, position_id: str) -> Dict[str, Any]:
        """Deep dive into a specific position"""
        position = self.data.get_position_by_id(position_id)
        if not position:
            return {"error": f"Position {position_id} not found"}
        
        strands = self.data.get_strands_for_position(position_id)
        logs = self.logs.get_logs_for_position(position_id)
        
        context = {
            "position": position,
            "strands": strands,
            "relevant_logs": logs
        }
        
        question = f"Tell me about this position. What happened? What's its current state? Any issues?"
        return await self.ask(question, sources=None)  # We provide context directly
    
    async def health(self) -> Dict[str, Any]:
        """Quick health check"""
        return await self.ask(
            "What's the current system health? Any errors or issues I should know about?",
            sources=["errors", "warnings", "system_health", "logs_1h"]
        )
    
    async def summary(self) -> Dict[str, Any]:
        """Daily summary"""
        return await self.ask(
            "Give me a summary: How many positions? Any closed today? Total PnL? Any issues?",
            sources=["active_positions", "closed_today", "total_pnl", "errors"]
        )
    
    def _build_prompt(self, question: str, context: Dict) -> str:
        """Build the prompt with context"""
        context_str = json.dumps(context, indent=2, default=str)
        return f"""Question: {question}

Available Data:
```json
{context_str}
```

Please answer the question based on this data. Be specific and use actual numbers."""
    
    def _store_interaction(self, result: Dict):
        """Store interaction in llm_learning"""
        self.sb.table("llm_learning").insert({
            "kind": "observer_interaction",
            "level": 1,
            "module": "system_observer",
            "status": "active",
            "content": result,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
```

### 5. CLI Interface (`src/intelligence/system_observer/cli.py`)

```python
import click
import asyncio
from .observer import SystemObserver

@click.group()
def lotus():
    """Lotus Trading System CLI"""
    pass

@lotus.command()
@click.argument('question', nargs=-1)
def ask(question):
    """Ask a question about the system"""
    question_str = ' '.join(question)
    observer = get_observer()
    result = asyncio.run(observer.ask(question_str))
    print_result(result)

@lotus.command()
def health():
    """Quick health check"""
    observer = get_observer()
    result = asyncio.run(observer.health())
    print_result(result)

@lotus.command()
def summary():
    """Daily summary"""
    observer = get_observer()
    result = asyncio.run(observer.summary())
    print_result(result)

@lotus.command()
@click.argument('position_id')
def position(position_id):
    """Debug a specific position"""
    observer = get_observer()
    result = asyncio.run(observer.position(position_id))
    print_result(result)

@lotus.command()
def chat():
    """Interactive chat mode"""
    observer = get_observer()
    print("Lotus System Observer - Interactive Mode")
    print("Type 'quit' to exit\n")
    
    while True:
        question = input("You: ").strip()
        if question.lower() in ['quit', 'exit', 'q']:
            break
        if not question:
            continue
        
        result = asyncio.run(observer.ask(question))
        print(f"\nLotus: {result['answer']}\n")
        
        if result.get('suggested_followups'):
            print("Suggested follow-ups:")
            for f in result['suggested_followups'][:3]:
                print(f"  • {f}")
            print()
```

### 6. Proactive Digests (`src/intelligence/system_observer/digests.py`)

```python
class ProactiveDigest:
    """Scheduled digests and alerts - two-channel strategy"""
    
    def __init__(self, observer: SystemObserver, 
                 public_notifier=None,    # Existing public TG channel
                 private_notifier=None):  # Lotus Overseer private group
        self.observer = observer
        self.public = public_notifier
        self.private = private_notifier
    
    async def hourly_health_check(self):
        """Run every hour - check for errors (private channel only)"""
        errors = self.observer.logs.get_errors(hours=1)
        
        if errors:
            result = await self.observer.ask(
                f"We have {len(errors)} errors in the last hour. Summarize what's concerning.",
                sources=["errors", "logs_1h"]
            )
            
            # Only alert on private channel
            if self.private:
                await self.private.send_alert(f"⚠️ {len(errors)} errors in last hour\n\n{result['answer']}")
            
            return result
        
        return {"status": "healthy", "errors": 0}
    
    async def daily_digest_public(self):
        """Run daily - engaging summary for public channel"""
        result = await self.observer.ask(
            """Create a brief, engaging daily summary:
            - Total PnL today (with emoji)
            - Number of trades
            - Best/worst trade
            - One interesting insight
            Keep it short and engaging for a community audience.
            """,
            sources=["closed_24h", "total_pnl", "active_positions"]
        )
        
        if self.public:
            await self.public.send_digest(result['answer'])
        
        return result
    
    async def daily_digest_private(self):
        """Run daily - full technical summary for operator"""
        result = await self.observer.ask(
            """Full daily digest:
            1. Positions: active vs watchlist count
            2. Closed positions with PnL breakdown
            3. Errors and warnings summary
            4. System health status
            5. Learning updates (new lessons, override changes)
            6. Edge/pattern observations
            7. Anything unusual or concerning
            """,
            sources=[
                "active_positions", "closed_24h", "total_pnl",
                "errors", "warnings", "system_health", "lessons",
                "recent_overrides"
            ]
        )
        
        if self.private:
            await self.private.send_digest(f"📊 Daily Technical Digest\n\n{result['answer']}")
        
        return result
    
    async def position_alert(self, position_id: str, event: str):
        """Alert on specific position events (private channel)"""
        result = await self.observer.position(position_id)
        
        alert = f"🔔 Position Alert: {event}\n\n{result['answer']}"
        
        if self.private:
            await self.private.send_alert(alert)
        
        return result
```

### 7. Telegram Bot Handler (`src/intelligence/system_observer/telegram_bot.py`)

```python
class OverseerTelegramBot:
    """Bi-directional Telegram bot for Lotus Overseer private group"""
    
    ALLOWED_CHAT_IDS = ["lotus_overseer_chat_id"]  # Your private group
    
    def __init__(self, observer: SystemObserver, bot_token: str):
        self.observer = observer
        self.bot_token = bot_token
    
    async def handle_message(self, message: str, chat_id: str) -> str:
        """Handle incoming message - answer questions about the system"""
        
        # Security: only respond in allowed chats
        if chat_id not in self.ALLOWED_CHAT_IDS:
            return None
        
        # Check for specific commands
        if message.startswith("/health"):
            result = await self.observer.health()
            return result['answer']
        
        if message.startswith("/summary"):
            result = await self.observer.summary()
            return result['answer']
        
        if message.startswith("/position "):
            position_id = message.replace("/position ", "").strip()
            result = await self.observer.position(position_id)
            return result['answer']
        
        # Default: treat as a question
        result = await self.observer.ask(message)
        return result['answer']
    
    # Integration with python-telegram-bot or similar library
    # Actual implementation depends on your TG bot setup
```

## File Structure

```
src/intelligence/system_observer/
├── __init__.py
├── observer.py           # Main SystemObserver class
├── data_access.py        # Database access functions
├── log_aggregator.py     # Log file parsing and search
├── chart_generator.py    # Wrapper for live chart generation
├── context_assembler.py  # Context bundling + question understanding
├── cli.py               # CLI commands (lotus ask/health/summary/chat)
├── digests.py           # Proactive digests (public + private channels)
├── telegram_bot.py      # Bi-directional bot for Lotus Overseer group
└── prompts.py           # Prompt templates
```

### Integration Points

```
Existing Code → System Observer:
├── tools/live_charts/generate_live_chart.py  → chart_generator.py (wrapper)
├── src/utils/supabase_manager.py            → data_access.py (extend)
├── src/llm_integration/openrouter_client.py → observer.py (LLM calls)
├── src/communication/telegram_signal_notifier.py → digests.py (reuse for sending)
└── src/intelligence/lowcap_portfolio_manager/jobs/v5_learning_validator.py → system health
```

## Example Usage

```bash
# Ask any question
$ lotus ask "what positions got closed today?"

# Quick commands
$ lotus health
$ lotus summary
$ lotus position abc123

# Interactive mode
$ lotus chat
You: any errors in the last hour?
Lotus: No errors in the last hour. System is healthy.

You: what's our total PnL today?
Lotus: Total PnL today: +$1,234 across 3 closed positions...

You: tell me about position xyz
Lotus: Position xyz (PEPE/solana, 1m):
       Status: active, State: S2
       PnL: +15% (+$450)
       Last action: trim at 12:30...
```

## Evolution Path

### Phase 1 → Phase 2
As you use the observer, you'll notice patterns:
- "I ask about errors every morning" → becomes `lotus morning`
- "I always want position + strands + logs together" → becomes `position_debug` source
- "Edge questions always need lessons + overrides" → becomes `edge` source bundle

Extract these patterns into shortcuts and structured queries.

### Phase 2 → Phase 3 (Full Blueprint)
Once patterns stabilize:
- Common questions become **recipes** with structured outputs
- Add **zoom capability** (drill down from overview)
- Add **L2-5 investigators** for specific research
- Add **math validation** for hypotheses

### Phase 3 → Phase 4 (Code Improvement)
Ultimate goal: system proposes code changes based on findings.
- Research layer identifies: "Pattern X has 30% edge decay in high-vol regimes"
- Code layer proposes: "Add regime check to pattern X logic"
- Human reviews and approves
- System implements change

This requires:
- Codebase RAG (index code for LLM understanding)
- Diff generation (propose specific changes)
- Test execution (validate proposals)
- PR automation (create/merge PRs)

**Note**: This is a separate layer built on top of research. Focus on Phase 1-3 first.

---

## Notification Architecture

### Two-Channel Strategy

| Channel | Purpose | Content | Frequency |
|---------|---------|---------|-----------|
| **Public Channel** | Community engagement | Daily PnL, notable trades, interesting lessons | Daily digest |
| **Lotus Overseer** (private TG group) | Operator intelligence | Errors, technical debug, system health | Real-time + daily |

**Public Channel** (existing `telegram_signal_notifier.py`):
- Keep it engaging, not overwhelming
- Daily PnL summary with emoji
- Notable trades (big wins/losses)
- New lessons/edge insights (simplified)
- System status (positions count)
- NO error logs, NO technical details

**Lotus Overseer** (private group: https://t.me/+G63xTKwDBGI0MDE8):
- Full technical detail
- Error/warning alerts (immediate)
- System health checks
- Position-level debugging
- Edge decay alerts
- Override changes
- Interactive Q&A via bot

### Interactive Access

| Method | Use Case | Availability |
|--------|----------|--------------|
| **CLI** (`lotus chat`) | Deep debugging at computer | When at terminal |
| **Telegram Bot** (in Overseer group) | Ask questions on mobile | Async, anywhere |

The Telegram bot in Lotus Overseer is bi-directional:
```
You: what happened to position xyz?
Bot: Position xyz (PEPE/solana):
     Status: closed at 14:30
     PnL: -5% (-$120)
     Reason: emergency_exit triggered...
```

---

## Resolved Questions

1. **Log retention**: ~10MB rotation. Important data already goes to DB. Logs are for short-term error checking only.

2. **Notification channels**: Two-tier (public for community, private for operator)

3. **Bot token**: Same bot can serve both channels. A single Telegram bot can message multiple groups—just add the bot to both the public channel and Lotus Overseer private group. The existing `TelegramSignalNotifier` already supports this via the `channel_id` parameter. We'll extend it with a second notifier instance for the private group.

4. **Rate limiting**: TBD - consider caching recent answers, batching digest calls

5. **Context size**: TBD - truncate logs, summarize large datasets

---

## Build Plan (Implementation Order)

### What Makes This Hard?

The hardest parts are **question understanding** and **intelligent data collection**:

1. **Question → Data Mapping**: Given a natural language question, determining which data sources to query. The `infer_sources()` function is the critical path—it must understand intent from ambiguous language.

2. **Context Window Management**: Assembling enough context to answer well, without overwhelming the LLM. Logs can be huge; DB results can be verbose.

3. **Log Parsing**: Logs have multiple formats (standard, JSON structured). Parsing reliably, extracting timestamps, correlating entries—this is messy.

4. **Telegram Bot Integration**: Making the bot bi-directional (receive questions, send answers) with proper security.

### Build Order (Prioritized)

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1A: Core Infrastructure (Must Have First)                 │
│ Estimated: 1-2 days                                            │
├─────────────────────────────────────────────────────────────────┤
│ 1. log_aggregator.py        - Parse logs, search, filter       │
│ 2. data_access.py           - DB queries (extend SupabaseManager)│
│ 3. chart_generator.py       - Integrate live chart generator   │
│ 4. context_assembler.py     - Bundle sources, infer_sources()  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1B: Observer + CLI (Get It Working)                       │
│ Estimated: 1 day                                                │
├─────────────────────────────────────────────────────────────────┤
│ 5. observer.py              - ask(), health(), summary()       │
│ 6. cli.py                   - lotus ask/health/summary/chat    │
│ 7. prompts.py               - System prompt, format templates  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1C: Proactive + Notifications (Automated Value)           │
│ Estimated: 1 day                                                │
├─────────────────────────────────────────────────────────────────┤
│ 8. digests.py               - Hourly health, daily digest      │
│ 9. telegram_bot.py          - Bi-directional bot in Overseer   │
│ 10. Scheduler integration   - Hook into run_trade.py or cron   │
└─────────────────────────────────────────────────────────────────┘
```

### Detailed Implementation Tasks

#### 1. `log_aggregator.py` (Priority: HIGHEST)
The hardest piece. Must handle:
- **Standard log format**: `TIMESTAMP - LOGGER - LEVEL - MESSAGE`
- **JSON structured logs**: `trading_executions.log`
- **Rotated logs**: `.log.1`, `.log.2`, etc.
- **Time-based filtering**: "last hour", "last 24h"
- **Pattern search**: regex across all logs
- **Position correlation**: find all logs mentioning a position

```python
# Key methods to implement:
def parse_log_line(self, line: str) -> Optional[Dict]:
    """Parse standard format, extract timestamp/level/logger/message"""
    
def parse_json_log_line(self, line: str) -> Optional[Dict]:
    """Parse JSON structured logs"""
    
def get_recent_logs(self, hours: int, log_names: List[str] = None) -> List[Dict]:
    """Get logs from last N hours, optionally filtered by log file"""
    
def get_errors(self, hours: int = 24) -> List[Dict]:
    """Extract ERROR level entries"""
    
def search_logs(self, pattern: str, hours: int = 24) -> List[Dict]:
    """Regex search across logs"""
    
def get_logs_for_position(self, position_id: str) -> List[Dict]:
    """Find all log entries mentioning a position (id, ticker, contract)"""
```

#### 2. `data_access.py` (Priority: HIGH)
Extend `SupabaseManager` with research-focused queries:

```python
# Position queries
def get_active_positions(self) -> List[Dict]
def get_watchlist_positions(self) -> List[Dict]
def get_closed_positions(self, since: datetime, limit: int) -> List[Dict]
def get_position_by_id(self, position_id: int) -> Optional[Dict]
def get_positions_by_state(self, state: str) -> List[Dict]  # S0, S1, S2, S3

# PnL queries  
def get_total_pnl(self, hours: int = 24) -> Dict
def get_pnl_by_position(self, hours: int = 24) -> List[Dict]

# Learning queries
def get_recent_lessons(self, limit: int = 50) -> List[Dict]
def get_active_overrides(self) -> List[Dict]

# Strand queries
def get_recent_strands(self, kind: str = None, limit: int = 50) -> List[Dict]
def get_strands_for_position(self, position_id: int) -> List[Dict]

# System health (reuse v5_learning_validator logic)
def get_system_health(self) -> Dict
```

#### 3. `chart_generator.py` (Priority: HIGH)
Integrate with existing `tools/live_charts/generate_live_chart.py`:

```python
class ChartGenerator:
    """Wrapper around LiveChartGenerator for observer use"""
    
    def __init__(self):
        self.generator = LiveChartGenerator()
        self.output_dir = "tools/live_charts/output"
    
    def generate_position_chart(self, position_id: int) -> Optional[str]:
        """Generate chart for position, return file path"""
        paths = self.generator.generate_charts(position_id=position_id)
        return paths[0] if paths else None
    
    def generate_ticker_chart(self, ticker: str, timeframe: str = "1h") -> Optional[str]:
        """Generate chart by ticker"""
        paths = self.generator.generate_charts(ticker=ticker, timeframe=timeframe)
        return paths[0] if paths else None
    
    def generate_state_charts(self, state: str, timeframe: str = None) -> List[str]:
        """Generate charts for all positions in a given state"""
        return self.generator.generate_charts(
            all_positions=True, 
            stage=state, 
            timeframe=timeframe
        )
```

#### 4. `context_assembler.py` (Priority: HIGH)
The **critical piece** - question understanding:

```python
class ContextAssembler:
    def __init__(self, data_access, log_aggregator, chart_generator):
        self.data = data_access
        self.logs = log_aggregator  
        self.charts = chart_generator
        
        # Source registry
        self.sources = {
            # Database sources
            "active_positions": (self.data.get_active_positions, {}),
            "watchlist": (self.data.get_watchlist_positions, {}),
            "closed_today": (self.data.get_closed_positions, {"hours": 24}),
            "closed_week": (self.data.get_closed_positions, {"hours": 168}),
            "positions_in_profit": (self.data.get_positions_in_profit, {}),
            "positions_in_loss": (self.data.get_positions_in_loss, {}),
            "s3_positions": (self.data.get_positions_by_state, {"state": "S3"}),
            "total_pnl": (self.data.get_total_pnl, {}),
            "lessons": (self.data.get_recent_lessons, {}),
            "overrides": (self.data.get_active_overrides, {}),
            "recent_strands": (self.data.get_recent_strands, {}),
            "system_health": (self.data.get_system_health, {}),
            
            # Log sources
            "logs_1h": (self.logs.get_recent_logs, {"hours": 1}),
            "logs_24h": (self.logs.get_recent_logs, {"hours": 24}),
            "errors": (self.logs.get_errors, {"hours": 24}),
            "errors_1h": (self.logs.get_errors, {"hours": 1}),
            "warnings": (self.logs.get_warnings, {"hours": 24}),
        }
    
    def infer_sources(self, question: str) -> List[str]:
        """THE CRITICAL FUNCTION - understand what data the question needs"""
        q = question.lower()
        sources = []
        
        # Keywords → Sources mapping
        # Position-related
        if any(w in q for w in ["position", "holding", "trade", "ticker"]):
            if "closed" in q:
                sources.append("closed_today")
            elif "active" in q or "current" in q:
                sources.append("active_positions")
            elif "loss" in q or "losing" in q or "underwater" in q:
                sources.append("positions_in_loss")
            elif "profit" in q or "winning" in q:
                sources.append("positions_in_profit")
            elif "s3" in q or "trending" in q:
                sources.append("s3_positions")
            else:
                sources.extend(["active_positions", "closed_today"])
        
        # PnL/money
        if any(w in q for w in ["pnl", "profit", "money", "made", "lost", "performance"]):
            sources.append("total_pnl")
            if "position" in q:
                sources.append("active_positions")
        
        # Errors/issues
        if any(w in q for w in ["error", "issue", "problem", "fail", "wrong", "bug", "crash"]):
            sources.extend(["errors", "warnings", "logs_1h"])
        
        # Learning/edge
        if any(w in q for w in ["edge", "pattern", "lesson", "learn", "override"]):
            sources.extend(["lessons", "overrides"])
        
        # System health
        if any(w in q for w in ["health", "status", "running", "system", "ok", "good"]):
            sources.append("system_health")
        
        # Watchlist
        if "watchlist" in q or "watching" in q:
            sources.append("watchlist")
        
        # Default: give some context
        if not sources:
            sources = ["active_positions", "system_health", "errors"]
        
        return list(set(sources))
    
    def assemble(self, source_names: List[str], **kwargs) -> Dict[str, Any]:
        """Fetch and bundle all requested sources"""
        context = {}
        for name in source_names:
            if name in self.sources:
                func, defaults = self.sources[name]
                merged_kwargs = {**defaults, **kwargs.get(name, {})}
                try:
                    context[name] = func(**merged_kwargs)
                except Exception as e:
                    context[name] = {"error": str(e)}
        return context
```

#### 5-7. Observer + CLI + Prompts (See existing spec)

#### 8-10. Digests + Telegram Bot

**Telegram Integration Details:**

```python
# In digests.py
class ProactiveDigest:
    def __init__(self, observer: SystemObserver):
        self.observer = observer
        
        # Reuse existing TelegramSignalNotifier for both channels
        # Just different channel_id for each
        self.public_notifier = TelegramSignalNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            channel_id=os.getenv("TELEGRAM_PUBLIC_CHANNEL_ID"),  # @your_public_channel
            api_id=int(os.getenv("TELEGRAM_API_ID")),
            api_hash=os.getenv("TELEGRAM_API_HASH")
        )
        
        self.private_notifier = TelegramSignalNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),  # SAME BOT TOKEN
            channel_id=os.getenv("TELEGRAM_OVERSEER_CHANNEL_ID"),  # -100xxxxx (group ID)
            api_id=int(os.getenv("TELEGRAM_API_ID")),
            api_hash=os.getenv("TELEGRAM_API_HASH")
        )
```

**Bi-directional bot (telegram_bot.py):**
```python
# Uses python-telegram-bot library (not Telethon) for receiving messages
# Telethon is already used by TelegramSignalNotifier for sending

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

class OverseerTelegramBot:
    ALLOWED_CHAT_IDS = [int(os.getenv("TELEGRAM_OVERSEER_CHANNEL_ID"))]
    
    async def handle_message(self, update: Update, context):
        if update.effective_chat.id not in self.ALLOWED_CHAT_IDS:
            return  # Ignore messages from other chats
        
        question = update.message.text
        result = await self.observer.ask(question)
        await update.message.reply_text(result['answer'])
```

### Live Chart Integration

The observer can generate and send charts:

```python
# In observer.py
async def position(self, position_id: int) -> Dict[str, Any]:
    """Deep dive into a specific position WITH CHART"""
    position = self.data.get_position_by_id(position_id)
    if not position:
        return {"error": f"Position {position_id} not found"}
    
    # Generate chart
    chart_path = self.charts.generate_position_chart(position_id)
    
    strands = self.data.get_strands_for_position(position_id)
    logs = self.logs.get_logs_for_position(str(position_id))
    
    result = await self.ask(
        f"Tell me about this position. What happened? Current state? Any issues?",
        context_override={
            "position": position,
            "strands": strands[:20],  # Limit strands
            "relevant_logs": logs[:50]  # Limit logs
        }
    )
    
    result["chart_path"] = chart_path  # Include chart for TG to send as image
    return result

# In telegram_bot.py - send chart as image
async def send_position_analysis(self, chat_id: int, position_id: int):
    result = await self.observer.position(position_id)
    
    # Send chart image first
    if result.get("chart_path"):
        await self.bot.send_photo(
            chat_id=chat_id,
            photo=open(result["chart_path"], "rb"),
            caption=f"Chart for position {position_id}"
        )
    
    # Then send text analysis
    await self.bot.send_message(chat_id=chat_id, text=result["answer"])
```

### Environment Variables Needed

```bash
# Add to .env
TELEGRAM_BOT_TOKEN=xxx          # Existing bot token (same for both channels)
TELEGRAM_PUBLIC_CHANNEL_ID=@lotus_trader  # Public channel
TELEGRAM_OVERSEER_CHANNEL_ID=-100xxxxx    # Private Lotus Overseer group ID
TELEGRAM_API_ID=xxx             # Existing
TELEGRAM_API_HASH=xxx           # Existing

OPENROUTER_API_KEY=xxx          # For LLM calls
```

### Scheduling Options

**Option A: Integrate with run_trade.py**
Add digest calls to existing scheduler:
```python
# In run_trade.py or appropriate scheduler
async def run_hourly_health():
    digest = ProactiveDigest(get_observer())
    await digest.hourly_health_check()

async def run_daily_digest():
    digest = ProactiveDigest(get_observer())
    await digest.daily_digest_public()
    await digest.daily_digest_private()
```

**Option B: Separate cron process**
```bash
# crontab
0 * * * * cd /path/to/lotus && .venv/bin/python -c "from src.intelligence.system_observer.digests import hourly_health; asyncio.run(hourly_health())"
0 20 * * * cd /path/to/lotus && .venv/bin/python -c "from src.intelligence.system_observer.digests import daily_digest; asyncio.run(daily_digest())"
```

### Testing Plan

```bash
# 1. Test log aggregator
lotus ask "any errors in the last hour?"

# 2. Test position queries  
lotus ask "what positions are active?"
lotus ask "show me closed positions today"

# 3. Test position deep dive with chart
lotus position 123

# 4. Test health
lotus health

# 5. Test summary
lotus summary

# 6. Test interactive
lotus chat
> what's our total pnl?
> tell me about position xyz
> any issues with the uptrend engine?
```

---

0. Layer Hierarchy (Who does what?)
Overseer (active intelligence - asks questions, interprets, routes)
    ↓
Level 6 – Research Manager (data provisioner, recipe executor, validator)
    ↓
Level 1 – Performance Observer (zoomable perception layer)
    ↓
Levels 2-5 – Blind Researchers (targeted investigation tools)
    ↓
Math Layer (verification & execution)
Core Intelligence Flow
1. Overseer: "How are we doing?"
   ↓
2. Level 6 → Level 1 (general overview recipe)
   ↓
3. Level 1 → Returns structured performance map
   ↓
4. Overseer: Sees anomaly → "Zoom into this region"
   ↓
5. Level 6 → Level 1 (zoom-in recipe with filters)
   ↓
6. Level 1 → Returns zoomed slice
   ↓
7. Overseer: Understands shape → "Investigate semantic differences in these tokens"
   ↓
8. Level 6 → Prepares exact data bundles → Level 2
   ↓
9. Level 2 → Analyzes only provided bundle → Returns findings
   ↓
10. Level 6 → Validates → Overseer
   ↓
11. Overseer: Evaluates → May ask more questions or escalate
1. Overseer (Active Intelligence Layer)
Purpose
The Overseer is the active intelligence that asks questions, interprets results, and directs research attention. It is not a passive planner—it actively thinks, zooms, and routes investigations.

The 5 Core Questions (All Asked to Level 1)
The Overseer operates by asking Level 1 these fundamental questions:

Q1: "How are we doing overall?"
Asks Level 1 for general overview
Receives structured performance map:
Strong edge zones
Weak edge zones
Anomalies/inconsistencies
Edge trends (decay/emergence)
Areas to watch
This sparks all other questions
Q2: "Where are we strongest?"
Asks Level 1 to zoom into high-edge regions
Wants to understand:
Why strong zones are strong
What tokens/patterns are inside
Whether strength is stable
Whether there are hidden clusters
Based on answer, Overseer may ask Level 2/3/4 to investigate why success occurs
Q3: "Where are we weakest?"
Asks Level 1 to zoom into low-edge regions
Wants to understand:
What exactly is failing
Which tokens drag performance
Whether weak zones overlap with strong ones
Whether structural changes are needed
Based on answer, Overseer may ask Level 3/5 to investigate failures
Q4: "Where are we inconsistent or anomalous?"
Asks Level 1 to highlight anomalies
Wants to understand:
Where things look similar but behave differently
Where performance is mixed/unclear
Where there's instability
Where hidden structure might exist
Based on answer, Overseer may ask Level 2 (semantic) or Level 3 (structural) to investigate
Q5: "How is our edge changing over time?"
Asks Level 1 for edge history analysis
Wants to understand:
Which edges are decaying
Which edges are emerging
Decay rates and half-lives
Regime shifts
Based on answer, Overseer may ask Level 3 (structure) or Level 5 (timing) to investigate
Q6: "Where are we concentrated or under-exposed?"
Asks Level 1 for exposure/crowding analysis
Wants to understand:
Which scopes/patterns consume most capital
Whether those crowded zones still have meaningful edge
Where high-edge regions are under-allocated
Diversification pressure vs conviction zones
Based on answer, Overseer may ask Level 3 (structure) to rebalance scopes, or Level 2 (semantic) to explain why capital clusters exist
Questions Overseer Asks to Other Parts of the System
Based on Level 1's answers, the Overseer asks targeted questions to other parts of the system:

To Level 2 (Semantic Investigator):
"These tokens have identical scopes but different performance. Investigate semantic subclasses."
"What semantic factors explain this divergence?"
"Are there hidden semantic categories within this group?"
To Level 3 (Structure Investigator):
"This scope group has mixed performance. Should we split it by dimension X?"
"Are bucket boundaries optimal for this pattern?"
"Should semantic factors be integrated as scope dimensions?"
To Level 4 (Cross-Domain Investigator):
"Do these patterns share lever adjustments? Is there a meta-lesson?"
"Are there cross-domain patterns that explain this behavior?"
To Level 5 (Tuning Investigator):
"CF data shows missed RR. How can we improve timing for this pattern/scope?"
"What execution constraints are limiting R/R here?"
To Math Layer:
"Validate this scope proposal via SQL tests"
"Test whether this hypothesis holds statistically"
"Verify this edge claim with historical data"
Core Functions
Question Formation (To Level 1)

Asks Level 1 the 5 core questions (all perception questions)
Asks Level 1 follow-up zoom-in questions
Never asks vague questions—always specific
All questions to Level 1 are about "where" and "what" (perception)
Zoom-In Requests (To Level 1)

When Level 1 shows an anomaly, Overseer asks Level 1 to zoom:
"Zoom into this region with these filters"
"Break this down by semantic class"
"Split this scope group by bucket_volatility"
"Show token-level breakdown"
Overseer does NOT ask itself—it asks Level 1
Investigation Routing (To Levels 2-5 & Math)

After Level 1 provides answers, Overseer understands the shape
Routes targeted "why" and "how" questions to appropriate investigators:
Semantic/token differences → Level 2 ("Why do these tokens differ?")
Structural/scope differences → Level 3 ("How should we restructure?")
Cross-domain patterns → Level 4 ("What patterns span domains?")
Timing/counterfactual issues → Level 5 ("How can we improve R/R?")
Mathematical validation → Math layer ("Validate this claim")
Synthesis & Decision Making

Receives investigation results from Levels 2-5
Synthesizes findings into actionable insights
Decides what should be tested, changed, or monitored
Can request further investigation or escalate to math layer
Architecture Evolution

Monitors whether research outputs improve edge
Detects when new investigation types are needed
Can request Level 6 to create new recipes or summarizers
Overseer Context & Memory
The Overseer doesn't live in a vacuum every run. When answering "What should we investigate next?", it can leverage:

Recent Research History: Reads recent llm_learning entries (last N days) to see:

Which anomalies have already been investigated
Which hypotheses have pending validation
Which research directions have paid off
Which areas have been investigated with no payoff (de-prioritize)
Validation Feedback: Reviews math layer validation results to learn:

Which recipe types produce validated insights
Which investigation patterns are most successful
Which anomalies recur and need escalation
Research Summary Bundle: Level 6 supplies a recent_research_summary bundle that includes:

Recent investigation outcomes
Pending validation status
Historical success rates per recipe/level
Recurring anomaly patterns
This prevents Overseer from recursing on the same anomaly forever and helps it learn which research strategies work.

Triggering & Scheduling
The Overseer is "always" reacting to:

Fresh Level 1 Overview: Q1 ("How are we doing?") runs on:

A daily schedule (automatic)
Explicit Overseer request (on-demand)
Specific alerts (e.g., edge collapse detected)
User/Dev-Triggered Runs: Manual investigation requests

Follow-Up Investigations: After Level 1 reveals anomalies, Overseer triggers targeted investigations to Levels 2-5

Level 6 manages the actual scheduling and execution based on recipe triggers (daily_cron|on_demand|alert_driven).

Does NOT
Touch raw data, prompts, or low-level task configs
Manage schedules or validation (Level 6 handles this)
Write SQL, modify scopes, directly change overrides
Execute recipes (Level 6 does this)
Access raw tables or summarizers (always talks to Level 1 through Level 6)
Pull data directly (receives structured Level 1 JSON outputs only)
2. Level 6 – Research Manager (Data Provisioner & Executor)
Purpose
Level 6 is the data provisioner and execution manager. It translates Overseer's questions into recipes, prepares exact data bundles for investigators, and protects the math system.

Core Responsibilities
Question Translation

Converts Overseer questions into concrete recipes
Example: "How are we doing?" → level1_recipe_performance_overview_v1
Example: "Zoom into AI tokens with pattern X" → level1_recipe_zoom_semantic_breakdown_v1
Example: "Investigate semantic differences in these 12 tokens" → level2_recipe_semantic_deep_dive_v1
Data Bundle Preparation

Level 6 does NOT handle raw data itself
Level 6 uses summarizers and indexes (never queries raw tables)
Level 6 never writes SQL; it only calls summarizers, which encapsulate the DB access
For Level 1: Calls summarizers to create overview/zoom bundles
For Levels 2-5: Prepares exact, targeted data slices
Selects which summarizers to call (from the summarizer registry)
Uses data index/catalog to know what's available
Calls summarizers with appropriate filters/parameters
Assembles bundles with precise context
Ensures investigators are not overwhelmed
This keeps Level 6 from being overwhelmed—it orchestrates, doesn't process raw data
Recipe Management

Owns the library of versioned recipe configs
Can create/modify recipes based on Overseer instructions (long-term)
Maintains recipe health metrics
Execution Pipeline

Loads recipe config
Calls required summarizers
Builds LLM prompts (system + user + bundles + schema)
Calls LLM, validates JSON against schema
Scores output (format, consistency, novelty, risk)
Stores result in llm_learning
Forwards actionable items to appropriate consumers
Output Validation & Protection

Validates JSON schema (hard fail if invalid)
Checks for hallucinations (numbers match input bundles?)
Checks for conflicts (does it contradict math state?)
Prevents LLM outputs from directly touching lessons/overrides
Ensures all proposals flow through math/tuning validation first
Reporting

Provides execution summaries to Overseer
Reports task health, coverage, drift, ROI
Critical Rule: Levels 2-5 Are Blind Researchers
Levels 2-5 do NOT:

Access Level 1 data directly
Fetch their own data
Query raw tables
Decide what data they need
Browse or explore
Levels 2-5 ONLY:

Receive exact data bundles prepared by Level 6
Answer very specific, targeted questions
Analyze only the provided data slice
Return structured findings
This ensures:

Safety (no unauthorized data access)
Consistency (same data = same results)
Performance (no unnecessary queries)
Simplicity (investigators are focused tools)
Correctness (no hallucinated correlations)
Does NOT
Set strategic direction (Overseer does this)
Interpret anomalies (Overseer does this)
Do research (Levels 2-5 do this)
Directly change lessons/overrides (produces proposals only)
Handle raw data (uses summarizers/indexes only)
Query raw tables (summarizers do this)
3. Level 1 – Performance Observer (Zoomable Perception Layer)
Purpose
Level 1 is the Overseer's zoomable perception layer. It provides structured situational awareness about system performance and can zoom into specific regions when asked.

Level 1 does NOT:

Generate hypotheses
Do deep reasoning
Investigate causes
Propose structural changes
Modify trading logic
Access data directly (Level 6 calls summarizers)
Level 1 DOES:

Summarize performance
Highlight strong/weak zones
Identify anomalies
Show what deserves attention
Zoom into specific regions when asked
Return structured snapshots
Triggers
Daily schedule: Q1 ("How are we doing?") runs automatically
Overseer request: On-demand when Overseer needs fresh overview
Alert-driven: When edge collapse or major anomaly is detected
Zoom-in requests: When Overseer asks to zoom into specific regions
The Three Core Areas
Level 1 always covers these three regions:

Strong Edge Zones - Where we're performing well
Weak Edge Zones - Where we're performing badly
Anomalies - Where behavior is inconsistent or unexpected
Launch Goal: "How are we doing?" (General Overview)
Input Bundles (prepared by Level 6):

lesson_edge_summary - Edge/EV/reliability vectors from learning_lessons
lesson_decay_summary - Decay states, slopes, half-lives per slice
scope_delta_summary - Sibling scopes with large edge differences (derived from lessons/events)
exposure_crowding_summary - Crowding/exposure_skew metrics from runtime caches
raw_event_sample_summary (optional) - Targeted slices from pattern_trade_events for zoom follow-ups
Output Schema:

{
  "edge_health": {
    "overall_status": "healthy|degrading|emerging",
    "strong_zones": [
      {
        "pattern_key": "string",
        "action_category": "string",
        "scope_description": "string",
        "edge_raw": "number",
        "avg_rr": "number",
        "n": "integer",
        "stability": "stable|fragile|emerging",
        "notes": "string"
      }
    ],
    "weak_zones": [
      {
        "pattern_key": "string",
        "action_category": "string",
        "scope_description": "string",
        "edge_raw": "number",
        "avg_rr": "number",
        "n": "integer",
        "stability": "stable|fragile|decaying",
        "notes": "string"
      }
    ],
    "fragile_zones": [
      {
        "pattern_key": "string",
        "description": "string",
        "concern": "high_variance|low_n|inconsistent|decaying"
      }
    ],
    "decaying_patterns": [
      {
        "pattern_key": "string",
        "edge_trend": "number",
        "decay_pct": "number",
        "timeframe_days": "integer"
      }
    ],
    "emerging_patterns": [
      {
        "pattern_key": "string",
        "edge_trend": "number",
        "growth_pct": "number",
        "timeframe_days": "integer"
      }
    ],
    "surprising_anomalies": [
      {
        "type": "scope_divergence|semantic_split|unexpected_edge|mixed_performance",
        "description": "string",
        "pattern_key": "string",
        "scope_description": "string",
        "suggested_investigation": "semantic|structural|cross_domain|tuning",
        "priority": "low|medium|high"
      }
    ],
    "areas_to_watch": [
      {
        "pattern_key": "string",
        "reason": "string",
        "priority": "low|medium|high"
      }
    ]
  }
}
Each strong_zones/weak_zones entry now carries the full lesson payload: averaged RR, edge_raw, the six edge component scores, decay metadata, and exposure context. This mirrors what the miner stores in learning_lessons, so Overseer is reasoning directly on top of the ground-truth lesson store rather than legacy aggregates.

Consumers:

Overseer (primary) - Uses this to decide what to investigate next
Dashboards (secondary) - Human-readable performance views
Zoom-In Capability
When Overseer sees an anomaly and asks Level 1 to zoom in, Level 1 can:

Filter by specific pattern_keys
Filter by scope dimensions
Filter by semantic factors
Filter by time windows
Break down by subgroups (tokens, buckets, timeframes)
Show token-level details
Show scope-level details
Example Zoom-In Request:

Overseer: "Zoom into AI tokens with pattern pm.uptrend.S1.entry that show mixed performance"
Level 6: Prepares zoom recipe with filters
Level 1: Returns detailed breakdown of those specific tokens
Zoom-In Output Schema:

{
  "zoomed_region": {
    "filters_applied": {
      "pattern_key": "pm.uptrend.S1.entry",
      "semantic_filter": "AI",
      "performance_filter": "mixed"
    },
    "token_breakdown": [
      {
        "token_address": "string",
        "edge_raw": "number",
        "avg_rr": "number",
        "n": "integer",
        "scope_values": {},
        "semantic_factors": ["string"]
      }
    ],
    "scope_breakdown": [
      {
        "scope_values": {},
        "edge_raw": "number",
        "n": "integer",
        "token_count": "integer"
      }
    ],
    "key_differences": [
      {
        "dimension": "string",
        "value_a": "string",
        "value_b": "string",
        "edge_a": "number",
        "edge_b": "number"
      }
    ]
  }
}
Vision Goal
More sophisticated anomaly detection
Automatic trend classification
Predictive edge health warnings
Integration with semantic factors (once Level 2 matures)
Multi-level zooming (zoom into zoom)
4. Level 2 – Semantic Investigator (Blind Researcher)
Purpose
Level 2 investigates semantic/token-level differences when Overseer detects anomalies that math cannot explain.

Triggers
Overseer request: When Overseer detects semantic anomalies after Level 1 zoom
Specific questions: "Tokens with same scopes perform very differently" or "Semantic factors might be driving edge divergence"
On-demand: Only when Level 1 reveals token-level inconsistencies that need semantic investigation
Critical: Level 2 is a Blind Researcher
Level 2 does NOT:

Access Level 1 data directly
Fetch its own data
Query raw tables
Decide what data it needs
Level 2 ONLY:

Receives exact data bundle prepared by Level 6
Answers the specific question Overseer asked
Analyzes only the provided data slice
Launch Goal: Semantic Factor Investigation
How It Works:

Overseer: "These 12 AI tokens have identical scopes but 50/50 performance split. Investigate semantic subclasses."
Level 6 prepares exact bundle:
Calls token_metadata_bundle for those 12 tokens
Calls semantic_factor_summary for those tokens
Calls performance_breakdown_by_token for those tokens
Assembles into targeted bundle
Level 6 creates recipe: level2_recipe_semantic_subclass_analysis_v1
Level 2 receives:
The exact 12 tokens
Their metadata
Their performance data
The question: "Find semantic subclasses that explain the divergence"
Level 2 analyzes ONLY this bundle and returns findings
Input Bundle (prepared by Level 6):

{
  "target_tokens": ["token_address_1", "token_address_2", ...],
  "scope_context": {
    "pattern_key": "pm.uptrend.S1.entry",
    "scope_values": {...}
  },
  "token_metadata": [
    {
      "token_address": "string",
      "description": "string",
      "website": "string",
      "x_com_handle": "string",
      "dexscreener_data": {...}
    }
  ],
  "performance_data": [
    {
      "token_address": "string",
      "edge_raw": "number",
      "avg_rr": "number",
      "n": "integer"
    }
  ],
  "question": "Investigate semantic subclasses that explain why these tokens with identical scopes show 50/50 performance split"
}
Output Schema:

{
  "semantic_investigation": {
    "target_tokens": ["string"],
    "findings": [
      {
        "token_address": "string",
        "semantic_subclasses": [
          {
            "subclass": "string",
            "category": "narrative|style|theme|catalyst",
            "confidence": 0.0-1.0,
            "evidence": "string",
            "source": "dexscreener|website|twitter|github"
          }
        ],
        "divergence_explanation": "string",
        "recommended_actions": [
          "add_to_scope|exclude_from_pattern|create_new_scope_dim"
        ]
      }
    ],
    "meta_observations": [
      {
        "meta_name": "string",
        "tokens_in_meta": ["string"],
        "performance_summary": "string",
        "suggested_scope_integration": "boolean"
      }
    ]
  }
}
Consumers:

Overseer - Receives findings, decides if semantic factors should be added to scopes
Level 3 - Can use semantic findings to propose scope changes
Position table - Semantic factors stored for future analysis
Vision Goal: Full Token Research Agent
Crawl websites, GitHub, Twitter for deeper research
Track narrative momentum, meta rotations
Discover new curators, data sources
Wallet tracking, contract analysis
Vector similarity for token clustering
5. Level 3 – Structure Investigator (Blind Researcher)
Purpose
Level 3 investigates structural/scope-level differences when Overseer detects that scope dimensions might need adjustment, bucket boundaries are suboptimal, or dimensions are overfit.

Triggers
Overseer request: When Overseer detects structural anomalies after Level 1 zoom
Specific questions: "Scope deltas suggest dimension X is critical", "Bucket boundaries might be too wide/narrow", "Pattern shows inconsistent behavior across similar scopes"
Post-Level 2: When semantic factors (from Level 2) should be integrated into scopes
Weekly: After lesson builder runs, review scope structure (optional)
Critical: Level 3 is a Blind Researcher
Level 3 does NOT:

Access Level 1 data directly
Fetch its own data
Query raw tables
Decide what data it needs
Level 3 ONLY:

Receives exact data bundle prepared by Level 6
Answers the specific question Overseer asked
Analyzes only the provided data slice
Launch Goal: Scope Structure Analysis
How It Works:

Overseer: "This scope group has mixed performance. Investigate whether splitting by bucket_volatility stabilizes it."
Level 6 prepares exact bundle:
Calls scope_delta_summary for that pattern/scope
Calls dimension_importance_summary for relevant dimensions
Calls bucket_performance_summary for bucket_volatility splits
Assembles into targeted bundle
Level 6 creates recipe: level3_recipe_scope_split_analysis_v1
Level 3 receives:
The exact scope group
Dimension importance data
Bucket split performance data
The question: "Should we split this scope by bucket_volatility?"
Level 3 analyzes ONLY this bundle and returns findings
Input Bundle (prepared by Level 6):

{
  "target_scope": {
    "pattern_key": "pm.uptrend.S1.entry",
    "scope_values": {...}
  },
  "scope_deltas": [
    {
      "dimension": "string",
      "value_a": "string",
      "value_b": "string",
      "edge_a": "number",
      "edge_b": "number",
      "n_a": "integer",
      "n_b": "integer"
    }
  ],
  "dimension_importance": [
    {
      "dimension": "string",
      "importance_score": 0.0-1.0,
      "edge_impact": "high|medium|low"
    }
  ],
  "bucket_split_options": [
    {
      "dimension": "bucket_volatility",
      "split_points": ["string"],
      "performance_by_split": [...]
    }
  ],
  "question": "Should this scope be split by bucket_volatility to improve edge stability?"
}
Output Schema:

{
  "structure_investigation": {
    "dimension_insights": [
      {
        "dimension": "string",
        "importance_score": 0.0-1.0,
        "edge_impact": "high|medium|low",
        "evidence": "string",
        "recommendation": "keep|remove|split|merge"
      }
    ],
    "scope_adjustment_proposals": [
      {
        "pattern_key": "string",
        "current_scope": {},
        "proposed_scope": {},
        "rationale": "string",
        "expected_edge_improvement": "number",
        "confidence": 0.0-1.0
      }
    ],
    "bucket_split_recommendations": [
      {
        "dimension": "string",
        "current_bucket": "string",
        "proposed_split": ["string", "string"],
        "rationale": "string",
        "edge_improvement_estimate": "number"
      }
    ],
    "new_dimension_proposals": [
      {
        "dimension_name": "string",
        "dimension_type": "semantic|numeric|categorical",
        "rationale": "string",
        "integration_complexity": "low|medium|high"
      }
    ]
  }
}
Consumers:

Overseer - Reviews proposals, decides what to test
Math layer - Validates scope proposals via SQL tests
Lesson builder - Can incorporate approved scope changes
Vision Goal: Dimension Weighting
Compute global importance weights for all dimensions
Suggest architecture changes to lesson builder
Auto-detect overfit dimensions
Integrate semantic factors as scope dimensions
6. Level 4 – Cross-Domain Pattern Investigator (Blind Researcher)
Purpose
Level 4 investigates cross-domain patterns when Overseer detects that similar lever adjustments or semantic+scope combos appear across different pattern families.

Triggers
Overseer request: When Overseer detects cross-domain patterns after reviewing multiple Level 1/2/3 outputs
Specific questions: "Same lever adjustments appearing in different families", "Semantic+scope combos show consistent effects across patterns", "Potential meta-lessons that span multiple domains"
Weekly: After lesson builder runs, review for cross-domain patterns (optional)
Critical: Level 4 is a Blind Researcher
Level 4 does NOT:

Access Level 1 data directly
Fetch its own data
Query raw tables
Decide what data it needs
Level 4 ONLY:

Receives exact data bundle prepared by Level 6
Answers the specific question Overseer asked
Analyzes only the provided data slice
Launch Goal: Cross-Domain Synthesis
How It Works:

Overseer: "Both prediction-market S2 entries and low-cap AI entries show aggressive trim preference under high volatility. Investigate if this is a cross-domain pattern."
Level 6 prepares exact bundle:
Calls lesson_override_summary for those patterns
Calls semantic_performance_summary for relevant semantic factors
Calls scope_overlap_summary for those patterns
Assembles into targeted bundle
Level 6 creates recipe: level4_recipe_cross_domain_pattern_v1
Level 4 receives:
The exact patterns to compare
Their lever adjustments
Their scope/semantic conditions
The question: "Is there a cross-domain pattern here?"
Level 4 analyzes ONLY this bundle and returns findings
Input Bundle (prepared by Level 6):

{
  "target_patterns": ["pattern_key_1", "pattern_key_2"],
  "lever_adjustments": [
    {
      "pattern_key": "string",
      "lever_type": "trim_timing|entry_delay|exit_aggression",
      "adjustment": {},
      "scope_conditions": {},
      "semantic_conditions": {}
    }
  ],
  "scope_overlap": {
    "common_scopes": [...],
    "unique_scopes": [...]
  },
  "semantic_overlap": {
    "common_factors": [...],
    "unique_factors": [...]
  },
  "question": "Is there a cross-domain pattern that explains why these patterns share lever preferences?"
}
Output Schema:

{
  "cross_domain_investigation": {
    "meta_lessons": [
      {
        "meta_lesson_name": "string",
        "applies_to_patterns": ["string"],
        "lever_adjustment": {},
        "scope_conditions": {},
        "semantic_conditions": {},
        "rationale": "string",
        "confidence": 0.0-1.0,
        "suggested_validation": "sql_test|ab_test|tuning_episode"
      }
    ],
    "cross_domain_patterns": [
      {
        "pattern_description": "string",
        "affected_patterns": ["string"],
        "common_levers": ["string"],
        "common_scopes": {},
        "edge_consistency": "high|medium|low"
      }
    ],
    "hypothesis_seeds": [
      {
        "hypothesis": "string",
        "related_patterns": ["string"],
        "test_type": "sql_aggregate|sql_regression|ab_scope_test",
        "priority": "low|medium|high"
      }
    ]
  }
}
Consumers:

Overseer - Reviews meta-lessons, decides what to validate
Level 5 - Can use hypothesis seeds for tuning investigations
Math layer - Validates meta-lessons via tests
Vision Goal: Pattern Recognition Brain
Spot structures math doesn't detect
Automatically spawn hypotheses for Level 5
Detect emerging regimes via semantic+scope+override relationships
7. Level 5 – Tuning Investigator (Blind Researcher)
Purpose
Level 5 investigates timing/counterfactual issues when Overseer detects that execution constraints (entry delays, trim timing, exit aggression) might be creating missed opportunities.

Activation Trigger
Overseer sees anomaly like:

"Counterfactual improvement buckets show large missed RR"
"Tuning episode results suggest execution timing issues"
"CF data shows we could enter/exit better"
Critical: Level 5 is a Blind Researcher
Level 5 does NOT:

Access Level 1 data directly
Fetch its own data
Query raw tables
Decide what data it needs
Level 5 ONLY:

Receives exact data bundle prepared by Level 6
Answers the specific question Overseer asked
Analyzes only the provided data slice
Launch Goal: R/R Maximization Analysis
How It Works:

Overseer: "This pattern is strong but CF data shows large missed entry RR. Investigate timing constraints."
Level 6 prepares exact bundle:
Calls tuning_episode_summary for that pattern
Calls counterfactual_opportunity_summary for entry/exit improvements
Calls lesson_response_summary for current timing constraints
Assembles into targeted bundle
Level 6 creates recipe: level5_recipe_timing_optimization_v1
Level 5 receives:
The exact pattern and scope
CF entry/exit data
Current timing constraints
The question: "How can we improve R/R by adjusting timing?"
Level 5 analyzes ONLY this bundle and returns findings
Input Bundle (prepared by Level 6):

{
  "target_pattern": {
    "pattern_key": "pm.uptrend.S1.entry",
    "scope_values": {...}
  },
  "tuning_episode_data": [
    {
      "took_trade": "boolean",
      "success": "boolean",
      "rr": "number",
      "cf_entry_improvement_bucket": "none|small|medium|large",
      "cf_exit_improvement_bucket": "none|small|medium|large",
      "could_enter_better": {...},
      "could_exit_better": {...}
    }
  ],
  "current_constraints": {
    "entry_delay": "number",
    "trim_timing": "string",
    "exit_aggression": "string"
  },
  "question": "How can we improve R/R by adjusting timing constraints for this pattern/scope?"
}
Output Schema:

{
  "tuning_investigation": {
    "rr_improvement_opportunities": [
      {
        "pattern_key": "string",
        "stage": "S1|S3|trim|exit",
        "current_constraint": "string",
        "proposed_adjustment": "string",
        "rationale": "string",
        "cf_evidence": {
          "missed_rr_avg": "number",
          "cf_bucket": "none|small|medium|large",
          "sample_size": "integer"
        },
        "expected_rr_improvement": "number",
        "confidence": 0.0-1.0
      }
    ],
    "tuning_hypotheses": [
      {
        "hypothesis": "string",
        "test_type": "entry_delay|trim_timing|exit_aggression|...",
        "scope_conditions": {},
        "proposed_sql": "string",
        "priority": "low|medium|high"
      }
    ],
    "stage_specific_recommendations": [
      {
        "stage": "S1|S3|trim|exit",
        "recommendation": "string",
        "affected_patterns": ["string"],
        "validation_approach": "tuning_episode|sql_test|ab_test"
      }
    ]
  }
}
Consumers:

Overseer - Reviews opportunities, decides what to test
Tuning system - Receives hypotheses for validation
Math layer - Validates tuning proposals via SQL tests
Vision Goal: Full R/R Maximizer
Cover entries, trims, exits comprehensively
Integrate with math hypothesis runner (auto-run SQL tests)
Feed results back into tuning episodes
Detect systematic execution improvements
7. Math & Learning System Integration
Purpose
The Math Layer validates all LLM research outputs and integrates validated insights into the learning system. This section defines the complete feedback loop between LLM research and the math/learning infrastructure.

Inputs from LLM Research Layer
The Math Layer receives proposals from:

Level 2 (Semantic): Semantic factor integration suggestions, semantic scope dimension proposals
Level 3 (Structure): Scope adjustment proposals, bucket split recommendations, new dimension proposals
Level 4 (Cross-Domain): Meta-lesson candidates, cross-domain pattern hypotheses
Level 5 (Tuning): Tuning hypotheses, R/R improvement proposals, execution timing adjustments
Validation Mechanisms
SQL Tests / Aggregates

Validates scope proposals by computing edge differences
Tests statistical significance of edge claims
Verifies sample sizes and variance estimates
Checks for overfitting (edge on training vs validation windows)
Tuning Episodes

Validates tuning hypotheses via S1/S3 stage episodes
Tests counterfactual improvements with historical data
Measures actual R/R impact of proposed changes
AB Tests on Scopes or Overrides

Tests scope splits by comparing sibling scopes
Validates override proposals by comparing before/after performance
Measures impact of new dimension integrations
Outputs to Learning System
Approved Scope Changes → Lesson Builder

Validated scope proposals become inputs to lesson_builder_v5
New dimensions (e.g., semantic factors) get integrated into scope computation
Bucket splits get applied to future scope calculations
Updated Overrides → Learning Configs

Validated meta-lessons flow through override materializer
Tuning improvements get incorporated into PM config
Semantic factor overrides get added to learning_configs.pm.config_data
Rejected Ideas → Logged with Feedback

Failed validations are written back to llm_learning with:
validation_status: "failed"
failure_reason: "string"
math_evidence: {...}
This feedback helps Overseer learn which recipes/levels are useful
Feedback Loop to Overseer
The Math Layer writes validation results back so Overseer can learn:

Which hypotheses got validated → Prioritize similar research directions
Which hypotheses got rejected → Avoid repeating failed patterns
Which recipes are paying off → Focus on high-ROI investigation types
Which anomalies recur → Escalate persistent issues
Level 6 provides this feedback via a recent_research_summary bundle that includes:

Recent validation outcomes
Pending validation status
Historical success rates per recipe/level
This prevents Overseer from recursing on the same anomaly forever and helps it learn which research strategies work.

8. Data Infrastructure
8.1 Data Index Layer (Catalog)
Static registry describing available tables, fields, summarizers, bundle names, schemas
Note: "Static" means table schemas are stable, not that data is static. Data updates continuously.
Queried by Level 6 to understand what can be fetched for a recipe
Overseer can inspect the catalog when designing new goals
8.2 Summarizer Layer
Deterministic Python modules that read the DB and return small JSON bundles

Bundles are designed per use case:

global_edge_summary - Edge by module/action_category
pattern_edge_summary - Edge by pattern_key + top/bottom scopes
scope_delta_summary - Sibling scopes with large edge differences
edge_history_summary - Edge trends over time
semantic_factor_summary - Semantic factor performance
token_metadata_bundle - Token metadata from DexScreener/external sources
tuning_episode_summary - Tuning episode results
counterfactual_opportunity_summary - CF entry/exit improvements
And more...
Level 6 maps recipe→bundles via a registry:

BUNDLE_REGISTRY = {
    "global_edge_summary": summarize_global_edges,
    "pattern_edge_summary": summarize_pattern_edges,
    "scope_delta_summary": summarize_scope_deltas,
    "edge_history_summary": summarize_edge_history,
    "semantic_factor_summary": summarize_semantic_factors,
    "token_metadata_bundle": fetch_token_metadata,
    ...
}
Future: Level 6 can create new summarizers (LLM-assisted) but only after validation by math/ops.

8.2.1 External Data Sources
External sources (Dexscreener, websites, x.com, GMGN, etc.) are accessed by summarizers, not by LLMs directly. LLMs only see the JSON bundles built from these APIs.

Summarizers encapsulate all external API calls
Summarizers handle rate limiting, caching, and error handling
LLMs receive clean, structured JSON bundles
This keeps the "no tools from inside the LLMs" pattern consistent
Example: token_metadata_bundle summarizer calls Dexscreener API, fetches website content, searches x.com, and returns a structured JSON bundle. Level 2 never directly calls these APIs.

8.3 Input Bundles
JSON documents produced by summarizers
Each bundle has:
metadata (generated_at, window_days, filters)
payload (e.g. list of patterns, scope stats, history)
Level 6 merges bundles into the LLM prompt
8.4 Output Storage
Structured outputs stored in llm_learning (or dedicated tables per level) with metadata:
recipe_id, level, version
input_bundle_hash
output JSON (validated)
scoring metrics (usefulness, risk)
downstream status (e.g. "math test created", "dashboard updated")
8.5 Event → Lesson → Override Pipeline (Core Data Flow)
This architecture now treats learning as three explicit layers:

Fact Table – pattern_trade_events

One row per trade/action (the “reality buffer”)
Captures pattern_key, action_category, full unified scope (entry + action + regime dims), RR, PnL, timestamps, metadata
Written immediately when a trade closes; no aggregation logic lives here
Lesson Miner – learning_lessons

Lesson builder scans pattern_trade_events (level-wise) for any slice with N ≥ 33
Stores every observed phenomenon, even if neutral/negative edge
stats JSON now includes the full edge vector (avg_rr, edge_raw, ev/reliability/support/time/stability scores) plus decay metadata (linear/exponential slopes, half-life, decay_state)
Provides the canonical truth table that the LLM layer reasons about
Override Table – pm_overrides

Override materializer reads learning_lessons, filters for actionable edges (e.g., edge significantly above/below baseline, acceptable decay/reliability)
Writes only those slices into a dedicated override table that the PM runtime blends at execution
Prevents runtime from being flooded with neutral lessons while keeping the full memory intact for analysis
This separation keeps observation (events), understanding (lessons), and action (overrides) clean. Summarizers surface data from all three layers depending on the recipe:

Level 1 primarily reads learning_lessons (edge/decay) + exposure caches derived from runtime
Levels 2-3 can request raw pattern_trade_events slices when needed for zooms
Overseer can compare lessons vs active overrides to ask, “What truths exist that we are not acting on?”
9. Execution Pipeline (Per Recipe)
Overseer → Level 6 (Goal: run recipe X)
Level 6:
    1. Loads recipe config (JSON)
    2. Calls required summarizers to fetch bundles
    3. Builds LLM prompt (system + user + bundles + schema)
    4. Calls LLM, validates JSON against schema
    5. Scores output
    6. Stores result + forwards actionable items
9.1 Recipe Config (Example: Level 1 General Overview)
{
  "id": "level1_recipe_performance_overview_v1",
  "level": "level1_performance_observer",
  "version": 1,
  "goal": "Provide structured performance awareness for Overseer.",
  "input_bundles": [
    "global_edge_summary",
    "pattern_edge_summary",
    "scope_delta_summary",
    "edge_history_summary"
  ],
  "llm_tasks": [
    "identify_strong_zones",
    "identify_weak_zones",
    "detect_fragile_zones",
    "detect_decaying_patterns",
    "detect_emerging_patterns",
    "identify_surprising_anomalies",
    "flag_areas_to_watch"
  ],
  "constraints": {
    "max_patterns_per_group": 20,
    "min_sample_size": 30,
    "min_edge_abs": 0.05
  },
  "output_schema": {
    "edge_health": { ... }
  },
  "consumers": [
    "overseer",
    "edge_dashboard"
  ],
  "run_config": {
    "trigger": "daily_cron|on_demand",
    "max_retries": 2,
    "timeout_seconds": 60
  }
}
9.2 Prompt Assembly
System prompt: describes role, constraints, required output format
User prompt: includes recipe metadata, instructions per task, bundle descriptions, output schema, actual bundles (as JSON inside triple backticks)
No raw SQL or table names; only summarizer outputs
9.3 Validation & Scoring
After LLM response:
Validate JSON schema (hard fail if invalid)
Score:
format_valid (bool)
consistency (did numbers match input bundles?)
novelty/usefulness (anomalies detected, areas flagged)
risk/conflict (does it contradict known math state?)
Store scores; degrade or disable recipe if repeated failures
9.4 Consumers
Level 6 routes parts of the output to:
Overseer (primary for Level 1)
Dashboards (human-readable views)
Math test queue (SQL snippets for validation - from Levels 2-5)
Tuning system (hypotheses from Level 5)
Lesson builder (scope proposals from Level 3)
10. Complete Example Investigation Flow
Scenario: "AI tokens with identical scopes show 50/50 performance split"
Step 1: Overseer asks Q1

Overseer: "How are we doing?"
Level 6: Executes level1_recipe_performance_overview_v1
Level 1: Returns performance map with surprising_anomalies:
  {
    "surprising_anomalies": [{
      "type": "scope_divergence",
      "description": "AI tokens with identical scopes show 50% strong, 50% weak performance",
      "pattern_key": "pm.uptrend.S1.entry",
      "suggested_investigation": "semantic",
      "priority": "high"
    }]
  }
Step 2: Overseer asks Level 1 to zoom

Overseer: "Zoom into AI tokens with pattern pm.uptrend.S1.entry that show mixed performance"
Level 6: Executes level1_recipe_zoom_semantic_breakdown_v1 with filters:
  - pattern_key: pm.uptrend.S1.entry
  - semantic_filter: AI
  - performance_filter: mixed
Level 1: Returns zoomed slice:
  {
    "zoomed_region": {
      "token_breakdown": [
        {"token_address": "0x123...", "edge_raw": 0.15, "n": 45},
        {"token_address": "0x456...", "edge_raw": -0.08, "n": 38},
        ...
      ],
      "key_differences": [
        {
          "dimension": "semantic_factor",
          "value_a": "AI Infra",
          "value_b": "AI Meme",
          "edge_a": 0.12,
          "edge_b": -0.05
        }
      ]
    }
  }
Step 3: Overseer understands shape and routes investigation

Overseer: "These 12 AI tokens have identical scopes but semantic subclasses differ. 
           Investigate whether semantic subclasses explain the divergence."
Level 6: Prepares exact bundle for Level 2:
  - Calls token_metadata_bundle for those 12 tokens
  - Calls semantic_factor_summary for those tokens
  - Calls performance_breakdown_by_token for those tokens
  - Assembles into targeted bundle
Level 6: Executes level2_recipe_semantic_subclass_analysis_v1
Level 2: Receives bundle, analyzes ONLY provided data, returns:
  {
    "findings": [{
      "divergence_explanation": "Half are 'AI Infra' tokens (high utility, strong roadmap), 
                                half are 'AI Meme' tokens (trend-chasing, weak roadmap)",
      "recommended_actions": ["add_to_scope"]
    }]
  }
Step 4: Overseer receives findings and decides next step

Overseer: "Semantic subclasses explain divergence. Should integrate into scopes."
Overseer: "Propose scope changes to incorporate semantic_meta dimension"
Level 6: Prepares exact bundle for Level 3:
  - Calls scope_delta_summary for that pattern
  - Calls dimension_importance_summary
  - Assembles into targeted bundle
Level 6: Executes level3_recipe_scope_integration_v1
Level 3: Receives bundle, analyzes ONLY provided data, returns:
  {
    "new_dimension_proposals": [{
      "dimension_name": "semantic_meta",
      "dimension_type": "semantic",
      "values": ["AI Infra", "AI Meme", "AI Agent", ...],
      "rationale": "Semantic subclasses explain performance divergence",
      "integration_complexity": "medium"
    }]
  }
Step 5: Overseer reviews and escalates to math

Overseer: "Proposal looks good. Send to math layer for validation."
Level 6: Forwards scope proposal to math test queue
Math Layer: Runs SQL tests, confirms edge improvement
System: Lesson builder incorporates new scope dimension
11. Implementation Notes / Future Enhancements
Data Catalog

YAML/JSON describing tables, fields, summarizers, bundle schemas
Should be easily inspectable by humans and the Overseer (via tool)
Recipe Store

Could live in code repo (version controlled) and/or Supabase
Metadata includes owner, last_updated, approval status
Level 6 can create/modify recipes based on Overseer instructions (long-term)
LLM Sandbox

Each recipe should run under isolated runtime with guardrails
Logging for inputs/outputs (with redaction if needed)
Testing & Validation

Before enabling a recipe, run it in "dry run" mode (log output but don't forward to consumers)
Have math layer verify early outputs, ensure they're sane
Metrics

Track ROI per level/recipe (did it lead to validated hypotheses? overrides? tuning wins?)
Use metrics to prioritize research investment
Scaling

As new tables/dimensions appear (semantic factors, new CF metrics), add summarizers + catalog entries
Level 6 & Overseer adapt recipes accordingly
12. Summary
Overseer (Active Intelligence) asks 5 core questions, interprets results, routes investigations
Level 6 (Data Provisioner) translates questions into recipes, prepares exact bundles, protects system
Level 1 (Zoomable Perception) provides structured awareness and can zoom into specific regions
Levels 2-5 (Blind Researchers) receive exact bundles and answer targeted questions only
Data infrastructure separates raw tables from LLMs via summarizers and bundles
Recipes describe everything: inputs, tasks, outputs, triggers, consumers
Validation and scoring keep the system safe; outputs always go through math/tuning before affecting overrides
Complete Flow:

Perceive (L1) → Think (Overseer) → Zoom (L1) → Think (Overseer) → Investigate (L2-5) → Verify (Math) → Adapt (System)
Key Principle: Levels 2-5 are blind researchers. They do NOT access Level 1 data or fetch their own data. They ONLY receive exact bundles prepared by Level 6 and answer very specific questions.

This blueprint should guide both near-term implementation (v5 launch) and long-term evolution (adaptive research agent).