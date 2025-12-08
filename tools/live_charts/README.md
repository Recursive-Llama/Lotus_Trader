# Live Position Chart Generator

Generate charts for live positions to verify EMAs, geometry S/R levels, and current state.

## Purpose

This tool helps verify that:
- EMAs are computed correctly (compares stored `features.ta` values to recomputed values)
- Geometry S/R levels are correct (visualizes them on the chart)
- Positions are in the correct stages (shows current state on chart)

## Usage

### By Position ID
```bash
python3 generate_live_chart.py --position-id 123
```

### By Contract Address
```bash
# All timeframes for a token
python3 generate_live_chart.py --contract 0xABC... --chain solana

# Specific timeframe
python3 generate_live_chart.py --contract 0xABC... --chain solana --timeframe 1h
```

### By Ticker Symbol
```bash
python3 generate_live_chart.py --ticker DREAMS --timeframe 1h
```

### All Positions
```bash
# All watchlist + active positions
python3 generate_live_chart.py --all

# All positions for a specific timeframe
python3 generate_live_chart.py --all --timeframe 1h

# All positions in a specific stage
python3 generate_live_chart.py --all --stage S3

# Combinations: timeframe + stage
python3 generate_live_chart.py --all --timeframe 1m --stage S3
python3 generate_live_chart.py --all --timeframe 15m --stage S2
python3 generate_live_chart.py --all --timeframe 1h --stage S1
python3 generate_live_chart.py --all --timeframe 4h --stage S0
```

## Output

Charts are saved to `tools/live_charts/output/` with filenames like:
- `live_chart_DREAMS_1h_1234567890.png`

Each chart shows:
- Price and all EMAs (20, 30, 60, 144, 250, 333)
- Geometry S/R levels (horizontal dashed lines)
- Current state marker (colored star)
- EMA verification status (matches/mismatches)
- Current EMA values (text annotation)

## EMA Verification

The tool automatically verifies that recomputed EMAs match stored values from `features.ta`:
- ✅ Green checkmark if all EMAs match (within 0.1% tolerance)
- ⚠️ Warning if any EMAs mismatch (shows stored vs computed values)

## Requirements

- `SUPABASE_URL` and `SUPABASE_KEY` environment variables
- Position must have OHLC data in `lowcap_price_data_ohlc` table
- Position must have `features.ta` (from TA Tracker)
- Position must have `features.geometry` (from Geometry Builder)
- Position must have `features.uptrend_engine_v4` (from Uptrend Engine)

