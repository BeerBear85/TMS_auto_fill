"""Tests for network_utils module."""

import pytest
from unittest.mock import patch, MagicMock
import urllib.error
import socket
import ssl

from timesheet_bot.network_utils import (
    check_tms_connectivity,
    is_vpn_proxy_error,
    format_connectivity_error
)


class TestCheckTmsConnectivity:
    """Tests for check_tms_connectivity function."""

    @patch('urllib.request.urlopen')
    def test_successful_connection_200(self, mock_urlopen):
        """Test successful connectivity with HTTP 200."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        success, error = check_tms_connectivity("https://example.com")
        assert success is True
        assert error == ""

    @patch('urllib.request.urlopen')
    def test_successful_redirect_302(self, mock_urlopen):
        """Test successful connectivity with redirect (login page)."""
        mock_response = MagicMock()
        mock_response.status = 302
        mock_response.reason = "Found"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        success, error = check_tms_connectivity("https://example.com")
        assert success is True
        assert error == ""

    @patch('urllib.request.urlopen')
    def test_dns_failure(self, mock_urlopen):
        """Test DNS resolution failure (VPN/proxy issue)."""
        mock_urlopen.side_effect = urllib.error.URLError(
            socket.gaierror(11001, "getaddrinfo failed")
        )

        success, error = check_tms_connectivity("https://example.com")
        assert success is False
        assert "DNS" in error or "resolution" in error

    @patch('urllib.request.urlopen')
    def test_connection_timeout(self, mock_urlopen):
        """Test connection timeout."""
        mock_urlopen.side_effect = socket.timeout()

        success, error = check_tms_connectivity("https://example.com", timeout=5)
        assert success is False
        assert "timeout" in error.lower()
        assert "5s" in error

    @patch('urllib.request.urlopen')
    def test_connection_timeout_via_urlerror(self, mock_urlopen):
        """Test connection timeout wrapped in URLError."""
        mock_urlopen.side_effect = urllib.error.URLError(socket.timeout())

        success, error = check_tms_connectivity("https://example.com", timeout=10)
        assert success is False
        assert "timeout" in error.lower()
        assert "10s" in error

    @patch('urllib.request.urlopen')
    def test_ssl_error(self, mock_urlopen):
        """Test SSL certificate error."""
        mock_urlopen.side_effect = ssl.SSLError("certificate verify failed")

        success, error = check_tms_connectivity("https://example.com")
        assert success is False
        assert "SSL" in error or "certificate" in error

    @patch('urllib.request.urlopen')
    def test_ssl_error_via_urlerror(self, mock_urlopen):
        """Test SSL error wrapped in URLError."""
        mock_urlopen.side_effect = urllib.error.URLError(
            ssl.SSLError("certificate verify failed")
        )

        success, error = check_tms_connectivity("https://example.com")
        assert success is False
        assert "SSL" in error or "certificate" in error

    @patch('urllib.request.urlopen')
    def test_connection_refused(self, mock_urlopen):
        """Test connection refused error."""
        mock_urlopen.side_effect = urllib.error.URLError(
            ConnectionRefusedError("Connection refused")
        )

        success, error = check_tms_connectivity("https://example.com")
        assert success is False
        assert "refused" in error.lower()

    @patch('urllib.request.urlopen')
    def test_server_error_500(self, mock_urlopen):
        """Test server error (HTTP 500)."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com", 500, "Internal Server Error", {}, None
        )

        success, error = check_tms_connectivity("https://example.com")
        assert success is False
        assert "500" in error

    @patch('urllib.request.urlopen')
    def test_server_error_503(self, mock_urlopen):
        """Test server unavailable (HTTP 503)."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com", 503, "Service Unavailable", {}, None
        )

        success, error = check_tms_connectivity("https://example.com")
        assert success is False
        assert "503" in error

    @patch('urllib.request.urlopen')
    def test_client_error_404(self, mock_urlopen):
        """Test client error (HTTP 404)."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com", 404, "Not Found", {}, None
        )

        success, error = check_tms_connectivity("https://example.com")
        assert success is False
        assert "404" in error

    @patch('urllib.request.urlopen')
    def test_os_error(self, mock_urlopen):
        """Test general OS error."""
        mock_urlopen.side_effect = urllib.error.URLError(
            OSError("Network unreachable")
        )

        success, error = check_tms_connectivity("https://example.com")
        assert success is False
        assert "Network" in error or "error" in error

    @patch('urllib.request.urlopen')
    def test_invalid_url(self, mock_urlopen):
        """Test invalid URL."""
        mock_urlopen.side_effect = ValueError("Invalid URL")

        success, error = check_tms_connectivity("not-a-url")
        assert success is False
        assert "Invalid" in error or "URL" in error


class TestIsVpnProxyError:
    """Tests for is_vpn_proxy_error function."""

    def test_dns_error_detected(self):
        """Test DNS errors are flagged as VPN issues."""
        assert is_vpn_proxy_error("DNS resolution failed") is True
        assert is_vpn_proxy_error("getaddrinfo failed") is True
        assert is_vpn_proxy_error("gaierror occurred") is True

    def test_timeout_detected(self):
        """Test timeouts are flagged as VPN issues."""
        assert is_vpn_proxy_error("Connection timed out") is True
        assert is_vpn_proxy_error("timeout after 10s") is True
        assert is_vpn_proxy_error("Request TIMED OUT") is True

    def test_connection_refused_detected(self):
        """Test connection refused is flagged as VPN issue."""
        assert is_vpn_proxy_error("Connection refused") is True
        assert is_vpn_proxy_error("CONNECTION REFUSED") is True

    def test_proxy_keywords_detected(self):
        """Test proxy-related keywords are detected."""
        assert is_vpn_proxy_error("tunnel connection failed") is True
        assert is_vpn_proxy_error("proxy error occurred") is True
        assert is_vpn_proxy_error("VPN not connected") is True

    def test_network_unreachable_detected(self):
        """Test network unreachable is flagged as VPN issue."""
        assert is_vpn_proxy_error("network unreachable") is True
        assert is_vpn_proxy_error("no route to host") is True

    def test_non_vpn_error_http_500(self):
        """Test HTTP 500 error is not flagged as VPN issue."""
        assert is_vpn_proxy_error("HTTP 500 Internal Server Error") is False

    def test_non_vpn_error_http_404(self):
        """Test HTTP 404 error is not flagged as VPN issue."""
        assert is_vpn_proxy_error("HTTP 404 Not Found") is False

    def test_non_vpn_error_generic(self):
        """Test generic errors are not flagged as VPN issues."""
        assert is_vpn_proxy_error("Unexpected error occurred") is False
        assert is_vpn_proxy_error("Something went wrong") is False

    def test_case_insensitive(self):
        """Test error detection is case-insensitive."""
        assert is_vpn_proxy_error("DNS RESOLUTION FAILED") is True
        assert is_vpn_proxy_error("connection TIMEOUT") is True


class TestFormatConnectivityError:
    """Tests for format_connectivity_error function."""

    def test_vpn_error_formatting(self):
        """Test VPN error includes helpful hints."""
        message = format_connectivity_error(
            "https://tms.example.com",
            "DNS resolution failed",
            is_vpn_issue=True
        )
        assert "NETWORK CONNECTIVITY CHECK FAILED" in message
        assert "VPN" in message or "Proxy" in message
        assert "Zscaler" in message
        assert "https://tms.example.com" in message
        assert "DNS resolution failed" in message
        assert "authenticated" in message.lower()

    def test_non_vpn_error_formatting(self):
        """Test non-VPN error has generic message."""
        message = format_connectivity_error(
            "https://tms.example.com",
            "HTTP 500 error",
            is_vpn_issue=False
        )
        assert "NETWORK CONNECTIVITY CHECK FAILED" in message
        assert "HTTP 500 error" in message
        assert "internet connection" in message.lower()
        assert "VPN" not in message  # Should not mention VPN for non-VPN errors

    def test_url_included_in_message(self):
        """Test URL is included in error message."""
        message = format_connectivity_error(
            "https://tms.md-man.biz/home",
            "Connection timeout",
            is_vpn_issue=True
        )
        assert "https://tms.md-man.biz/home" in message

    def test_error_details_included(self):
        """Test error details are included in message."""
        error_detail = "Connection timeout after 10s"
        message = format_connectivity_error(
            "https://example.com",
            error_detail,
            is_vpn_issue=True
        )
        assert error_detail in message

    def test_multiline_format(self):
        """Test message is formatted with multiple lines."""
        message = format_connectivity_error(
            "https://example.com",
            "Test error",
            is_vpn_issue=True
        )
        lines = message.split("\n")
        assert len(lines) > 5  # Should have multiple lines

    def test_vpn_specific_hints(self):
        """Test VPN-specific hints are included."""
        message = format_connectivity_error(
            "https://example.com",
            "DNS failed",
            is_vpn_issue=True
        )
        assert "Cisco AnyConnect" in message  # Another VPN example
        assert "turned ON" in message
        assert "authenticated" in message.lower()

    def test_non_vpn_hints(self):
        """Test non-VPN hints are different."""
        message = format_connectivity_error(
            "https://example.com",
            "Server error",
            is_vpn_issue=False
        )
        assert "TMS server" in message.lower() or "accessible" in message.lower()
        assert "internet connection" in message.lower()
