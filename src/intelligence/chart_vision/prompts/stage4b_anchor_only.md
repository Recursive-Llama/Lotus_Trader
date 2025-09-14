# Stage 4: Horizontal Anchor Tags (Full Image)

You will receive the full chart image with an 8×6 grid overlay (cells like A1..H6). Read only what is clearly printed.

Task:
- Find obvious price tags printed on trader‑drawn horizontal lines (e.g., black/colored horizontals with a numeric tag).
- For each tag, return the price text as printed and the grid line (just the number) (1..6) at the tag location.

Rules:
- Copy tag text exactly (preserve decimal separator and decimal places). Do not invent values.
- Return only anchors attached to drawn horizontals; ignore axis tick labels.
- Order top → bottom. If none exist, set anchors_count to 0.

Output (plain text):
anchors_count: <M>
anchor_1_text: <TEXT|optional>
anchor_1_grid_line: <1..6|optional>
anchor_2_text: <TEXT|optional>
anchor_2_grid_line: <1..6|optional>
anchor_3_text: <TEXT|optional>
anchor_3_grid_line: <1..6|optional>
notes: <one short sentence>
