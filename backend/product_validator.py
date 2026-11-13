"""
Product URL validation, SSRF protection, safe image URL verification,
Shopify store & handle identification, and Myntra/AJIO retailer detection.
"""

from __future__ import annotations
import ipaddress
import os
import re
import socket
from dataclasses import dataclass
from typing import Optional, Set, Tuple
from urllib.parse import urlparse


SUPPORTED_RETAILERS = {
    "myntra.com": "Myntra",
    "www.myntra.com": "Myntra",
    "m.myntra.com": "Myntra",
    "ajio.com": "AJIO",
    "www.ajio.com": "AJIO",
    "luxe.ajio.com": "AJIO",
}

DEFAULT_AUTHORIZED_SHOPIFY_DOMAINS: Set[str] = {
    "taylorstitch.com",
    "www.taylorstitch.com",
    "allbirds.com",
    "www.allbirds.com",
    "kotn.com",
    "www.kotn.com",
    "gymshark.com",
    "www.gymshark.com",
}

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "metadata",
    "169.254.169.254",
    "0.0.0.0",
}


class URLValidationError(ValueError):
    def __init__(self, message: str, code: str = "INVALID_URL"):
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass
class ValidatedProductTarget:
    normalized_url: str
    retailer: str  # "Shopify" | "Myntra" | "AJIO"
    store_domain: str
    product_id: str
    product_handle: Optional[str] = None
    is_authorized_shopify_store: bool = False


def get_authorized_shopify_domains() -> Set[str]:
    domains = set(DEFAULT_AUTHORIZED_SHOPIFY_DOMAINS)
    env_domains = os.environ.get("SHOPIFY_AUTHORIZED_DOMAINS", "")
    for item in env_domains.split(","):
        cleaned = item.strip().lower().strip(".")
        if cleaned:
            domains.add(cleaned)
            if not cleaned.startswith("www."):
                domains.add(f"www.{cleaned}")
    return domains


def is_private_or_reserved_ip(ip_str: str) -> bool:
    """Check if an IP address is loopback, private, link-local, multicast, or reserved."""
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        )
    except ValueError:
        return False


def validate_safe_image_url(img_url: Optional[str]) -> Optional[str]:
    """Ensure extracted image URLs use safe protocols and do not point to internal/private IPs."""
    if not img_url or not isinstance(img_url, str):
        return None
    cleaned = img_url.strip()
    if cleaned.startswith("/src/assets/"):
        return cleaned
    if cleaned.startswith("//"):
        cleaned = "https:" + cleaned
    try:
        parsed = urlparse(cleaned)
    except Exception:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    host = (parsed.hostname or "").lower().strip(".")
    if not host or host in BLOCKED_HOSTNAMES or is_private_or_reserved_ip(host):
        return None
    return cleaned


def extract_shopify_handle(path: str) -> Optional[str]:
    """
    Extract product handle from standard Shopify URL patterns:
    - /products/<handle>
    - /collections/<collection>/products/<handle>
    - /en-us/products/<handle>
    """
    if not path:
        return None
    match = re.search(r"/products/([a-zA-Z0-9_-]+)(?:\.(?:json|js|html))?/?$", path, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def identify_shopify_store(url: str) -> Tuple[str, str, bool]:
    """
    Identify store domain, product handle, and authorization status from a Shopify product URL.
    Raises URLValidationError if the URL is invalid or lacks a /products/<handle> path.
    """
    if not url or not isinstance(url, str):
        raise URLValidationError("Product URL is required.", "EMPTY_URL")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise URLValidationError("Only http and https URLs are permitted.", "INVALID_SCHEME")
    hostname = (parsed.hostname or "").lower().strip(".")
    if not hostname:
        raise URLValidationError("URL is missing a valid hostname.", "MISSING_HOST")
    if hostname in BLOCKED_HOSTNAMES or is_private_or_reserved_ip(hostname):
        raise URLValidationError("SSRF protection: private or internal network addresses are blocked.", "SSRF_BLOCKED")

    handle = extract_shopify_handle(parsed.path or "")
    if not handle:
        raise URLValidationError(
            "Invalid Shopify product URL format. Expected a URL containing '/products/<product-handle>'.",
            "INVALID_SHOPIFY_URL",
        )

    auth_domains = get_authorized_shopify_domains()
    is_authorized = (
        hostname in auth_domains
        or hostname.endswith(".myshopify.com")
    )
    return hostname, handle, is_authorized


def detect_retailer(url: str) -> str:
    """
    Detect the supported retailer ('Shopify', 'Myntra', or 'AJIO') from a validated URL.
    Raises URLValidationError if the domain is unsupported or invalid.
    """
    if not url or not isinstance(url, str):
        raise URLValidationError("Product URL is required.", "EMPTY_URL")

    cleaned = url.strip()
    try:
        parsed = urlparse(cleaned)
    except Exception as exc:
        raise URLValidationError("Malformed URL structure.", "MALFORMED_URL") from exc

    if parsed.scheme not in ("http", "https"):
        raise URLValidationError(
            f"Unsupported URL scheme '{parsed.scheme or 'none'}'. Only http and https are permitted.",
            "INVALID_SCHEME",
        )

    hostname = (parsed.hostname or "").lower().strip(".")
    if not hostname:
        raise URLValidationError("URL is missing a valid hostname.", "MISSING_HOST")

    if hostname in BLOCKED_HOSTNAMES or is_private_or_reserved_ip(hostname):
        raise URLValidationError(
            "Access to private, loopback, or internal network addresses is prohibited (SSRF protection).",
            "SSRF_BLOCKED",
        )

    if hostname in SUPPORTED_RETAILERS:
        return SUPPORTED_RETAILERS[hostname]

    auth_shopify = get_authorized_shopify_domains()
    path = parsed.path or ""
    if hostname in auth_shopify or hostname.endswith(".myshopify.com"):
        return "Shopify"

    # Also check if it's a /products/<handle> URL on an unauthorized domain
    if extract_shopify_handle(path):
        raise URLValidationError(
            f"Shopify store domain '{hostname}' is not in the authorized store list. "
            f"Authorized Shopify domains: {', '.join(sorted(d for d in auth_shopify if not d.startswith('www.')))}.",
            "UNAUTHORIZED_SHOPIFY_STORE",
        )

    raise URLValidationError(
        f"Unsupported retailer domain '{hostname}'. Supported sources: authorized Shopify stores, Myntra (myntra.com), and AJIO (ajio.com).",
        "UNSUPPORTED_RETAILER",
    )


def validate_product_target(url: str, check_dns: bool = False) -> ValidatedProductTarget:
    """
    Full target validation returning ValidatedProductTarget with retailer, store_domain,
    product_id, product_handle, and authorization state.
    """
    retailer = detect_retailer(url)
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    hostname = (parsed.hostname or "").lower().strip(".")

    if parsed.username or parsed.password:
        raise URLValidationError("URLs containing embedded credentials are not allowed.", "CREDENTIALS_NOT_ALLOWED")

    if check_dns:
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_addr = item[4][0]
                if is_private_or_reserved_ip(ip_addr):
                    raise URLValidationError(
                        "Domain resolved to a private or reserved network IP address.",
                        "SSRF_BLOCKED",
                    )
        except socket.gaierror:
            pass

    path = parsed.path or ""
    if not path or path == "/":
        raise URLValidationError(
            f"Please provide a direct {retailer} product page URL rather than the store homepage.",
            "NOT_A_PRODUCT_PATH",
        )

    if retailer == "Shopify":
        store_domain, handle, is_auth = identify_shopify_store(cleaned)
        if not is_auth:
            raise URLValidationError(
                f"Shopify store '{store_domain}' is not authorized for automated extraction.",
                "UNAUTHORIZED_SHOPIFY_STORE",
            )
        clean_path = re.sub(r"\.(?:json|js)$", "", path)
        normalized_url = f"https://{store_domain}{clean_path}"
        return ValidatedProductTarget(
            normalized_url=normalized_url,
            retailer="Shopify",
            store_domain=store_domain,
            product_id=handle,
            product_handle=handle,
            is_authorized_shopify_store=True,
        )

    if retailer == "Myntra":
        match = re.search(r"/(\d{5,12})(?:/buy)?/?$", path, re.IGNORECASE)
        if not match:
            match = re.search(r"(\d{6,12})", path)
        if not match:
            raise URLValidationError(
                "Invalid Myntra product URL format. Expected a URL containing a product ID (e.g., https://www.myntra.com/shirts/brand/product-name/12345678/buy).",
                "INVALID_MYNTRA_URL",
            )
        extracted_id = match.group(1)
        return ValidatedProductTarget(
            normalized_url=f"https://{hostname}{path}",
            retailer="Myntra",
            store_domain=hostname,
            product_id=extracted_id,
            product_handle=extracted_id,
        )

    if retailer == "AJIO":
        match = re.search(r"/p/([a-zA-Z0-9_-]{5,32})", path, re.IGNORECASE)
        if not match:
            match = re.search(r"/([0-9]{8,15}(?:_[a-zA-Z0-9]+)?)/?$", path)
        if not match:
            raise URLValidationError(
                "Invalid AJIO product URL format. Expected a product path containing '/p/<product_id>' (e.g., https://www.ajio.com/brand-product-name/p/469123456_navy).",
                "INVALID_AJIO_URL",
            )
        extracted_id = match.group(1)
        return ValidatedProductTarget(
            normalized_url=f"https://{hostname}{path}",
            retailer="AJIO",
            store_domain=hostname,
            product_id=extracted_id,
            product_handle=extracted_id,
        )

    raise URLValidationError(f"Unsupported retailer '{retailer}'.", "UNSUPPORTED_RETAILER")


def validate_product_url(url: str, check_dns: bool = False) -> Tuple[str, str, Optional[str]]:
    """Backward-compatible tuple wrapper returning (normalized_url, retailer, product_id)."""
    target = validate_product_target(url, check_dns=check_dns)
    return target.normalized_url, target.retailer, target.product_id
