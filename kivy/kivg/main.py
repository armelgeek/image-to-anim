"""
Kivg - SVG drawing and animation for Kivy
Core class and main API
"""

import os
import tempfile
from collections import OrderedDict
from typing import List, Tuple, Dict, Any, Callable, Optional

from kivg.animation.kivy_animation import Animation
from kivg.drawing.manager import DrawingManager
from kivg.animation.handler import AnimationHandler
from kivg.mesh_handler import MeshHandler
from kivg.svg_renderer import SvgRenderer
from kivg.drawing.pen_tracker import PenTracker
from kivg.text_to_svg import (
    text_to_svg_file,
    get_text_animation_config,
    find_system_font
)


class Kivg:
    """
    Main class for rendering and animating SVG files in Kivy applications.
    
    This class provides methods to draw SVG files onto Kivy widgets and
    animate them using various techniques.
    """

    def __init__(self, widget: Any, *args):
        """
        Initialize the Kivg renderer.
        
        Args:
            widget: Kivy widget to draw SVG upon
            *args: Additional arguments (not currently used)
        """
        self.widget = widget  # Target widget for rendering
        self._fill = True  # Fill path with color after drawing
        self._line_width = 2
        self._line_color = [0, 0, 0, 1]
        self._animation_duration = 0.02
        self._previous_svg_file = ""  # Cache previous SVG file
        
        # Animation state
        self.path = []
        self.closed_shapes = OrderedDict()
        self.svg_size = []
        self.current_svg_file = ""
        
        # Shape animation state
        self.all_anim = []
        self.curr_count = 0
        self.prev_shapes = []
        self.curr_shape = []
        
        # Pen tracking state
        self._pen_tracker: Optional[PenTracker] = None
        self._show_hand = False
        self._current_pen_pos: Optional[Tuple[float, float]] = None  # Store current pen position
        
        # Temporary file management for text rendering
        self._temp_text_svg: Optional[str] = None

    def _cleanup_temp_svg(self) -> None:
        """Clean up temporary SVG file if it exists."""
        if self._temp_text_svg and os.path.exists(self._temp_text_svg):
            try:
                os.unlink(self._temp_text_svg)
            except OSError:
                pass  # Ignore cleanup errors
            self._temp_text_svg = None

    def fill_up(self, shapes: List[List[float]], color: List[float]) -> None:
        """
        Fill shapes with specified color using mesh rendering.
        
        Args:
            shapes: List of shape point lists to fill
            color: RGB or RGBA color to fill with
        """
        MeshHandler.render_mesh(self.widget, shapes, color, "mesh_opacity")

    def fill_up_shapes(self, *args) -> None:
        """Fill all shapes in the current SVG file.
        
        Clears the canvas first to remove stroke lines from the drawing animation,
        then renders filled shapes.
        """
        self.widget.canvas.clear()
        for id_, closed_paths in self.closed_shapes.items():
            color = self.closed_shapes[id_]["color"]
            self.fill_up(closed_paths[id_ + "shapes"], color)
    
    def fill_up_shapes_anim(self, shapes: List[Tuple[List[float], List[float]]], *args) -> None:
        """Fill shapes during animation."""
        for shape in shapes:
            color = shape[0]
            self.fill_up([shape[1]], color)
    
    def anim_on_comp(self, *args) -> None:
        """Handle completion of an animation in the sequence."""
        self.curr_count += 1
        self.prev_shapes.append(self.curr_shape)
        
        if self.curr_count < len(self.all_anim):
            id_, animation = self.all_anim[self.curr_count]
            setattr(self, "curr_id", id_)
            setattr(self, "curr_clr", self.closed_shapes[id_]["color"])
            
            # Clear previous bindings and add new ones
            animation.unbind(on_progress=self.track_progress)
            animation.unbind(on_complete=self.anim_on_comp)
            
            animation.bind(on_progress=self.track_progress)
            animation.bind(on_complete=self.anim_on_comp)
            
            animation.start(self.widget)
    
    def track_progress(self, *args) -> None:
        """
        Track animation progress and update the canvas.
        
        Called during animation progress. Updates the current shape.
        """
        id_ = getattr(self, "curr_id")
        elements_list = getattr(self, f"{id_}_tmp")

        shape_list = SvgRenderer.collect_shape_points(elements_list, self.widget, id_)
        
        self.widget.canvas.clear()
        self.curr_shape = (getattr(self, "curr_clr"), shape_list)
        shapes = [*self.prev_shapes, self.curr_shape]
        self.fill_up_shapes_anim(shapes)

    def update_canvas(self, *args, **kwargs) -> None:
        """Update the canvas with the current drawing state."""
        SvgRenderer.update_canvas(self.widget, self.path, self._line_color)
        
        # Update and store current pen position
        pen_pos = SvgRenderer.get_current_pen_position(self.widget, self.path)
        if pen_pos:
            self._current_pen_pos = pen_pos
        
        # Update pen tracker position if active
        if self._pen_tracker and self._pen_tracker.is_active and self._current_pen_pos:
            self._pen_tracker.update_position(*self._current_pen_pos)
    
    def _on_draw_complete(self, *args) -> None:
        """Handle completion of draw animation."""
        # Slide out the hand with animation instead of stopping immediately
        if self._pen_tracker:
            self._pen_tracker.slide_out(on_complete=self._on_hand_slide_complete)
        else:
            self._current_pen_pos = None
    
    def _on_hand_slide_complete(self) -> None:
        """Handle completion of hand slide-out animation."""
        self._current_pen_pos = None

    def draw(self, svg_file: str, animate: bool = False, 
             anim_type: str = "seq", *args, **kwargs) -> None:
        """
        Draw an SVG file onto the widget with optional animation.
        
        Args:
            svg_file: Path to the SVG file
            animate: Whether to animate the drawing process
            anim_type: Animation type - "seq" for sequential or "par" for parallel
            
        Keyword Args:
            fill: Whether to fill the drawing (bool)
            line_width: Width of lines (int)
            line_color: Color of lines (list)
            dur: Duration of each animation step (float)
            from_shape_anim: Whether called from shape_animate (bool)
            show_hand: Whether to show a hand image following the pen (bool)
            hand_image: Path to custom hand image file (str)
            hand_size: Size of hand image as (width, height) tuple
            pen_offset: Offset of pen tip in hand image as (x, y) tuple
        """
        # Process arguments
        fill = kwargs.get("fill", self._fill)
        line_width = kwargs.get("line_width", self._line_width)
        line_color = kwargs.get("line_color", self._line_color)
        duration = kwargs.get("dur", self._animation_duration)
        from_shape_anim = kwargs.get("from_shape_anim", False)
        anim_type = anim_type if anim_type in ("seq", "par") else "seq"
        
        # Pen tracking options
        show_hand = kwargs.get("show_hand", False)
        hand_image = kwargs.get("hand_image", None)
        hand_size = kwargs.get("hand_size", (100, 100))
        pen_offset = kwargs.get("pen_offset", (10, 85))
        
        # Set current values as instance attributes for other methods to access
        self._fill = fill
        self._line_width = line_width
        self._line_color = line_color
        self._animation_duration = duration
        self.current_svg_file = svg_file
        self._show_hand = show_hand and animate  # Only show hand when animating
        
        # Initialize pen tracker if needed
        if self._show_hand:
            self._pen_tracker = PenTracker(
                self.widget, 
                hand_image=hand_image,
                hand_size=hand_size,
                pen_offset=pen_offset
            )
            self._pen_tracker.start()
        else:
            if self._pen_tracker:
                self._pen_tracker.stop()
            self._pen_tracker = None
        
        # Only process SVG if it's different from the previous one
        if svg_file != self._previous_svg_file:
            self.svg_size, self.closed_shapes, self.path = DrawingManager.process_path_data(svg_file)
            self._previous_svg_file = svg_file
        
        # Calculate the paths and get animation list
        anim_list = DrawingManager.calculate_paths(
            self.widget, self.closed_shapes, self.svg_size, 
            svg_file, animate, line_width, duration
        )
        
        # Handle animation and rendering
        if not from_shape_anim:
            if animate:
                # Combine animations according to anim_type
                draw_anim = AnimationHandler.create_animation_sequence(
                    anim_list, sequential=(anim_type == "seq")
                )
                
                # Bind update_canvas only to drawing animation progress
                draw_anim.bind(on_progress=self.update_canvas)
                
                # Add fill animation if needed
                if fill:
                    setattr(self.widget, "mesh_opacity", 0)
                    # Create fill animation and bind fill_up_shapes to its progress
                    fill_anim = Animation(d=0.4, mesh_opacity=1)
                    fill_anim.bind(on_progress=self.fill_up_shapes)
                    # Chain drawing animation with fill animation
                    anim = draw_anim + fill_anim
                else:
                    anim = draw_anim
                
                # Cancel any existing animations and start the new one
                anim.cancel_all(self.widget)
                
                # Add completion callback for pen tracker if needed
                if self._show_hand:
                    anim.bind(on_complete=self._on_draw_complete)
                    
                anim.start(self.widget)
            else:
                # Static rendering
                Animation.cancel_all(self.widget)
                if not fill:
                    self.update_canvas()
                else:
                    self.widget.canvas.clear()
                    self.fill_up_shapes()

    def shape_animate(self, svg_file: str, anim_config_list: List[Dict] = None, 
                     on_complete: Callable = None) -> None:
        """
        Animate individual shapes in an SVG file.
        
        Args:
            svg_file: Path to the SVG file
            anim_config_list: List of animation configurations, each containing:
                - id_: Shape ID to animate
                - from_: Direction of animation
                - d: Duration (optional)
                - t: Transition (optional)
            on_complete: Function to call when all animations complete
        """
        if anim_config_list is None:
            anim_config_list = []
            
        # First draw the SVG without animation
        self.draw(svg_file, from_shape_anim=True)
        setattr(self.widget, "mesh_opacity", 1)

        # Initialize animation state
        self.all_anim = []
        self.curr_count = 0
        self.prev_shapes = []
        self.curr_shape = []
        
        # Prepare animations using AnimationHandler
        self.all_anim = AnimationHandler.prepare_shape_animations(
            self,
            self.widget,
            anim_config_list,
            self.closed_shapes,
            self.svg_size,
            self.current_svg_file
        )
        
        # Start animations if any are ready
        if self.all_anim:
            id_, animation = self.all_anim[0]
            setattr(self, "curr_id", id_)
            setattr(self, "curr_clr", self.closed_shapes[id_]["color"])
            
            # Attach progress tracking
            animation.bind(on_progress=self.track_progress)
            
            # Attach completion callback if provided
            if on_complete and self.all_anim:
                self.all_anim[-1][1].bind(on_complete=on_complete)
            
            # Start the animation
            animation.cancel_all(self.widget)
            animation.bind(on_complete=self.anim_on_comp)
            animation.start(self.widget)
        elif anim_config_list:
            # In case there are config items but no animations were created
            if on_complete:
                on_complete()

    def draw_text(
        self,
        text: str,
        animate: bool = True,
        font_path: Optional[str] = None,
        font_size: float = 100.0,
        fill_color: str = "#000000",
        anim_type: str = "seq",
        on_complete: Optional[Callable] = None,
        **kwargs
    ) -> None:
        """
        Draw and animate text like handwriting.
        
        This method converts text to SVG paths and animates the drawing
        to create a handwriting effect suitable for whiteboards.
        
        Args:
            text: Text string to draw and animate
            animate: Whether to animate the drawing process
            font_path: Path to TTF/OTF font file. If None, uses system default.
            font_size: Target font size in pixels
            fill_color: Fill color for the text (hex format, e.g., "#000000")
            anim_type: Animation type - "seq" for sequential or "par" for parallel
            on_complete: Callback function called when drawing completes (only 
                        called immediately for non-animated draws; for animated 
                        draws with completion callbacks, use text_animate() instead)
            
        Keyword Args:
            fill: Whether to fill the text after drawing (bool)
            line_width: Width of lines (int)
            line_color: Color of lines during drawing (list of RGBA values)
            dur: Duration of each animation step (float)
            show_hand: Whether to show a hand image following the pen (bool)
            hand_image: Path to custom hand image file (str)
            hand_size: Size of hand image as (width, height) tuple
            pen_offset: Offset of pen tip in hand image as (x, y) tuple
            
        Example:
            >>> kivg = Kivg(widget)
            >>> kivg.draw_text("Hello World", animate=True, font_size=80)
        """
        # Find font if not specified
        if font_path is None:
            font_path = find_system_font()
            if font_path is None:
                raise ValueError(
                    "No font file found. Please specify a font_path parameter."
                )
        
        # Clean up any previous temporary file
        self._cleanup_temp_svg()
        
        # Create temporary SVG file from text
        fd, temp_svg_path = tempfile.mkstemp(suffix='.svg')
        os.close(fd)
        
        try:
            # Convert text to SVG
            text_to_svg_file(
                text=text,
                output_path=temp_svg_path,
                font_path=font_path,
                font_size=font_size,
                fill_color=fill_color
            )
            
            # Store the temp path for cleanup
            self._temp_text_svg = temp_svg_path
            
            # Store the completion callback for animation
            self._text_on_complete = on_complete
            
            # Draw the SVG with animation
            self.draw(
                temp_svg_path,
                animate=animate,
                anim_type=anim_type,
                **kwargs
            )
            
            # Handle completion callback
            if on_complete:
                if not animate:
                    # For non-animated draws, call immediately
                    on_complete()
                # For animated draws, the callback should be called when animation completes.
                # Note: The draw() method currently doesn't expose on_complete callback.
                # Users can use text_animate() for full animation control with callbacks.
                    
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_svg_path):
                os.unlink(temp_svg_path)
            raise e

    def text_animate(
        self,
        text: str,
        font_path: Optional[str] = None,
        font_size: float = 100.0,
        fill_color: str = "#000000",
        animation_type: str = "from_center_y",
        duration_per_char: float = 0.15,
        transition: str = "out_bounce",
        on_complete: Optional[Callable] = None
    ) -> None:
        """
        Animate text with shape animation effects (each character appears separately).
        
        This method creates a more dramatic text animation where each character
        appears with its own animation effect, similar to shape_animate().
        
        Args:
            text: Text string to animate
            font_path: Path to TTF/OTF font file. If None, uses system default.
            font_size: Target font size in pixels
            fill_color: Fill color for the text (hex format)
            animation_type: Type of animation effect:
                - "from_left": Characters slide in from left
                - "from_right": Characters slide in from right
                - "from_top": Characters drop from top
                - "from_bottom": Characters rise from bottom
                - "from_center_x": Characters grow horizontally from center
                - "from_center_y": Characters grow vertically from center
                - "sequential": Characters appear without directional animation
            duration_per_char: Duration of animation per character in seconds
            transition: Kivy animation transition type (e.g., "out_bounce", 
                       "out_back", "out_elastic")
            on_complete: Callback function when animation completes
            
        Example:
            >>> kivg = Kivg(widget)
            >>> kivg.text_animate(
            ...     "Hello",
            ...     animation_type="from_top",
            ...     transition="out_bounce"
            ... )
        """
        # Find font if not specified
        if font_path is None:
            font_path = find_system_font()
            if font_path is None:
                raise ValueError(
                    "No font file found. Please specify a font_path parameter."
                )
        
        # Clean up any previous temporary file
        self._cleanup_temp_svg()
        
        # Create temporary SVG file from text
        fd, temp_svg_path = tempfile.mkstemp(suffix='.svg')
        os.close(fd)
        
        try:
            # Convert text to SVG
            text_to_svg_file(
                text=text,
                output_path=temp_svg_path,
                font_path=font_path,
                font_size=font_size,
                fill_color=fill_color
            )
            
            # Store the temp path for cleanup
            self._temp_text_svg = temp_svg_path
            
            # Generate animation config for each character
            anim_config = get_text_animation_config(
                text=text,
                animation_type=animation_type,
                duration_per_char=duration_per_char,
                transition=transition
            )
            
            # Use shape_animate to animate the text
            self.shape_animate(
                temp_svg_path,
                anim_config_list=anim_config,
                on_complete=on_complete
            )
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_svg_path):
                os.unlink(temp_svg_path)
            raise e
