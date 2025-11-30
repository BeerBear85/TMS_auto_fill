"""
Network connectivity utilities for TMS automation.

This module provides lightweight network connectivity checks
to detect VPN/proxy issues before launching browser automation.
"""

import urllib.request
import urllib.error
import socket
import ssl
from typing import Tuple


class ConnectivityError(Exception):
    """Raised when network connectivity check fails."""
    pass


def check_tms_connectivity(tms_url: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Check network connectivity to TMS URL.

    Performs a HEAD request to validate DNS, TCP, SSL, and HTTP connectivity
    without transferring full page content.

    Args:
        tms_url: URL to check (e.g., "https://tms.md-man.biz/home")
        timeout: Timeout in seconds (default: 10)

    Returns:
        Tuple of (success: bool, error_message: str)
        - success=True, error_message="" if connection successful
        - success=False, error_message=<details> if connection failed

    Examples:
        >>> success, error = check_tms_connectivity("https://tms.md-man.biz/home")
        >>> if not success:
        ...     print(f"Connection failed: {error}")
    """
    try:
        # Use HEAD request for minimal data transfer
        request = urllib.request.Request(tms_url, method='HEAD')
        request.add_header('User-Agent', 'TMS-Timesheet-Bot/2.1')

        with urllib.request.urlopen(request, timeout=timeout) as response:
            # 2xx or 3xx = success (TMS redirects to login are OK)
            if 200 <= response.status < 400:
                return (True, "")
            else:
                # 4xx or 5xx errors
                return (False, f"HTTP {response.status}: {response.reason}")

    except urllib.error.HTTPError as e:
        # HTTP error (4xx, 5xx)
        return (False, f"HTTP {e.code}: {e.reason}")

    except urllib.error.URLError as e:
        # Network-level errors (DNS, connection, SSL)
        if isinstance(e.reason, socket.timeout):
            return (False, f"Connection timeout after {timeout}s")
        elif isinstance(e.reason, socket.gaierror):
            # DNS resolution failure
            return (False, f"DNS resolution failed: {e.reason}")
        elif isinstance(e.reason, ssl.SSLError):
            # SSL certificate error
            return (False, f"SSL certificate error: {e.reason}")
        elif isinstance(e.reason, ConnectionRefusedError):
            return (False, f"Connection refused: {e.reason}")
        elif isinstance(e.reason, OSError):
            return (False, f"Network error: {e.reason}")
        else:
            return (False, str(e.reason))

    except socket.timeout:
        return (False, f"Connection timeout after {timeout}s")

    except ssl.SSLError as e:
        return (False, f"SSL certificate error: {e}")

    except ValueError as e:
        # Invalid URL
        return (False, f"Invalid URL: {e}")

    except Exception as e:
        # Catch-all for unexpected errors
        return (False, f"Unexpected error: {str(e)}")


def is_vpn_proxy_error(error_message: str) -> bool:
    """
    Determine if error is likely VPN/proxy related.

    Checks for common VPN/proxy error indicators like DNS failures,
    timeouts, connection refusals, and tunnel issues.

    Args:
        error_message: Error message from connectivity check

    Returns:
        True if error appears to be VPN/proxy related, False otherwise

    Examples:
        >>> is_vpn_proxy_error("DNS resolution failed")
        True
        >>> is_vpn_proxy_error("HTTP 500 Internal Server Error")
        False
    """
    vpn_indicators = [
        # DNS-related
        'dns',
        'name resolution failed',
        'getaddrinfo failed',
        'gaierror',
        # Connection-related
        'connection refused',
        'connection timed out',
        'timeout',
        'timed out',
        'network unreachable',
        'no route to host',
        # VPN/Proxy-specific
        'tunnel',
        'proxy',
        'vpn',
    ]

    error_lower = error_message.lower()
    return any(indicator in error_lower for indicator in vpn_indicators)


def format_connectivity_error(
    tms_url: str,
    error_message: str,
    is_vpn_issue: bool
) -> str:
    """
    Format user-friendly connectivity error message.

    Creates a detailed error message with helpful hints for resolving
    the connectivity issue, especially for VPN/proxy problems.

    Args:
        tms_url: The URL that failed to connect
        error_message: The error message from the connectivity check
        is_vpn_issue: Whether the error appears to be VPN/proxy related

    Returns:
        Formatted error message string

    Examples:
        >>> msg = format_connectivity_error(
        ...     "https://tms.example.com",
        ...     "DNS resolution failed",
        ...     True
        ... )
        >>> "VPN/Proxy" in msg
        True
    """
    lines = []
    lines.append("NETWORK CONNECTIVITY CHECK FAILED")
    lines.append("")
    lines.append(f"Could not reach TMS server: {tms_url}")
    lines.append(f"Error: {error_message}")
    lines.append("")

    if is_vpn_issue:
        lines.append("This error is often caused by:")
        lines.append("  - VPN/Proxy not connected (e.g., Zscaler, Cisco AnyConnect)")
        lines.append("  - VPN/Proxy not authenticated")
        lines.append("  - Network connectivity issues")
        lines.append("  - Firewall blocking the connection")
        lines.append("")
        lines.append("Please ensure:")
        lines.append("  1. Your VPN/Proxy (e.g., Zscaler) is turned ON and authenticated")
        lines.append("  2. You can access the TMS website in your browser")
        lines.append(f"  3. The URL is correct: {tms_url}")
    else:
        lines.append("Please check:")
        lines.append("  1. Your internet connection is working")
        lines.append("  2. The TMS server is accessible")
        lines.append(f"  3. The URL is correct: {tms_url}")

    return "\n".join(lines)
