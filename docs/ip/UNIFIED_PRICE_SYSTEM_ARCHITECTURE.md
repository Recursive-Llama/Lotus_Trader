# Unified Price System Architecture

## Overview

This document outlines the plan to unify the current dual price system (Price Oracle + Price Monitor) into a single, robust price management system with proper data infrastructure.

## Current Problems

### 1. Dual Price System Issues
- **Code Duplication**: Both systems implement similar pricing logic for the same chains
- **Inconsistent Pricing**: Price Oracle uses DexScreener, Price Monitor uses multiple methods
- **Maintenance Overhead**: Two systems to maintain, debug, and update
- **Integration Complexity**: Price Monitor accesses Price Oracle through trader instance
- **Caching Inconsistency**: Price Monitor has caching while Price Oracle doesn't
- **Error Handling Duplication**: Both systems handle the same pricing failures

### 2. Database Data Management Issues
- **Fragile Saves**: One wrong column name kills entire position save
- **Redundant API Calls**: Both systems calling APIs for same tokens
- **No Price History**: Not storing price data, just current prices
- **Inconsistent Data Sources**: Different systems using different APIs

### 3. API Usage Inefficiency
- **Wasteful Calls**: Multiple systems making separate calls for same tokens
- **Rate Limiting**: No coordinated rate limiting across systems
- **No Caching Strategy**: Repeated calls for same data

## Proposed Solution

### 1. Unified Price Oracle Architecture

#### Core Components
```
Unified Price Oracle
├── Price Fetcher (DexScreener + Chain-specific methods)
├── Intelligent Caching Layer
├── Data Quality Monitor
├── Rate Limiting Manager
└── Price History Storage
```

#### Key Features
- **Single Source of Truth**: One system for all pricing needs
- **Multi-Chain Support**: BSC, Base, Ethereum, Solana
- **Intelligent Caching**: Shared cache across all requests
- **Data Quality Tracking**: Monitor price reliability and staleness
- **Rate Limiting**: Coordinated API usage (300 calls/minute limit)
- **Price History**: Store 1-minute price snapshots for analysis

### 2. Database Schema Design

#### Hybrid Approach: Keep Position Data Together, Separate Price Data

**Position Table (Enhanced)**
```sql
-- Keep existing structure but add data quality tracking
CREATE TABLE lowcap_positions (
    id UUID PRIMARY KEY,
    token_contract VARCHAR(42) NOT NULL,
    token_chain VARCHAR(20) NOT NULL,
    -- ... existing position fields
    
    -- Keep JSONB arrays but make them more robust
    entries JSONB DEFAULT '[]'::jsonb,
    exits JSONB DEFAULT '[]'::jsonb,
    planned_entries JSONB DEFAULT '[]'::jsonb,
    planned_exits JSONB DEFAULT '[]'::jsonb,
    
    -- Add data quality tracking
    last_price_update TIMESTAMPTZ,
    price_data_quality DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Price Data Table (New)**
```sql
-- Time-series price data following alpha_market_data pattern
CREATE TABLE lowcap_price_data_1m (
    token_contract VARCHAR(42) NOT NULL,
    chain VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price_usd DECIMAL(20,8) NOT NULL,
    price_native DECIMAL(20,8) NOT NULL,
    quote_token VARCHAR(10) NOT NULL,
    liquidity_usd DECIMAL(20,2),
    liquidity_change_1m DECIMAL(20,2),
    volume_24h DECIMAL(20,2),
    volume_change_1m DECIMAL(20,2),
    price_change_24h DECIMAL(8,4),
    market_cap DECIMAL(20,2),
    fdv DECIMAL(20,2),
    dex_id VARCHAR(50),
    pair_address VARCHAR(42),
    source VARCHAR(50) DEFAULT 'dexscreener',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (token_contract, chain, timestamp)
);

-- Indexes for performance
CREATE INDEX idx_lowcap_price_data_1m_token_timestamp ON lowcap_price_data_1m(token_contract, chain, timestamp DESC);
CREATE INDEX idx_lowcap_price_data_1m_timestamp ON lowcap_price_data_1m(timestamp DESC);
```

### 3. Data Flow Architecture

#### Scheduled Collection (1-minute intervals)
```
Active Positions → Token List → DexScreener API → lowcap_price_data_1m table
```

#### On-Demand Requests
```
Request → DexScreener API → Return Price (no database storage)
```

#### Position Monitoring
```
Position Check → lowcap_price_data_1m table → Execute Actions
```

### 4. Implementation Plan

#### Phase 1: Database Infrastructure
1. Create `lowcap_price_data_1m` table
2. Add data quality fields to `lowcap_positions`
3. Create proper indexes and constraints

#### Phase 2: Remove Price Monitor
1. Delete Price Monitor code completely
2. Update position monitoring to use Price Oracle
3. Wire scheduled collection to database

#### Phase 3: Data Collection System
1. Build scheduled price collection (1-minute intervals for active positions)
2. Store results in `lowcap_price_data_1m` table
3. Keep on-demand requests as API-only

#### Phase 4: Integration
1. Update all components to use unified Price Oracle
2. Test scheduled collection and position monitoring
3. Verify database storage and retrieval

### 5. Benefits

#### Immediate Benefits
- **Single Source of Truth**: One system for all pricing
- **Consistent Pricing**: Same price for same token across all systems
- **Better Caching**: Shared cache reduces API calls
- **Simpler Architecture**: One component to maintain

#### Long-term Benefits
- **Price History**: Historical data for analysis and backtesting
- **Data Quality**: Track and monitor price reliability
- **Performance**: Optimized API usage and caching
- **Scalability**: Handle more tokens and higher frequency

### 6. API Usage Strategy

#### Current State
- Price Oracle: On-demand calls (unlimited)
- Price Monitor: 30-60 second intervals (unlimited)
- Total: Potentially hundreds of calls per minute

#### Proposed State
- **Scheduled Collection**: 1 call per active token per minute (stored in database)
- **On-Demand Requests**: API calls only (no database storage)
- **Database**: Only contains scheduled collection data for active positions
- **Total**: 300 calls per minute limit (scheduled + on-demand)

### 7. Implementation Strategy

#### Simple Approach
- **Keep Price Oracle** as-is (it works well with DexScreener)
- **Remove Price Monitor** completely (it's redundant)
- **Wire everything to Price Oracle** (clean, simple)
- **Add price data storage** for history

#### No Complex Migration
- Just delete Price Monitor code
- Update position monitoring to use Price Oracle
- Done

## Next Steps

### Phase 1: Basic Implementation
1. **Database Schema**: Create `lowcap_price_data_1m` table
2. **Remove Price Monitor**: Delete all Price Monitor code
3. **Wire to Price Oracle**: Update position monitoring to use Price Oracle
4. **Scheduled Collection**: Store price data in `lowcap_price_data_1m` table
5. **Done**: Simple, clean, working system

### Phase 2: Data Rollups (Later)
1. **Add Rollup Tables**: Create `lowcap_price_data_5m`, `lowcap_price_data_15m`, `lowcap_price_data_1h` tables
2. **Rollup Jobs**: Implement scheduled jobs to roll up 1m data to higher timeframes
3. **OHLCV Data**: Store open, high, low, close, volume for each timeframe
4. **Performance**: Optimize queries for different timeframes

## Notes

- Price Oracle already works well - just use it everywhere
- No complex migration needed - just delete redundant code
- Database only for scheduled collection (active position tokens)
- On-demand requests use API directly (no database storage)
- Store both native and USD prices in same entry (as Price Oracle already provides)
- Focus on simplicity over complexity
