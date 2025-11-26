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
- Works with image files (PNG, JPG, JPEG, WEBP)
- Best for sharing and offline playback

### SVG Live Mode
- Real-time SVG animation rendered directly in the app
- Uses the kivg library for SVG tracking and animation
- Animated drawing hand that follows the sketch path
- Smooth vector-based animation
- **Supports both:**
  - Converting images to SVG and animating them
  - Uploading pre-made SVG files directly
- No video file generation required
- Best for live demonstrations and interactive presentations

## How It Works

### Option 1: Upload an Image File
1. The image is converted to grayscale and thresholded (same as video mode)
2. The image is divided into a grid based on the selected speed
3. The algorithm traces black pixels using nearest-neighbor pathfinding
4. The traced path is converted to SVG format with proper viewBox and path elements
5. kivg renders and animates the SVG in real-time

### Option 2: Upload an SVG File Directly ✨ NEW!
1. Upload any SVG file (.svg extension)
2. The app automatically switches to SVG Live mode
3. kivg parses and animates the SVG paths
4. No image processing needed - instant animation!

### Algorithm Consistency
For image-based generation, both Video and SVG modes use the same core algorithm from `sketchApi.py`:
- Same image preprocessing (adaptive thresholding)
- Same grid-based pixel tracing
- Same Euclidean distance calculation for path optimization
- This ensures consistent sketch quality across both modes

## Usage

### Uploading Files
1. Click the "Upload" button
2. Select either:
   - **Image file** (.png, .jpg, .jpeg, .webp) for sketch generation
   - **SVG file** (.svg) for direct animation
3. The app will automatically detect the file type

### Selecting Animation Mode
- **For Images**: Choose between Video or SVG Live mode
- **For SVG Files**: Automatically switches to SVG Live mode (only mode compatible with SVG)

### Parameters
Both modes share the same parameters when using images:
- **Video Speed**: Controls the grid size for tracing (smaller = more detail, slower)
  - *Not applicable for uploaded SVG files*
- **Frame Rate**: Only used in Video mode (fps of output video)
- **Object Skip Rate**: Controls drawing speed in Video mode
- **Background Skip Rate**: Controls background drawing speed in Video mode  
- **Main Image Duration**: Duration to show final image in Video mode (seconds)

### SVG Live Mode Specific Features
- Animated hand cursor that follows the drawing path
- Real-time SVG rendering using Kivy graphics
- Smooth vector-based animation
- Fill animation after path drawing completes
- Support for uploaded SVG files with multiple paths

## SVG File Requirements

### Compatible SVG Files
Your SVG files should:
- Have a valid SVG structure with `<svg>` root element
- Include `viewBox` attribute for proper scaling
- Contain `<path>` elements with `d` attribute (path data)
- Use standard SVG path commands (M, L, C, Z, etc.)

### Example SVG Structure
```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
  <path id="shape1" d="M 50,50 L 150,50 L 150,150 Z" 
        stroke="#000000" stroke-width="2" fill="#FF0000"/>
  <path id="shape2" d="M 200,200 L 300,200 L 250,300 Z" 
        stroke="#0000FF" stroke-width="2" fill="none"/>
</svg>
```

## Technical Details

### Integration with kivg
The SVG Live mode leverages the kivg library capabilities:
- **SVG Parser**: Parses both generated and uploaded SVG files
- **Path Renderer**: Renders SVG paths on Kivy canvas
- **Animation Handler**: Manages sequential or parallel animations
- **Pen Tracker**: Shows animated hand following the drawing path
- **Mesh Renderer**: Fills shapes after drawing

### Files Modified/Added
1. `svgGenerator.py` - New module for SVG generation from images
2. `sketchApi.py` - Added `generate_svg_from_image_sketch()` function
3. `main.py` - Added SVG animation mode support and SVG file upload handling
4. `main_layout.kv` - Added segmented control for mode selection

### SVG Format
Generated SVG files include:
- Proper XML declaration
- SVG element with viewBox matching image dimensions
- Single path element with all traced points
- Stroke styling (color, width, line caps)
- Compatible with kivg's SVG parser

Uploaded SVG files should follow standard SVG specification with path elements.

## Benefits

### Why SVG Live Mode?
- **Interactive**: Real-time animation without waiting for video encoding
- **Scalable**: Vector-based, looks crisp at any zoom level
- **Lightweight**: No video file generation or storage
- **Educational**: Great for demonstrations and teaching
- **kivg Integration**: Leverages powerful SVG animation library
- **Flexible**: Works with both images and pre-made SVG files

### Why Video Mode?
- **Shareable**: Easy to share video files
- **Offline Playback**: Works on any video player
- **Mobile Compatible**: APK can be installed on Android devices
- **Proven**: Existing, battle-tested feature

## Use Cases

### Image to SVG Animation
- Educational content creation
- Sketch-style presentations
- Whiteboard-style animations
- Tutorial videos

### Direct SVG Upload and Animation
- Logo animations
- Icon animations
- Hand-drawn illustrations
- Design presentations
- Interactive art displays

## Future Enhancements
Potential improvements for SVG mode:
- Export animated SVG file for web use
- Save generated SVG files from images
- Customize hand image and pen position
- Adjust animation speed and timing
- Multiple color support
- Object masking for selective animation
