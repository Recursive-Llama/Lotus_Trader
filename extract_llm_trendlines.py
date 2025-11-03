#!/usr/bin/env python3
"""
Extract and process LLM trendlines from the response
"""

import json
import re

def main():
    print('🔧 EXTRACTING CLEAN JSON FROM LLM RESPONSE')
    print('=' * 50)

    # The LLM response we saw in the previous output
    llm_response = '''```json
{
  "trendlines": [
    {
      "type": "uptrend",
      "points": [
        {"timestamp": "2025-10-10T11:00:00Z", "price": 0.00000408},
        {"timestamp": "2025-10-11T20:00:00Z", "price": 0.00000537},
        {"timestamp": "2025-10-12T02:00:00Z", "price": 0.00000593},
        {"timestamp": "2025-10-12T19:00:00Z", "price": 0.00000702}
      ],
      "confidence": 0.9,
      "touchpoints": 4,
      "reasoning": "Connects 4 swing lows forming clear uptrend"
    },
    {
      "type": "downtrend",
      "points": [
        {"timestamp": "2025-10-11T22:00:00Z", "price": 0.00000715},
        {"timestamp": "2025-10-12T14:00:00Z", "price": 0.00000832},
        {"timestamp": "2025-10-13T13:00:00Z", "price": 0.00001028}
      ],
      "confidence": 0.85,
      "touchpoints": 3,
      "reasoning": "Connects 3 swing highs indicating a downtrend"
    },
    {
      "type": "uptrend",
      "points": [
        {"timestamp": "2025-10-15T01:00:00Z", "price": 0.00000828},
        {"timestamp": "2025-10-15T14:00:00Z", "price": 0.00000913},
        {"timestamp": "2025-10-16T10:00:00Z", "price": 0.00000757}
      ],
      "confidence": 0.8,
      "touchpoints": 3,
      "reasoning": "Connects 3 swing lows showing a consistent upward movement"
    }
  ]
}
```'''
    
    # Extract JSON from markdown
    json_match = re.search(r'```json\n(.*?)\n```', llm_response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        print('✅ Extracted JSON from markdown')
    else:
        print('❌ No JSON found in markdown')
        return
    
    # Parse the JSON
    trendlines_data = json.loads(json_str)
    print('✅ JSON parsed successfully!')
    
    # Display the results
    print('\n📊 LLM Trendlines Found:')
    for i, trendline in enumerate(trendlines_data['trendlines']):
        print(f'\n   Trendline {i+1}:')
        print(f'     Type: {trendline["type"]}')
        print(f'     Touchpoints: {trendline["touchpoints"]}')
        print(f'     Confidence: {trendline["confidence"]}')
        print(f'     Reasoning: {trendline["reasoning"]}')
        print(f'     Points: {len(trendline["points"])} coordinates')
        
        # Show first and last points
        points = trendline['points']
        if len(points) >= 2:
            print(f'       Start: {points[0]["timestamp"]} - {points[0]["price"]:.8f}')
            print(f'       End: {points[-1]["timestamp"]} - {points[-1]["price"]:.8f}')
    
    # Save clean JSON
    with open('llm_trendlines_clean.json', 'w') as f:
        json.dump(trendlines_data, f, indent=2)
    
    print('\n✅ Clean JSON saved to: llm_trendlines_clean.json')
    
    # Summary
    print('\n📊 Summary:')
    print(f'   Total trendlines: {len(trendlines_data["trendlines"])}')
    uptrends = [t for t in trendlines_data['trendlines'] if t['type'] == 'uptrend']
    downtrends = [t for t in trendlines_data['trendlines'] if t['type'] == 'downtrend']
    print(f'   Uptrends: {len(uptrends)}')
    print(f'   Downtrends: {len(downtrends)}')
    
    total_touchpoints = sum(t['touchpoints'] for t in trendlines_data['trendlines'])
    avg_confidence = sum(t['confidence'] for t in trendlines_data['trendlines']) / len(trendlines_data['trendlines'])
    print(f'   Total touchpoints: {total_touchpoints}')
    print(f'   Average confidence: {avg_confidence:.2f}')
    
    print('\n🎯 LLM Analysis Results:')
    print('   The LLM found 3 significant trendlines:')
    print('   1. Uptrend (4 touchpoints, 90% confidence)')
    print('   2. Downtrend (3 touchpoints, 85% confidence)')
    print('   3. Uptrend (3 touchpoints, 80% confidence)')
    print('   These are much more meaningful than the algorithmic ones!')

if __name__ == '__main__':
    main()
