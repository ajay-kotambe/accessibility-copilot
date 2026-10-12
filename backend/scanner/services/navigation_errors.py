"""Translate Playwright navigation failures into clear, user-facing messages.

Raw browser errors (for example ``net::ERR_NAME_NOT_RESOLVED``) are useful in
server logs but meaningless to someone scanning a site. This module maps the
common navigation failures onto a single plain sentence each, so a failed scan
never exposes a raw Playwright string or stack trace through the API.

Nothing here affects URL validation or the SSRF guard; those keep raising
``ValueError`` with their own user-safe messages.
"""

MESSAGE_DNS = "We couldn't find that website. Check the URL and try again."
MESSAGE_CONNECTION = "We couldn't connect to this website. Check that it is online and try again."
MESSAGE_TIMEOUT = "This website took too long to respond. Try again later."
MESSAGE_GENERIC = "We couldn't scan that website. Check the URL and try again."

# Chromium/Playwright error codes grouped by how they should read to a user.
DNS_ERROR_CODES = (
    'ERR_NAME_NOT_RESOLVED',
    'ERR_NAME_RESOLUTION_FAILED',
)

CONNECTION_ERROR_CODES = (
    'ERR_CONNECTION_REFUSED',
    'ERR_CONNECTION_RESET',
    'ERR_CONNECTION_CLOSED',
    'ERR_CONNECTION_ABORTED',
    'ERR_CONNECTION_FAILED',
    'ERR_ADDRESS_UNREACHABLE',
    'ERR_NETWORK_CHANGED',
    'ERR_INTERNET_DISCONNECTED',
    'ERR_EMPTY_RESPONSE',
    'ERR_SSL_PROTOCOL_ERROR',
    'ERR_SSL_VERSION_OR_CIPHER_MISMATCH',
    'ERR_CERT_',
)

TIMEOUT_ERROR_CODES = (
    'ERR_TIMED_OUT',
    'ERR_CONNECTION_TIMED_OUT',
)


class ScanNavigationError(Exception):
    """A navigation failure carrying a safe, human-readable message.

    The technical cause is logged by the caller; only ``user_message`` is ever
    written to ``Scan.error_message`` or returned by the API.
    """

    def __init__(self, user_message):
        super().__init__(user_message)
        self.user_message = user_message


def _is_playwright_timeout(exc):
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    except Exception:  # pragma: no cover - Playwright is a hard dependency
        return False
    return isinstance(exc, PlaywrightTimeoutError)


def friendly_navigation_error(exc):
    """Map a navigation exception onto a user-facing message."""
    text = str(exc).upper()
    if any(code in text for code in DNS_ERROR_CODES):
        return MESSAGE_DNS
    if any(code in text for code in CONNECTION_ERROR_CODES):
        return MESSAGE_CONNECTION
    if _is_playwright_timeout(exc) or any(code in text for code in TIMEOUT_ERROR_CODES):
        return MESSAGE_TIMEOUT
    # Playwright raises a generic Error whose text says "Timeout ... exceeded".
    if 'TIMEOUT' in text:
        return MESSAGE_TIMEOUT
    return MESSAGE_GENERIC


def user_message_for(exc):
    """Return the safest user-facing message for a failed scan.

    Navigation failures carry their own message; URL validation / SSRF
    rejections are ``ValueError`` and already written for people. Everything
    else falls back to a generic sentence so no raw error reaches the UI.
    """
    message = getattr(exc, 'user_message', None)
    if message:
        return message
    if isinstance(exc, ValueError):
        return str(exc) or MESSAGE_GENERIC
    return MESSAGE_GENERIC
