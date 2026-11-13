"""
Backward-compatible ProductExtractionService facade delegating to ProductExtractionOrchestrator.
"""

from __future__ import annotations
from .product_extractor import ProductExtractionOrchestrator


class ProductExtractionService(ProductExtractionOrchestrator):
    """Alias for ProductExtractionOrchestrator preserving existing API contracts."""
    pass
