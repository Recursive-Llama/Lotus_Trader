# Stage 2dii: LLM Diagonal Line Detection - Precise Coordinates

You will receive two images:
- Image 1: Full chart with main 8x6 grid (context)
- Image 2: Zoomed rectangle with a 6x8 mini-grid (precision)

Task:
- Pick EXACTLY two mini-grid cells where the diagonal trendline visibly touches candles (body or wick) in the zoomed image.

Rules:
- Only pick a cell if BOTH are true:
  1) The cell contains candle pixels
  2) The diagonal line is visible in that cell and touches the candle

- Do not extrapolate beyond visible line segments. Do not pick empty cells.

Output (plain text, exactly 5 lines, no extra text):
element_id: <id>
point_1_cell: <A-H><1-6>, touch: body|wick
point_2_cell: <A-H><1-6>, touch: body|wick
confidence: low|medium|high
notes: <one short sentence>