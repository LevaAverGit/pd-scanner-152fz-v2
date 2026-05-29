"""
Minimal local HTTP server for synthetic submission verification.

Serves:
  GET  /           → HTML page with a first-party form (action="/submit")
  GET  /blocked    → HTML page with a form behind CAPTCHA (g-recaptcha div present)
  POST /submit     → accepts submission, returns 200 JSON
  GET  /third      → HTML page with a form pointing to a different host pattern

Usage:
    server = FormFixtureServer()
    server.start()
    base_url = server.base_url  # e.g. "http://127.0.0.1:PORT"
    # ... run scan ...
    server.stop()
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs


_FORM_PAGE_HTML = """<!DOCTYPE html>
<html>
<head><title>Test Form</title></head>
<body>
<h1>Contact Us</h1>
<form id="contact" action="/submit" method="post">
  <label for="name">Full Name</label>
  <input type="text" id="name" name="name" required>
  <label for="email">Email</label>
  <input type="email" id="email" name="email" required>
  <label for="phone">Phone</label>
  <input type="tel" id="phone" name="phone">
  <label for="message">Message</label>
  <textarea id="message" name="message"></textarea>
  <button type="submit">Send Message</button>
</form>
<a href="/privacy">Privacy Policy</a>
<a href="/terms">Terms of Service</a>
</body>
</html>
"""

_CAPTCHA_PAGE_HTML = """<!DOCTYPE html>
<html>
<body>
<form action="/submit" method="post">
  <input type="email" name="email">
  <div class="g-recaptcha" data-sitekey="fake-key"></div>
  <button type="submit">Submit</button>
</form>
</body>
</html>
"""

_SUCCESS_HTML = """<!DOCTYPE html>
<html><body><h1>Thank you!</h1><p>Form submitted successfully.</p></body></html>"""

_EXPLICIT_CONSENT_PAGE_HTML = """<!DOCTYPE html>
<html>
<head><title>Registration</title></head>
<body>
<h1>Create Account</h1>
<form action="/submit" method="post">
  <label for="ename">Full Name</label>
  <input type="text" id="ename" name="name" required>
  <label for="eemail">Email</label>
  <input type="email" id="eemail" name="email" required>
  <div>
    <input type="checkbox" id="privacy_cb" name="privacy_consent" required>
    <label for="privacy_cb">I agree to the <a href="/privacy">Privacy Policy</a></label>
  </div>
  <button type="submit">Register</button>
</form>
<a href="/privacy">Privacy Policy</a>
<a href="/terms">Terms of Service</a>
</body>
</html>
"""

_WEBHOOK_FORM_HTML = """<!DOCTYPE html>
<html>
<head><title>Demo Request</title></head>
<body>
<h1>Request a Demo</h1>
<form action="/api/lead" method="post">
  <label for="wname">Full Name</label>
  <input type="text" id="wname" name="name" required>
  <label for="wemail">Email</label>
  <input type="email" id="wemail" name="email" required>
  <input type="hidden" name="portalId" value="12345">
  <input type="hidden" name="hs_context" value="{}">
  <button type="submit">Request Demo</button>
</form>
<a href="/privacy">Privacy Policy</a>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silence server logs

    def do_GET(self):
        if self.path == "/":
            self._send(200, "text/html", _FORM_PAGE_HTML.encode())
        elif self.path == "/blocked":
            self._send(200, "text/html", _CAPTCHA_PAGE_HTML.encode())
        elif self.path == "/webhook-form":
            self._send(200, "text/html", _WEBHOOK_FORM_HTML.encode())
        elif self.path == "/consent-explicit":
            self._send(200, "text/html", _EXPLICIT_CONSENT_PAGE_HTML.encode())
        elif self.path in ("/privacy", "/terms"):
            self._send(200, "text/html", b"<html><body>Policy page</body></html>")
        else:
            self._send(404, "text/plain", b"Not found")

    def do_POST(self):
        if self.path == "/submit":
            length = int(self.headers.get("Content-Length", 0))
            _ = self.rfile.read(length)  # consume body but do not store it
            self._send(200, "application/json", json.dumps({"ok": True}).encode())
        elif self.path == "/api/lead":
            length = int(self.headers.get("Content-Length", 0))
            _ = self.rfile.read(length)  # consume but don't store
            self._send(200, "application/json", json.dumps({"ok": True, "lead": "captured"}).encode())
        else:
            self._send(404, "text/plain", b"Not found")

    def _send(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class FormFixtureServer:
    """
    Threaded local HTTP fixture server used by synthetic submission tests.
    Not a test class — named without 'Test' prefix to avoid pytest collection warnings.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self._server = HTTPServer((host, port), _Handler)
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()


# Backwards-compatible alias (do not use in new code)
TestFormServer = FormFixtureServer
