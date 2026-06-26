"""
app/components/__init__.py
--------------------------
Public interface for the components package.

Exports the three render functions so main_app.py can import them with a
single line per component.

Usage:
    from app.components.uploader import render_uploader
    from app.components.results  import render_results
    from app.components.sidebar  import render_sidebar
"""

from app.components.uploader import render_uploader
from app.components.results import render_results
from app.components.sidebar import render_sidebar

__all__ = ["render_uploader", "render_results", "render_sidebar"]
