"""Backward-compatibility shim for Android UI inspection.

The original :mod:`src.ui_inspector` module has been split into focused
modules:

- :mod:`src.ui_parser` — XML cleaning, escaping, and parsing.
- :mod:`src.ui_retriever` — ADB orchestration, file retrieval, and retries.
- :mod:`src.element_finder` — element search and dict-tree conversion.

This module re-exports the previous public API so existing imports such as
``from src.ui_inspector import UILayoutExtractor, ElementFinder, UIElement``
continue to work unchanged.
"""

from .element_finder import ElementFinder
from .ui_models import UIElement, parse_bounds
from .ui_parser import UIParser
from .ui_retriever import UILayoutExtractor

__all__ = [
    "ElementFinder",
    "UIElement",
    "UILayoutExtractor",
    "UIParser",
    "parse_bounds",
]
