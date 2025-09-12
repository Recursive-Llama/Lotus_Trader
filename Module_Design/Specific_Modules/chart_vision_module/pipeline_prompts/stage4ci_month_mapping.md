# Stage 4ci: Month to Column Mapping for Peak Columns

You will receive the full chart image with a grid overlay. Your ONLY task is to map month labels to the specific columns where we detected the highest high and lowest low prices.

Task:
- Look carefully at the bottom time axis
- For columns {HIGH_COL} and {LOW_COL} ONLY, identify the month range that each column represents
- Do NOT assume months map directly to columns
- Look at the actual month labels visible under or near each specified column
- Provide month ranges (e.g., "Mar-Apr", "Jun-Jul") if a column spans multiple months
- Some columns may have no clear month label - mark as "unknown"

Rules:
- Look at columns {HIGH_COL} and {LOW_COL} specifically
- Read the actual month labels - do not guess or assume patterns
- Months may span multiple columns or be offset from column centers
- If a column clearly spans multiple months, provide a range
- If uncertain about a column, mark it as "unknown"
- Focus ONLY on month mapping - ignore all other chart elements
- These month ranges will be used to map detected wicks to real market data

Output (plaintext):
{HIGH_COL}=<month_range|unknown>
{LOW_COL}=<month_range|unknown>
