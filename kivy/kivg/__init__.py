"""
Kivg - SVG drawing and animation for Kivy
"""
from kivy.logger import Logger
from .main import Kivg
from .version import __version__
from .text_to_svg import (
    text_to_svg_file,
    text_to_svg_paths,
    get_text_animation_config,
    find_system_font
)

_log_message = "Kivg:" + f" {__version__}" + f' (installed at "{__file__}")'
Logger.info(_log_message)

__all__ = [
    "Kivg",
    "text_to_svg_file",
    "text_to_svg_paths",
    "get_text_animation_config",
    "find_system_font"
]
