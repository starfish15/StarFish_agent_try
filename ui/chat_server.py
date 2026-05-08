import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UI_DIR = os.path.join(ROOT_DIR, "ui")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from agent.core import Agent


def _guess_content_type(path: str) -> str:
    if path.endswith(".html"):
        return "text/html; charset=utf-8"
    if path.endswith(".css"):
        return "text/css; charset=utf-8"
    if path.endswith(".js"):
        return "application/javascript; charset=utf-8"
    if path.endswith(".json"):
        return "application/json; charset=utf-8"
    return "application/octet-stream"


class ChatHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            return self._send_file(os.path.join(UI_DIR, "chat_ui.html"))

        if path in {"/chat_ui.css", "/chat_ui.js"}:
            return self._send_file(os.path.join(UI_DIR, path.lstrip("/")))

        self.send_error(404, "Not Found")

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/chat":
            return self._handle_chat()

        if path == "/shutdown":
            return self._handle_shutdown()

        self.send_error(404, "Not Found")

    def _handle_chat(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except json.JSONDecodeError:
            return self._send_json({"error": "Invalid JSON"}, status=400)

        text = payload.get("text", "")
        if not isinstance(text, str) or not text.strip():
            return self._send_json({"error": "text is required"}, status=400)

        try:
            reply = self.server.agent.run(text)
        except Exception as exc:  # keep server alive on LLM errors
            return self._send_json({"error": str(exc)}, status=500)

        self.server.history.append({"role": "user", "content": text})
        self.server.history.append({"role": "assistant", "content": reply})

        return self._send_json(
            {
                "reply": reply,
                "history": self.server.history,
            },
            status=200,
        )

    def _handle_shutdown(self):
        self._send_json({"ok": True}, status=200)

        def _shutdown():
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass

        threading.Thread(target=_shutdown, daemon=True).start()

    def _send_file(self, file_path: str):
        if not os.path.isfile(file_path):
            self.send_error(404, "Not Found")
            return

        with open(file_path, "rb") as f:
            body = f.read()

        self.send_response(200)
        self._set_cors()
        self.send_header("Content-Type", _guess_content_type(file_path))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self._set_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _set_cors(self):
        # 允许直接用浏览器打开/跨域调试（同源访问也不会受影响）
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def main():
    host = "0.0.0.0"
    port = 8002

    server = HTTPServer((host, port), ChatHandler)
    server.agent = Agent()
    server.history = []

    print(f"Chat server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
