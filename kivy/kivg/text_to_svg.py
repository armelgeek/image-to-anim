"""
Text to SVG conversion utilities for Kivg.

This module provides functionality to convert text strings to SVG path data,
enabling text animation like handwriting on a whiteboard.
"""

import os
import tempfile
from typing import List, Tuple, Optional
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen


# Default system fonts to try in order of preference
DEFAULT_FONT_PATHS = [
    # Liberation fonts (commonly available on Linux)
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    # DejaVu fonts
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    # Lato fonts
    "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
    # macOS fonts
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    # Windows fonts
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
]


def find_system_font() -> Optional[str]:
    """
    Find an available system font file.
    
    Returns:
        Path to a font file, or None if no font is found.
    """
    for font_path in DEFAULT_FONT_PATHS:
        if os.path.exists(font_path):
            return font_path
    
    # Try to find any TTF font on the system
    font_dirs = ["/usr/share/fonts", "/usr/local/share/fonts"]
    for font_dir in font_dirs:
        if os.path.exists(font_dir):
            for root, _, files in os.walk(font_dir):
                for f in files:
                    if f.endswith(".ttf") and "Color" not in f and "Emoji" not in f:
                        return os.path.join(root, f)
    
    return None


def get_glyph_path(font: TTFont, char: str) -> Tuple[str, float]:
    """
    Get the SVG path data for a single character.
    
    Args:
        font: TTFont object
        char: Single character to convert
        
    Returns:
        Tuple of (path_string, glyph_width)
    """
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    
    char_code = ord(char)
    if char_code not in cmap:
        return "", 0
    
    glyph_name = cmap[char_code]
    glyph = glyph_set[glyph_name]
    
    pen = SVGPathPen(glyph_set)
    glyph.draw(pen)
    
    path_string = pen.getCommands()
    glyph_width = glyph.width
    
    return path_string, glyph_width


def transform_path(path: str, x_offset: float, y_offset: float, 
                   scale: float = 1.0, flip_y: bool = True,
                   units_per_em: int = 2048) -> str:
    """
    Transform SVG path coordinates by offset and scale.
    
    Args:
        path: SVG path string
        x_offset: X offset to apply
        y_offset: Y offset to apply
        scale: Scale factor to apply to coordinates
        flip_y: Whether to flip Y coordinates (fonts have Y going up, SVG has Y going down)
        units_per_em: Font units per em (reserved for future use, default 2048 is common)
        
    Returns:
        Transformed path string with coordinates adjusted by offset, scale, and optionally flipped
    """
    if not path:
        return ""
    
    result = []
    i = 0
    commands = []
    current_nums = []
    current_cmd = None
    
    # Parse the path
    while i < len(path):
        char = path[i]
        
        if char.isalpha():
            if current_cmd is not None and current_nums:
                commands.append((current_cmd, current_nums))
            current_cmd = char
            current_nums = []
            i += 1
        elif char in "0123456789.-":
            # Read number
            num_start = i
            if char == '-':
                i += 1
            while i < len(path) and (path[i].isdigit() or path[i] == '.'):
                i += 1
            num_str = path[num_start:i]
            if num_str and num_str != '-':
                current_nums.append(float(num_str))
        else:
            i += 1
    
    if current_cmd is not None and current_nums:
        commands.append((current_cmd, current_nums))
    
    # Transform coordinates
    for cmd, nums in commands:
        new_nums = []
        
        if cmd in 'MmLlTt':
            # Move, Line, Smooth quadratic: x, y pairs
            for j in range(0, len(nums), 2):
                if j + 1 < len(nums):
                    x = nums[j] * scale + x_offset
                    y = nums[j + 1]
                    if flip_y:
                        y = -y * scale + y_offset
                    else:
                        y = y * scale + y_offset
                    new_nums.extend([x, y])
        elif cmd in 'HhVv':
            # Horizontal or Vertical line
            if cmd in 'Hh':
                for n in nums:
                    new_nums.append(n * scale + x_offset)
            else:
                for n in nums:
                    if flip_y:
                        new_nums.append(-n * scale + y_offset)
                    else:
                        new_nums.append(n * scale + y_offset)
        elif cmd in 'CcSs':
            # Cubic bezier or Smooth cubic: 6 values (3 x,y pairs) for C, 4 for S
            for j in range(0, len(nums), 2):
                if j + 1 < len(nums):
                    x = nums[j] * scale + x_offset
                    y = nums[j + 1]
                    if flip_y:
                        y = -y * scale + y_offset
                    else:
                        y = y * scale + y_offset
                    new_nums.extend([x, y])
        elif cmd in 'QqTt':
            # Quadratic bezier: x,y pairs
            for j in range(0, len(nums), 2):
                if j + 1 < len(nums):
                    x = nums[j] * scale + x_offset
                    y = nums[j + 1]
                    if flip_y:
                        y = -y * scale + y_offset
                    else:
                        y = y * scale + y_offset
                    new_nums.extend([x, y])
        elif cmd in 'Aa':
            # Arc: rx, ry, rotation, large-arc, sweep, x, y
            for j in range(0, len(nums), 7):
                if j + 6 < len(nums):
                    rx = nums[j] * scale
                    ry = nums[j + 1] * scale
                    rotation = nums[j + 2]
                    large_arc = nums[j + 3]
                    sweep = nums[j + 4]
                    if flip_y:
                        # Flip sweep direction: 0 becomes 1, 1 becomes 0
                        sweep = 1 if sweep == 0 else 0
                    x = nums[j + 5] * scale + x_offset
                    y = nums[j + 6]
                    if flip_y:
                        y = -y * scale + y_offset
                    else:
                        y = y * scale + y_offset
                    new_nums.extend([rx, ry, rotation, large_arc, sweep, x, y])
        elif cmd in 'Zz':
            pass  # Close path, no coordinates
        
        # Format the command with numbers
        if new_nums:
            # Format numbers with 2 decimal places, but avoid stripping trailing zeros
            # from the integer part (e.g., 100.0 should remain 100, not become 1)
            num_strs = []
            for n in new_nums:
                formatted = f"{n:.2f}"
                # Only strip trailing zeros after decimal point
                if '.' in formatted:
                    formatted = formatted.rstrip('0').rstrip('.')
                num_strs.append(formatted)
            result.append(cmd + " ".join(num_strs))
        else:
            result.append(cmd)
    
    return "".join(result)


def text_to_svg_paths(
    text: str,
    font_path: Optional[str] = None,
    font_size: float = 100.0,
    fill_color: str = "#000000",
    line_spacing: float = 1.2,
    letter_spacing: float = 0.0
) -> Tuple[str, Tuple[float, float]]:
    """
    Convert text to SVG path elements.
    
    Args:
        text: Text string to convert
        font_path: Path to TTF/OTF font file. If None, uses system default.
        font_size: Target font size in pixels
        fill_color: Fill color for the text (hex format)
        line_spacing: Line spacing multiplier
        letter_spacing: Additional spacing between letters
        
    Returns:
        Tuple of (svg_content, (width, height))
    """
    if font_path is None:
        font_path = find_system_font()
        if font_path is None:
            raise ValueError("No font file found. Please specify a font_path.")
    
    font = TTFont(font_path)
    units_per_em = font['head'].unitsPerEm
    scale = font_size / units_per_em
    
    # Calculate dimensions
    ascender = font['hhea'].ascender * scale
    descender = font['hhea'].descender * scale
    line_height = font_size * line_spacing
    
    paths = []
    lines = text.split('\n')
    
    max_width = 0
    current_y = ascender  # Start from top
    
    for line_idx, line in enumerate(lines):
        current_x = 0
        non_space_char_idx = 0  # Counter for non-space characters only
        
        for char in line:
            if char == ' ':
                # Get space width
                glyph_set = font.getGlyphSet()
                cmap = font.getBestCmap()
                if ord(' ') in cmap:
                    space_name = cmap[ord(' ')]
                    current_x += glyph_set[space_name].width * scale + letter_spacing
                else:
                    current_x += font_size * 0.25 + letter_spacing
                continue
            
            path_str, glyph_width = get_glyph_path(font, char)
            
            if path_str:
                # Transform the path
                transformed = transform_path(
                    path_str,
                    x_offset=current_x,
                    y_offset=current_y,
                    scale=scale,
                    flip_y=True,
                    units_per_em=units_per_em
                )
                
                # Use non_space_char_idx to match animation config IDs
                char_id = f"char_{line_idx}_{non_space_char_idx}"
                paths.append(f'<path fill="{fill_color}" id="{char_id}" d="{transformed}"/>')
            
            non_space_char_idx += 1
            current_x += glyph_width * scale + letter_spacing
        
        max_width = max(max_width, current_x)
        current_y += line_height
    
    total_height = current_y - line_height + abs(descender)
    
    # Create SVG content
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {max_width:.2f} {total_height:.2f}" width="{max_width:.2f}" height="{total_height:.2f}">
<g id="text_content">
{"".join(paths)}
</g>
</svg>'''
    
    font.close()
    return svg_content, (max_width, total_height)


def text_to_svg_file(
    text: str,
    output_path: str,
    font_path: Optional[str] = None,
    font_size: float = 100.0,
    fill_color: str = "#000000",
    line_spacing: float = 1.2,
    letter_spacing: float = 0.0
) -> Tuple[float, float]:
    """
    Convert text to an SVG file.
    
    Args:
        text: Text string to convert
        output_path: Path to save the SVG file
        font_path: Path to TTF/OTF font file. If None, uses system default.
        font_size: Target font size in pixels
        fill_color: Fill color for the text (hex format)
        line_spacing: Line spacing multiplier
        letter_spacing: Additional spacing between letters
        
    Returns:
        Tuple of (width, height) of the generated SVG
    """
    svg_content, dimensions = text_to_svg_paths(
        text, font_path, font_size, fill_color, line_spacing, letter_spacing
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    
    return dimensions


def create_text_svg_temp(
    text: str,
    font_path: Optional[str] = None,
    font_size: float = 100.0,
    fill_color: str = "#000000"
) -> str:
    """
    Create a temporary SVG file from text.
    
    Args:
        text: Text string to convert
        font_path: Path to TTF/OTF font file
        font_size: Target font size in pixels
        fill_color: Fill color for the text (hex format)
        
    Returns:
        Path to the temporary SVG file
    """
    fd, temp_path = tempfile.mkstemp(suffix='.svg')
    os.close(fd)
    
    text_to_svg_file(text, temp_path, font_path, font_size, fill_color)
    
    return temp_path


def get_text_animation_config(
    text: str,
    animation_type: str = "sequential",
    duration_per_char: float = 0.1,
    transition: str = "out_sine"
) -> List[dict]:
    """
    Generate animation configuration for text.
    
    This creates a configuration list suitable for use with Kivg.shape_animate()
    to animate each character appearing in sequence.
    
    Args:
        text: Text string that was converted to SVG
        animation_type: Type of animation ("sequential", "from_left", "from_right", 
                       "from_top", "from_bottom", "from_center")
        duration_per_char: Duration of animation per character
        transition: Kivy animation transition type
        
    Returns:
        List of animation configuration dictionaries
    """
    config = []
    
    direction_map = {
        "sequential": None,
        "from_left": "left",
        "from_right": "right",
        "from_top": "top",
        "from_bottom": "bottom",
        "from_center_x": "center_x",
        "from_center_y": "center_y",
    }
    
    direction = direction_map.get(animation_type, None)
    
    lines = text.split('\n')
    for line_idx, line in enumerate(lines):
        char_idx = 0
        for char in line:
            if char != ' ':
                char_id = f"char_{line_idx}_{char_idx}"
                config.append({
                    "id_": char_id,
                    "from_": direction,
                    "t": transition,
                    "d": duration_per_char
                })
                char_idx += 1
    
    return config
