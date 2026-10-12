"""External downloads connect to validated addresses to avoid DNS rebinding."""
import ipaddress
import os
import socket
from urllib.parse import urljoin, urlsplit
import urllib3

MAX_BYTES = 10 * 1024 * 1024

def destination(url):
    parsed = urlsplit(url)
    allowed = set(filter(None, os.getenv("ODIP_SOURCE_HOSTS", "jsonplaceholder.typicode.com,ec.europa.eu,re.jrc.ec.europa.eu").split(",")))
    if parsed.scheme != "https" or not parsed.hostname or parsed.hostname not in allowed or parsed.port not in (None, 443) or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Source destination is not approved")
    addresses = sorted({item[4][0] for item in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Source address is not public")
    return parsed, addresses[0]

def download(url):
    for _ in range(6):
        parsed, address = destination(url)
        pool = urllib3.HTTPSConnectionPool(address, port=443, assert_hostname=parsed.hostname, server_hostname=parsed.hostname, maxsize=1)
        response = None
        try:
            target = (parsed.path or "/") + (("?" + parsed.query) if parsed.query else "")
            response = pool.urlopen("GET", target, headers={"Host": parsed.hostname, "Accept-Encoding": "identity"}, redirect=False, preload_content=False, retries=False, timeout=urllib3.Timeout(connect=10, read=30))
            if response.status in (301,302,303,307,308):
                location = response.headers.get("Location")
                if not location: raise ValueError("Source redirect is invalid")
                url = urljoin(url, location)
                continue
            if response.status != 200: raise ValueError("Source request failed")
            if response.headers.get("Content-Encoding", "identity") != "identity": raise ValueError("Compressed sources are unsupported")
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if content_type not in ("application/json", "application/ld+json", "text/csv", "application/csv") and not content_type.endswith("+json"):
                raise ValueError("Source content type is unsupported")
            if int(response.headers.get("Content-Length", "0")) > MAX_BYTES: raise ValueError("Source exceeds the byte limit")
            payload = bytearray()
            for chunk in response.stream(65536, decode_content=False):
                if len(payload) + len(chunk) > MAX_BYTES: raise ValueError("Source exceeds the byte limit")
                payload.extend(chunk)
            return bytes(payload), content_type, response.headers.get("ETag")
        finally:
            if response is not None: response.close()
            pool.close()
    raise ValueError("Source redirect limit exceeded")
