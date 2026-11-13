"""
Re-exports validation primitives from product_validator.py for backward compatibility.
"""

from .product_validator import (
    BLOCKED_HOSTNAMES,
    DEFAULT_AUTHORIZED_SHOPIFY_DOMAINS,
    SUPPORTED_RETAILERS,
    URLValidationError,
    ValidatedProductTarget,
    detect_retailer,
    extract_shopify_handle,
    get_authorized_shopify_domains,
    identify_shopify_store,
    is_private_or_reserved_ip,
    validate_product_target,
    validate_product_url,
    validate_safe_image_url,
)

__all__ = [
    "BLOCKED_HOSTNAMES",
    "DEFAULT_AUTHORIZED_SHOPIFY_DOMAINS",
    "SUPPORTED_RETAILERS",
    "URLValidationError",
    "ValidatedProductTarget",
    "detect_retailer",
    "extract_shopify_handle",
    "get_authorized_shopify_domains",
    "identify_shopify_store",
    "is_private_or_reserved_ip",
    "validate_product_target",
    "validate_product_url",
    "validate_safe_image_url",
]
