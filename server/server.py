#!/usr/bin/env python3
"""听写纸 · 伴随服务：静态页面 + API 同源代理。

- GET  /*          -> 提供 --dir 下的静态文件（默认为仓库 web/ 目录）
- POST /typesafe   -> 原样转发 https://api.typesafe.ai/v1/systemone
- POST /deepseek   -> 原样转发 https://api.deepseek.com/chat/completions

浏览器把 API Key 放在 Authorization 头里经本服务透传给上游，
密钥只存在浏览器 localStorage，服务端不落盘、不记录。

用法:
    python server.py --port 6008 --dir ../web

仅依赖 Python 3.8+ 标准库。
"""
import argparse
import http.server
import json
import os
import socketserver
import urllib.error
import urllib.request

ROUTES = {
    "/typesafe": "https://api.typesafe.ai/v1/systemone",
    "/deepseek": "https://api.deepseek.com/chat/completions",
}


def make_handler(web_dir: str):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=web_dir, **kwargs)

        def log_message(self, fmt, *args):
            pass  # 静默访问日志，只留错误

        def do_POST(self):
            target = ROUTES.get(self.path.split("?")[0])
            if not target:
                self.send_error(404, "Not Found")
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
            except Exception:
                self.send_error(400, "Bad Request")
                return

            req = urllib.request.Request(
                target, data=body, method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self.headers.get("Authorization", ""),
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data, code = resp.read(), resp.status
            except urllib.error.HTTPError as e:
                data, code = e.read(), e.code
            except Exception as e:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "detail": {"error_type": "proxy_error", "message": str(e)}
                }).encode())
                return

            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    return Handler


def main():
    default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
    parser = argparse.ArgumentParser(description="听写纸静态页 + API 代理服务")
    parser.add_argument("-p", "--port", type=int, default=6008, help="监听端口（默认 6008）")
    parser.add_argument("-d", "--dir", default=default_dir, help="静态文件目录（默认 ../web）")
    args = parser.parse_args()

    class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    print(f"serving {os.path.abspath(args.dir)} on 0.0.0.0:{args.port} (+ POST /typesafe, /deepseek)")
    Server(("0.0.0.0", args.port), make_handler(os.path.abspath(args.dir))).serve_forever()


if __name__ == "__main__":
    main()
