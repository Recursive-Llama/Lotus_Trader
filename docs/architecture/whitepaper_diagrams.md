


┌────────────────────────────────────────────────────────────────────────────┐
│                         SERVICE 1: SCANNER                                  │
│                     (Batch, runs every N minutes)                           │
│                                                                            │
│   1. Discover markets → 69 candidates                                      │
│   2. Level 1 scan → Top 33 battlegrounds                                   │
│   3. Level 2 scan → Top 12 trade candidates                                │
│   4. Write to DB:                                                          │
│      - seer_battlegrounds (with SM wallet map)                             │
│      - seer_trade_signals (P2, clarity, alignment, etc.)                   │
│                                                                            │
└─────────────────────────────────┬──────────────────────────────────────────┘
                                  │ DB writes
                                  ▼
                           ┌─────────────┐
                           │   Supabase  │
                           │  (shared)   │
                           └─────────────┘
                                  ▲ DB reads + writes
                                  │
┌─────────────────────────────────┴──────────────────────────────────────────┐
│                        SERVICE 2: TRADER                                    │
│                     (Continuous, WebSocket-based)                           │
│                                                                            │
│   1. Subscribe to top 33 markets via WebSocket                             │
│   2. On each trade event:                                                  │
│      - Is this a known SM wallet?                                          │
│      - Update running SM strength (YES/NO)                                 │
│      - Recalculate clarity, alignment, delta                               │
│   3. Trigger Entry/Exit based on:                                          │
│      - Portfolio rules (max 6, top-3 insertion)                            │
│      - SM behaviour change (reversal, clarity collapse)                    │
│   4. Execute orders                                                        │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘



