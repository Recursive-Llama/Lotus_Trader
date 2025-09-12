# Stage 4D: Price and Temporal Calibration

## Overview
Stage 4D is the central calibration hub that creates mathematical formulas to map any pixel on the chart to its exact price and temporal position. This stage combines multiple data sources to achieve complete spatiotemporal calibration.

## Input Data Sources

### 1. Price Anchors (from Stage 4B)
- **Horizontal lines with price labels** (e.g., "1.5832" @ y=Y3)
- **High confidence** price-to-y-coordinate mappings
- **No temporal information** (price only)

### 2. Detected Wicks (from Stage 4C)
- **Peak high wick:** x=X1, y=Y1 (highest detected wick)
- **Peak low wick:** x=X2, y=Y2 (lowest detected wick)
- **Exact pixel coordinates** for both x and y

### 3. Month Mapping (from Stage 4Ci)
- **Peak high column:** Time period (e.g., "May-Jun")
- **Peak low column:** Time period (e.g., "Apr-May")
- **Rough temporal context** for wick positions

### 4. OHLC Market Data
- **Real market data** for the specified time periods
- **Exact dates** for each candle
- **Exact highs/lows** for each period

## Calibration Process

### Phase 1: Price Calibration
**Goal:** Create formula `price = α*y + β`

**Method:** Linear regression using 3+ points
1. **Anchor point(s):** y=Y_anchor → price=P_anchor
2. **Wick high:** y=Y1 → price from OHLC (period high)
3. **Wick low:** y=Y2 → price from OHLC (period low)

**Output:** `price = α*y + β` where:
- α = price change per pixel (typically negative: higher y = lower price)
- β = price intercept

### Phase 2: Temporal Calibration
**Goal:** Create formula `date = γ*x + δ`

**Method:** Linear regression using 2 points
1. **Wick high:** x=X1 → exact date from OHLC (period high date)
2. **Wick low:** x=X2 → exact date from OHLC (period low date)

**Output:** `date = γ*x + δ` where:
- γ = time change per pixel (typically positive: higher x = later date)
- δ = time intercept

## Output Schema

```json
{
  "price_calibration": {
    "formula": "price = α*y + β",
    "alpha": -0.00270168,
    "beta": 2.94799934,
    "calibration_points": [
      {"y": Y_anchor, "price": P_anchor, "source": "anchor"},
      {"y": Y1, "price": P_high, "source": "wick_high"},
      {"y": Y2, "price": P_low, "source": "wick_low"}
    ]
  },
  "temporal_calibration": {
    "formula": "date = γ*x + δ",
    "gamma": 0.00012345,
    "delta": "2025-01-01T00:00:00Z",
    "calibration_points": [
      {"x": X1, "date": "2025-06-15", "source": "wick_high"},
      {"x": X2, "date": "2025-05-01", "source": "wick_low"}
    ]
  },
  "metadata": {
    "anchors_used": 1,
    "wicks_used": 2,
    "ohlc_periods": ["period1", "period2"],
    "chart_dimensions": {"width": W, "height": H}
  }
}
```

## Key Benefits

### 1. Complete Chart Mapping
- **Any pixel** → **exact price + exact date**
- **Perfect for chart rebuilding** with real market data
- **Enables advanced sonar** with temporal precision

### 2. Dual Calibration
- **Price calibration:** Maps y-coordinates to real prices
- **Temporal calibration:** Maps x-coordinates to real dates
- **Independent formulas** for maximum accuracy

### 3. Data Validation
- **Multiple data sources** cross-validate each other
- **OHLC data** confirms detected wick positions
- **Anchor points** provide high-confidence price references

## Usage in Later Stages

### Stage 5: Chart Rebuilding
- Use both formulas to overlay real prices and dates
- Create accurate price scale and time axis
- Position detected elements with real market context

### Stage 4F: Advanced Sonar
- Use temporal context for element detection
- Apply price context for validation
- Enable precision mapping with full market data

## Error Handling

### Insufficient Data
- **< 2 anchor points:** Cannot calibrate price
- **< 2 wick points:** Cannot calibrate temporal
- **Missing OHLC data:** Cannot validate wick prices

### Fallback Strategies
- **Price only:** Use anchors + estimated wick prices
- **Temporal only:** Use wick dates + estimated anchor time
- **Partial calibration:** Flag for manual review

## Dependencies
- Stage 4B: Price anchors
- Stage 4C: Wick detection
- Stage 4Ci: Month mapping
- OHLC data: Market data for validation
