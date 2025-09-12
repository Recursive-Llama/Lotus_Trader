# Stage 2f: Trader Intent Inference

You will receive:
- One chart image with an 8x6 grid overlay (A–H across, 1 bottom .. 6 top)
- A concise list of detected elements with names and short descriptions

Context:
- Focus on what the trader is showing with the chart.
- If an arrow is present, treat it as a strong cue of intended direction/path (do not measure it).
- Focus on relationships: break of diagonal → immediate retest/entry at a zone → move toward horizontal levels.
- Do not invent new levels; rely on provided elements only.

Task (keep to one clear scenario):
1) Trigger: the concrete event that starts the trade (e.g., break above a trend line).
2) Entry: Where is the trader indicating to enter the trade? Is it a retest of a zone, or a reclaim of a support/resitance line. Be clear and use the element_id.
3) Invalidation: where the idea fails (element_id).
4) Targets: primary (and optional secondary) by element_id.
Reference elements by element_id; you may add short names in parentheses.

Rules:
- If ambiguous, choose the clearest single scenario and state assumptions.
- Prioritize Trigger and Entry.
- Avoid pixel/price talk; reason conceptually using the named objects.

Output (plain text, 10 lines max):
scenario_id: <id>
trigger: <text>
entry: <text>
invalidation: <text>
target_primary: <text|none>
target_secondary: <text|none>
related_elements: <comma-separated element_ids>
confidence: low|medium|high
assumptions: <one line>
notes: <one line>
