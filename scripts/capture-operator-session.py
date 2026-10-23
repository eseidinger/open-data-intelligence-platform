"""Capture an ODIP browser Cookie header from the Windows clipboard in WSL.

Reads ODIP_API_URL and ODIP_OPERATOR_COOKIE_FILE. Never prints cookie values.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from http.cookiejar import MozillaCookieJar
from http.cookies import SimpleCookie
from urllib.parse import urlsplit


def main():
    try:
        origin = urlsplit(os.environ["ODIP_API_URL"])
        target = Path(os.environ["ODIP_OPERATOR_COOKIE_FILE"])
        if (origin.scheme != "https" or not origin.hostname or origin.username
                or origin.password or origin.path not in ("", "/")
                or origin.query or origin.fragment):
            raise ValueError("ODIP_API_URL must be an HTTPS origin.")
        input("Copy the fresh ODIP request's Cookie header value to the Windows "
              "clipboard, then press Enter without pasting: ")
        raw = subprocess.check_output(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "Get-Clipboard -Raw"], text=True, stderr=subprocess.DEVNULL,
            timeout=15,
        ).strip()
        if not raw or any(c in raw for c in "\r\n\t"):
            raise ValueError("Clipboard must contain only a single-line Cookie header value.")
        cookies = SimpleCookie()
        cookies.load(raw)
        required = {"__Host-platform-session", "__Host-platform-activity",
                    "__Host-platform-csrf"}
        if not required.issubset(cookies) or any(not cookies[k].value for k in required):
            raise ValueError("Missing platform cookies; copy from an authenticated ODIP request.")
        lines = ["# Netscape HTTP Cookie File"]
        for name in sorted(required):
            lines.append("\t".join(
                [origin.hostname, "FALSE", "/", "TRUE", "", name,
                 cookies[name].coded_value]))
        # Validate the exact file format consumed by the publisher before replacing
        # the destination. A private temporary file also avoids following symlinks.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=target.parent,
                                             delete=False) as output:
                temporary = Path(output.name)
                output.write("\n".join(lines) + "\n")
            jar = MozillaCookieJar(str(temporary))
            jar.load(ignore_discard=True)
            if {c.name for c in jar} != required:
                raise ValueError("Unable to encode the captured session cookies.")
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        print("Operator session saved with owner-only permissions. Clear the clipboard.")
        return 0
    except (KeyError, OSError, ValueError, subprocess.SubprocessError, EOFError):
        print("Capture failed. Check the ODIP environment variables, clipboard "
              "contents, destination directory, and WSL PowerShell access.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Capture cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
