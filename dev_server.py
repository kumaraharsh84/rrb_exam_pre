from __future__ import annotations

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parent
SERVE_ROOT = PROJECT_ROOT.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import lambda_function  # noqa: E402
import explanation_service  # noqa: E402


class DevServerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SERVE_ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        parsed = urlparse(self.path)
        if parsed.path in {"/api/generate", "/api/explanation"}:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.end_headers()
            return

        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/generate", "/api/explanation"}:
            self.send_error(404, "Not Found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            if not raw_body.strip():
                raw_body = "{}"

            if parsed.path == "/api/explanation":
                payload = json.loads(raw_body)
                explanation_result = explanation_service.get_or_create_explanation(payload)
                status_code = int(explanation_result.get("statusCode", 200))
                response_body = explanation_result.get("body", {})
            else:
                lambda_result = lambda_function.lambda_handler({"body": raw_body}, None)
                status_code = int(lambda_result.get("statusCode", 200))
                response_body = lambda_result.get("body", "{}")

            if isinstance(response_body, bytes):
                response_body = response_body.decode("utf-8")
            elif not isinstance(response_body, str):
                response_body = json.dumps(response_body)

            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.end_headers()
            self.wfile.write(response_body.encode("utf-8"))
        except Exception as error:  # pragma: no cover - dev-server safety net
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "error": "Local dev proxy failed.",
                        "details": str(error),
                    }
                ).encode("utf-8")
            )


def main():
    port = int(os.environ.get("RRB_DEV_PORT", "5500"))
    server = ThreadingHTTPServer(("", port), DevServerHandler)

    print()
    print("==============================================")
    print("  RRB AI Practice Center - Local Dev Server")
    print("==============================================")
    print(f"Serving static files from: {SERVE_ROOT}")
    print(f"Frontend URL: http://localhost:{port}/rrb-exam-prep/frontend/login.html")
    print(f"Proxy URL:    http://localhost:{port}/api/generate")
    print(f"Explain URL:  http://localhost:{port}/api/explanation")
    print()
    print("This local server bypasses the broken API Gateway CORS/mapping flow")
    print("and sends quiz requests through backend/lambda_function.py instead.")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local dev server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
