"""
SVG Generator for converting image sketch to SVG paths
This module creates SVG files from the sketch drawing process
"""
import os
import numpy as np
import cv2
import xml.etree.ElementTree as ET
from xml.dom import minidom


def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def trace_image_to_svg_paths(img_thresh, resize_wd, resize_ht, split_len, object_mask=None, stroke_color="#000000", stroke_width=2):
    """
    Convert the thresholded image to SVG paths by tracing the black pixels.
    
    Args:
        img_thresh: Thresholded grayscale image
        resize_wd: Width of the resized image
        resize_ht: Height of the resized image
        split_len: Grid size for splitting the image
        object_mask: Optional mask for object-only drawing
        stroke_color: Color for the SVG strokes
        stroke_width: Width of the SVG strokes
        
    Returns:
        List of SVG path commands
    """
    img_thresh_copy = img_thresh.copy()
    
    if object_mask is not None:
        # Make area other than object white
        object_mask_black_ind = np.where(object_mask == 0)
        img_thresh_copy[object_mask_black_ind] = 255
    
    # Cut the image into grids
    n_cuts_vertical = int(np.ceil(resize_ht / split_len))
    n_cuts_horizontal = int(np.ceil(resize_wd / split_len))
    
    grid_of_cuts = np.array(np.split(img_thresh_copy, n_cuts_horizontal, axis=-1))
    grid_of_cuts = np.array(np.split(grid_of_cuts, n_cuts_vertical, axis=-2))
    
    # Find grids where there is at least one black pixel
    black_pixel_threshold = 10
    cut_having_black = (grid_of_cuts < black_pixel_threshold) * 1
    cut_having_black = np.sum(np.sum(cut_having_black, axis=-1), axis=-1)
    cut_black_indices = np.array(np.where(cut_having_black > 0)).T
    
    # Create path points by following the nearest neighbor
    path_points = []
    if len(cut_black_indices) > 0:
        visited = set()
        current_idx = 0
        
        while len(visited) < len(cut_black_indices):
            if current_idx in visited:
                # Find next unvisited point
                for i in range(len(cut_black_indices)):
                    if i not in visited:
                        current_idx = i
                        break
                else:
                    break
            
            visited.add(current_idx)
            point = cut_black_indices[current_idx]
            
            # Convert grid coordinates to pixel coordinates (center of grid)
            x = point[1] * split_len + split_len // 2
            y = point[0] * split_len + split_len // 2
            path_points.append((x, y))
            
            # Find nearest unvisited neighbor
            if len(visited) < len(cut_black_indices):
                unvisited_indices = [i for i in range(len(cut_black_indices)) if i not in visited]
                if unvisited_indices:
                    unvisited_points = cut_black_indices[unvisited_indices]
                    distances = np.sqrt(np.sum((unvisited_points - point) ** 2, axis=1))
                    nearest_idx = unvisited_indices[np.argmin(distances)]
                    current_idx = nearest_idx
    
    return path_points


def create_svg_from_paths(path_points, width, height, stroke_color="#000000", stroke_width=2, fill_color="none"):
    """
    Create an SVG element from path points.
    
    Args:
        path_points: List of (x, y) tuples representing the path
        width: SVG width
        height: SVG height
        stroke_color: Color for the path stroke
        stroke_width: Width of the path stroke
        fill_color: Fill color for the path
        
    Returns:
        SVG string
    """
    # Create SVG root element
    svg = ET.Element('svg', {
        'xmlns': 'http://www.w3.org/2000/svg',
        'width': str(width),
        'height': str(height),
        'viewBox': f'0 0 {width} {height}'
    })
    
    if len(path_points) == 0:
        return prettify_xml(svg)
    
    # Create path data
    path_data = []
    
    # Start with first point
    if len(path_points) > 0:
        path_data.append(f'M {path_points[0][0]},{path_points[0][1]}')
        
        # Add line segments
        for i in range(1, len(path_points)):
            x, y = path_points[i]
            path_data.append(f'L {x},{y}')
    
    # Create path element
    if path_data:
        path_string = ' '.join(path_data)
        path_elem = ET.SubElement(svg, 'path', {
            'd': path_string,
            'stroke': stroke_color,
            'stroke-width': str(stroke_width),
            'fill': fill_color,
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round'
        })
    
    return prettify_xml(svg)


def generate_svg_from_image(image_bgr, split_len=10, stroke_color="#000000", stroke_width=2, resize_wd=640, resize_ht=480):
    """
    Generate an SVG file from an image by converting it to a sketch-like path.
    
    Args:
        image_bgr: Input image in BGR format
        split_len: Grid size for tracing
        stroke_color: Color for the SVG strokes
        stroke_width: Width of the SVG strokes
        resize_wd: Target width for processing
        resize_ht: Target height for processing
        
    Returns:
        SVG string
    """
    # Resize image
    img = cv2.resize(image_bgr, (resize_wd, resize_ht))
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding
    img_thresh = cv2.adaptiveThreshold(
        img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10
    )
    
    # Trace the image to SVG paths
    path_points = trace_image_to_svg_paths(
        img_thresh, resize_wd, resize_ht, split_len, 
        object_mask=None, stroke_color=stroke_color, stroke_width=stroke_width
    )
    
    # Create SVG
    svg_string = create_svg_from_paths(
        path_points, resize_wd, resize_ht, 
        stroke_color=stroke_color, stroke_width=stroke_width
    )
    
    return svg_string


def save_svg_file(svg_string, output_path):
    """
    Save SVG string to a file.
    
    Args:
        svg_string: The SVG content as a string
        output_path: Path where the SVG file should be saved
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_string)
