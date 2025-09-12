# Stage 2di: OpenCV Detection - Horizontal Lines Only

## Task
Use OpenCV techniques to precisely locate and map trader-drawn horizontal lines to exact coordinates.

## Input
- **Original chart image**
- **Element info packs** from Stage 1 (horizontal lines only)
- **Grid mapping results** from Stage 2A (horizontal lines with row information)

## OpenCV Detection Strategy

### Horizontal Lines
- **Technique**: Canny Edge Detection + Hough Line Transform
- **Focus**: Find exact Y-coordinates for price levels
- **Processing**: Row-based extraction with adaptive thresholds
- **Output**: Precise pixel coordinates converted to price levels

## Output Format
```json
{
  "opencv_detection_results": {
    "horizontal_lines": [
      {
        "element_id": "ELEMENT_01",
        "opencv_technique": "canny_edge_hough",
        "detection_params": {
          "canny_low": 50,
          "canny_high": 150,
          "hough_threshold": 800,
          "min_separation": 10
        },
        "coordinates": {
          "y_pixel": 156,
          "price_level": 0.4567,
          "confidence": 0.92
        }
      }
    ],
    "summary": {
      "total_detected": 2,
      "opencv_success_rate": 1.0,
      "technique_used": "canny_edge_hough"
    }
  }
}
```

## Important Notes
- **Coordinate System**: Convert row-based positions back to main chart coordinates
- **Confidence Scoring**: Rate detection accuracy (0.0-1.0)
- **Row Processing**: Group horizontal lines by row for efficient detection
- **Adaptive Thresholds**: Cycle through thresholds (800, 700, 600, 500, 400, 300) until lines found
- **Minimum Separation**: Filter out duplicate detections (top/bottom edges of same line)
