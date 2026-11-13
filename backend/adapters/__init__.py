"""
Retailer-specific extraction adapters for Myntra and AJIO.
"""

from .myntra import MyntraExtractor
from .ajio import AjioExtractor

__all__ = ["MyntraExtractor", "AjioExtractor"]
