# SVG Animation Mode

## Overview
The application now includes two animation modes:
1. **Video Mode** - Traditional video-based sketch animation (existing feature)
2. **SVG Live Mode** - Real-time SVG animation using kivg library (new feature)

## Features

### Video Mode
- Generates a video file (.mp4 or .avi) with sketch animation
- Uses OpenCV and FFmpeg for video generation
- Supports downloading the video file
- Best for sharing and offline playback

### SVG Live Mode
- Real-time SVG animation rendered directly in the app
- Uses the kivg library for SVG tracking and animation
- Animated drawing hand that follows the sketch path
- Smooth vector-based animation
- No video file generation required
- Best for live demonstrations and interactive presentations

## How It Works

### SVG Generation Process
1. The image is converted to grayscale and thresholded (same as video mode)
2. The image is divided into a grid based on the selected speed
3. The algorithm traces black pixels using nearest-neighbor pathfinding
4. The traced path is converted to SVG format with proper viewBox and path elements
5. kivg renders and animates the SVG in real-time

### Algorithm Consistency
Both modes use the same core algorithm from `sketchApi.py`:
- Same image preprocessing (adaptive thresholding)
- Same grid-based pixel tracing
- Same Euclidean distance calculation for path optimization
- This ensures consistent sketch quality across both modes

## Usage

### Selecting Animation Mode
1. Open the application
2. Select an image using the "Upload" button
3. Choose the animation mode from the segmented control:
   - **Video**: Generates a downloadable video file
   - **SVG Live**: Shows animated SVG in the app

### Parameters
Both modes share the same parameters:
- **Video Speed**: Controls the grid size for tracing (smaller = more detail, slower)
- **Frame Rate**: Only used in Video mode (fps of output video)
- **Object Skip Rate**: Controls drawing speed in Video mode
- **Background Skip Rate**: Controls background drawing speed in Video mode  
- **Main Image Duration**: Duration to show final image in Video mode (seconds)

### SVG Live Mode Specific Features
- Animated hand cursor that follows the drawing path
- Real-time SVG rendering using Kivy graphics
- Smooth vector-based animation
- Fill animation after path drawing completes

## Technical Details

### Integration with kivg
The SVG Live mode leverages the kivg library capabilities:
- **SVG Parser**: Parses generated SVG files
- **Path Renderer**: Renders SVG paths on Kivy canvas
- **Animation Handler**: Manages sequential or parallel animations
- **Pen Tracker**: Shows animated hand following the drawing path
- **Mesh Renderer**: Fills shapes after drawing

### Files Modified/Added
1. `svgGenerator.py` - New module for SVG generation
2. `sketchApi.py` - Added `generate_svg_from_image_sketch()` function
3. `main.py` - Added SVG animation mode support
4. `main_layout.kv` - Added segmented control for mode selection

### SVG Format
Generated SVG files include:
- Proper XML declaration
- SVG element with viewBox matching image dimensions
- Single path element with all traced points
- Stroke styling (color, width, line caps)
- Compatible with kivg's SVG parser

## Benefits

### Why SVG Live Mode?
- **Interactive**: Real-time animation without waiting for video encoding
- **Scalable**: Vector-based, looks crisp at any zoom level
- **Lightweight**: No video file generation or storage
- **Educational**: Great for demonstrations and teaching
- **kivg Integration**: Leverages powerful SVG animation library

### Why Video Mode?
- **Shareable**: Easy to share video files
- **Offline Playback**: Works on any video player
- **Mobile Compatible**: APK can be installed on Android devices
- **Proven**: Existing, battle-tested feature

## Future Enhancements
Potential improvements for SVG mode:
- Export SVG file for external use
- Customize hand image and pen position
- Adjust animation speed and timing
- Multiple color support
- Object masking for selective animation
