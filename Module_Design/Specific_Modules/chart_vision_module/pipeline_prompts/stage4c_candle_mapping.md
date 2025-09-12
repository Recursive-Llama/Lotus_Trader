# Stage 4C: Candle Mapping (OpenCV) — Specification Note

Purpose
- Extract wick highs and lows per column using simple edge-based detection, to support price scale calibration and validation.
- This stage is deterministic OpenCV logic (no LLM). This file documents behavior and I/O to keep the pipeline aligned.

Inputs (from earlier stages)
- grid_meta: { padding, cell_width_px, cell_height_px, grid_rows=6, grid_cols=8, image_width, image_height }
- horizontals_y_px: int[] — exact y pixels for all trader‑drawn horizontals (Stage 2di)
- zone_boundaries_y_px: int[] — exact y pixels for zone top/bottom edges (Stage 2diii variants)
- arrow_cells: list — grid cells for detected arrows (Stage 2a). Used to compute stop_before_column
- column_months: mapping A..H → rough month spans (Stage 4a)
- debug flag (boolean)

Scan scope
- Columns: B → (stop_before_column − 1). If no arrows, default to B..E for this chart; configurable.
- Skip column A to avoid left margin noise.
- Temporal simplification (optional mode): every‑other‑column selection for highs/lows to reduce month granularity needs.

Detection rules
- For each column:
  - Top scan (rows 6 → 1):
    - If row == 6: skip first 150 px inside the cell; ensure the next 50 px contains NO edges; then scan remaining region.
    - Run Canny(50,150). Build disallowed set: any y within ±2 px of horizontals_y_px or zone_boundaries_y_px, and the row‑6 skip band.
    - Highest wick = single white pixel with minimal y not in disallowed set.
  - Bottom scan (rows 1 → 6):
    - If row == 1: skip last 150 px inside the cell; then scan.
    - Same exclusions. Lowest wick = single white pixel with maximal y.
- First hit per direction (top/bottom) in that column wins; then proceed to next column.

Outputs
- JSON object saved as stage4_candle_mapping.json:
  {
    "columns_scanned": ["B","C","D","E"],
    "top_wicks": { "B": {"row": 4, "x_px_abs": 259, "y_px_abs": 155}, ... },
    "bottom_wicks": { "B": {"row": 2, "x_px_abs": 106, "y_px_abs": 143}, ... },
    "debug_saved": true|false
  }
- Optional debug images (if debug=true): per cell original, edges, and marked wick images (e.g., B4_top_wick.png, B2_bottom_wick.png).

Notes
- Exclude only exact horizontal y’s and zone boundary y’s (±2 px). Do NOT exclude zone interiors wholesale.
- Dynamic stop: compute stop_before_column from the earliest arrow’s start cell column; scanning stops before that column.
- This stage provides wick coordinates for Stage 4D calibration/validation and for later overlays.


