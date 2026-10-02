import ipaddress
import re
from urllib.parse import urlparse, urlunparse

PRIVATE_IP_PATTERNS = [
    re.compile(r'^127\.'),
    re.compile(r'^10\.'),
    re.compile(r'^192\.168\.'),
    re.compile(r'^169\.254\.'),
    re.compile(r'^::1$'),
    re.compile(r'^fc00:'),
    re.compile(r'^fd00:'),
    re.compile(r'^fe80:'),
    re.compile(r'^0\.'),
]


def is_private_host(host):
    if not host:
        return True
    host = host.split(':')[0]
    for p in PRIVATE_IP_PATTERNS:
        if p.match(host):
            return True
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return True
    except Exception:
        pass
    blocked = {'localhost', 'metadata.google.internal', '169.254.169.254'}
    if host.lower() in blocked:
        return True
    return False


def normalize_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError('Invalid URL')
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path or '/', '', parsed.query, ''))
