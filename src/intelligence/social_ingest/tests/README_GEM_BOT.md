# Gem Bot Monitor Integration

This module monitors the Gem Bot dashboard for new cryptocurrency tokens and automatically creates trading strands.

## Features

- **Cookie-based Authentication**: Saves login cookies for persistent access
- **Column Monitoring**: Monitors specific columns (Risky, Balanced, Conservative)
- **Real-time Detection**: Detects new token entries using Playwright
- **Direct Trading**: Bypasses decision maker for pre-vetted tokens
- **Test Mode**: Monitor Risky column with 1.2% allocation for testing

## Configuration

### Test Mode (Default)
- **Column**: Risky (left column)
- **Allocation**: 1.2%
- **Strand Kind**: `gem_bot_risky_test`
- **Risk Level**: Medium

### Production Mode
- **Column**: Conservative (right column)
- **Allocation**: 12%
- **Strand Kind**: `gem_bot_conservative`
- **Risk Level**: Low

## Usage

### Test Strand Creation Only
```bash
cd src/intelligence/social_ingest
python test_gem_bot_monitor.py --mode strand
```

### Full Website Monitoring
```bash
cd src/intelligence/social_ingest
python test_gem_bot_monitor.py --mode full
```

### Integration with Main System
The Gem Bot monitor is automatically started when running the main social trading system:

```bash
python run_social_trading.py
```

## Authentication

1. **First Run**: Browser opens in headed mode for manual login
2. **Cookie Save**: Login cookies are saved to `src/config/gem_bot_cookies.json`
3. **Subsequent Runs**: Cookies are automatically loaded

## Data Extraction

The monitor extracts the following data from each token card:

- **Token Information**:
  - Ticker symbol
  - Contract address
  - Project name
  - Multiplier (if available)

- **Trading Metrics**:
  - Market cap
  - Liquidity
  - Transaction count
  - Holder count
  - Creator percentage
  - Bundled percentage
  - Snipers percentage

## Strand Structure

Created strands follow the standard structure with:

- **Signal Pack**: Complete token, venue, and curator data
- **Trading Signals**: Allocation percentage, confidence, reasoning
- **Auto-approval**: Bypasses decision maker
- **Direct Trader**: Triggers trader immediately

## Files

- `gem_bot_monitor.py`: Main monitoring module
- `test_gem_bot_monitor.py`: Test script
- `src/config/gem_bot_config.yaml`: Configuration file
- `src/config/gem_bot_cookies.json`: Saved authentication cookies

## Integration Points

1. **Universal Learning System**: Processes strands and triggers trader
2. **Trader Lowcap**: Executes trades with specified allocation
3. **Database**: Saves strands and positions
4. **Main System**: Integrated into `run_social_trading.py`

## Testing

The test mode allows safe testing with:
- Lower allocation (1.2% vs 12%)
- Risky column instead of Conservative
- Same trading logic and strand processing
- Real website monitoring with authentication
