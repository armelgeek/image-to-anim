"""
PenTracker handles pen/stylus tracking with hand image during SVG path animation.
This creates a writing effect where a hand image follows the drawing path.
"""

from kivy.graphics import Rectangle, Color, InstructionGroup
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from typing import Any, Optional, Tuple, Callable
import os


class PenTracker:
    """
    Tracks pen position during path drawing animation and displays a hand image.
    
    The hand image follows the current drawing position to create a realistic
    writing/drawing effect.
    """
    
    # Default hand image path (bundled with the package)
    DEFAULT_HAND_IMAGE = os.path.join(os.path.dirname(__file__), "..", "assets", "drawing-hand.png")
    
    def __init__(self, widget: Any, hand_image: Optional[str] = None, 
                 hand_size: Tuple[float, float] = (100, 100),
                 pen_offset: Tuple[float, float] = (10, 85)):
        """
        Initialize the PenTracker.
        
        Args:
            widget: The Kivy widget to draw the hand on
            hand_image: Path to the hand image file. If None, uses default.
            hand_size: Size of the hand image (width, height)
            pen_offset: Offset from pen tip to hand image position (x, y).
                       This is where the pen tip is located relative to the 
                       top-left corner of the hand image.
        """
        self.widget = widget
        self.hand_image_path = hand_image or self.DEFAULT_HAND_IMAGE
        self.hand_size = hand_size
        self.pen_offset = pen_offset
        self._hand_texture = None
        self._hand_group = None  # InstructionGroup to hold hand graphics
        self._hand_rect = None
        self._hand_color = None
        self._is_active = False
        self._current_pos = (0, 0)
        
        # Slide-out animation state
        self._slide_out_event = None
        self._slide_out_callback = None
        
        # Load the hand image texture
        self._load_hand_texture()
    
    def _load_hand_texture(self) -> None:
        """Load the hand image texture."""
        if not os.path.exists(self.hand_image_path):
            self._hand_texture = None
            return
        try:
            self._hand_texture = CoreImage(self.hand_image_path).texture
        except (IOError, OSError):
            # Image file could not be loaded (corrupted, unsupported format, etc.)
            self._hand_texture = None
    
    def start(self) -> None:
        """Start tracking - makes the hand visible.
        
        Does nothing if hand texture could not be loaded.
        """
        if self._hand_texture is None:
            return
        
        self._is_active = True
        # Create instruction group for hand graphics
        self._hand_group = InstructionGroup()
        self._hand_color = Color(1, 1, 1, 1)
        self._hand_rect = Rectangle(
            texture=self._hand_texture,
            pos=self._current_pos,
            size=self.hand_size
        )
        self._hand_group.add(self._hand_color)
        self._hand_group.add(self._hand_rect)
        self.widget.canvas.after.add(self._hand_group)
    
    def stop(self) -> None:
        """Stop tracking and hide the hand immediately."""
        # Cancel any ongoing slide-out animation
        if self._slide_out_event:
            self._slide_out_event.cancel()
            self._slide_out_event = None
        self._slide_out_callback = None
        
        self._is_active = False
        self.clear_hand()
    
    def update_position(self, x: float, y: float) -> None:
        """
        Update the hand position to follow the pen tip.
        
        Args:
            x: X coordinate of the current pen tip position
            y: Y coordinate of the current pen tip position
        """
        if not self._is_active or self._hand_texture is None:
            return
        
        # Calculate hand position based on pen tip and offset
        # The pen tip should appear at the pen_offset position within the hand image
        # pen_offset is specified from top-left of image, but Kivy uses bottom-left
        # So we need to convert: offset_from_bottom = hand_height - offset_from_top
        hand_x = x - self.pen_offset[0]
        hand_y = y - self.pen_offset[1]
        
        self._current_pos = (hand_x, hand_y)
        
        # Update the rectangle position directly (more efficient than recreating)
        if self._hand_rect:
            self._hand_rect.pos = self._current_pos
    
    def draw_hand(self) -> None:
        """Draw the hand image at the current position.
        
        Note: This is now a no-op since we update position directly.
        Kept for backward compatibility.
        """
        pass
    
    def clear_hand(self) -> None:
        """Clear the hand from the canvas."""
        if self._hand_group:
            self.widget.canvas.after.remove(self._hand_group)
            self._hand_group = None
            self._hand_rect = None
            self._hand_color = None
    
    @property
    def is_active(self) -> bool:
        """Check if pen tracking is active."""
        return self._is_active
    
    @property
    def current_position(self) -> Tuple[float, float]:
        """Get the current hand position."""
        return self._current_pos
    
    def slide_out(self, on_complete: Optional[Callable] = None, 
                  duration: float = 0.5, step: float = 0.016) -> None:
        """
        Animate the hand sliding out of the widget.
        
        The hand slides downward and fades out as if lifting the hand
        from the drawing surface.
        
        Args:
            on_complete: Callback to call when slide-out animation completes
            duration: Duration of the slide-out animation in seconds
            step: Time step for animation updates in seconds
        """
        if not self._is_active or self._hand_texture is None:
            if on_complete:
                on_complete()
            return
        
        self._slide_out_callback = on_complete
        
        # Calculate target position: slide downward off the widget
        # Keep the same x position, only move down below the widget bottom
        widget_bottom = self.widget.pos[1] - self.hand_size[1]
        
        # Starting position
        start_x, start_y = self._current_pos
        target_x = start_x  # Keep same x position - slide straight down
        target_y = widget_bottom
        
        # Animation state
        self._slide_start_pos = (start_x, start_y)
        self._slide_target_pos = (target_x, target_y)
        self._slide_progress = 0.0
        self._slide_duration = duration
        self._slide_step = step
        self._slide_start_opacity = 1.0  # Start fully visible
        # Store original color for fade effect
        if self._hand_color:
            self._slide_original_rgb = (
                self._hand_color.r, 
                self._hand_color.g, 
                self._hand_color.b
            )
        else:
            self._slide_original_rgb = (1, 1, 1)
        
        # Start the animation
        self._slide_out_event = Clock.schedule_interval(
            self._update_slide_out, step
        )
    
    def _update_slide_out(self, dt: float) -> bool:
        """
        Update the slide-out animation.
        
        Args:
            dt: Delta time since last update
            
        Returns:
            False to stop the animation, True to continue
        """
        self._slide_progress += dt / self._slide_duration
        
        if self._slide_progress >= 1.0:
            # Animation complete
            self._slide_progress = 1.0
            self._finish_slide_out()
            return False
        
        # Ease-out-quadratic: starts fast and decelerates smoothly
        # Formula: f(t) = -t * (t - 2) = -t^2 + 2t
        # At t=0: f(0) = 0, at t=1: f(1) = 1
        # Derivative: f'(t) = -2t + 2, so f'(0) = 2 (fast) and f'(1) = 0 (stops)
        t = self._slide_progress
        ease = -1.0 * t * (t - 2.0)
        
        start_x, start_y = self._slide_start_pos
        target_x, target_y = self._slide_target_pos
        
        current_x = start_x + (target_x - start_x) * ease
        current_y = start_y + (target_y - start_y) * ease
        
        self._current_pos = (current_x, current_y)
        
        if self._hand_rect:
            self._hand_rect.pos = self._current_pos
        
        # Update opacity with fade effect (linear fade from 1 to 0)
        if self._hand_color:
            current_opacity = self._slide_start_opacity * (1.0 - ease)
            r, g, b = self._slide_original_rgb
            self._hand_color.rgba = (r, g, b, current_opacity)
        
        return True
    
    def _finish_slide_out(self) -> None:
        """Complete the slide-out animation and clean up."""
        # Cancel the animation event if still scheduled
        if self._slide_out_event:
            self._slide_out_event.cancel()
            self._slide_out_event = None
        
        # Stop tracking and clear the hand
        self._is_active = False
        self.clear_hand()
        
        # Call the completion callback
        if self._slide_out_callback:
            callback = self._slide_out_callback
            self._slide_out_callback = None
            callback()
