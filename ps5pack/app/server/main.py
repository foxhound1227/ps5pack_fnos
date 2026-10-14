#!/usr/bin/env python3
"""
PS5 Game AMPR LZ4 Web Service
=============================
提供图形化 API 与静态页面服务，原生支持飞牛 OS 统一网关 (Unix Domain Socket) 与标准 HTTP 端口。
"""

import os
import sys
import time
import json
import socket
import socketserver
import argparse
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Any, Optional, List

from compressor import compressor_manager

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
GITHUB_REPO = "foxhound1227/ps5pack_fnos"
UPDATE_CACHE = {"timestamp": 0, "data": None}

def get_app_version() -> str:
    """读取 manifest 中的版本号"""
    curr = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        cand = os.path.join(curr, "manifest")
        if os.path.isfile(cand):
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("version="):
                            return line.strip().split("=", 1)[1]
            except Exception:
                pass
        curr = os.path.dirname(curr)
    return "1.2.0"

class AppRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def address_string(self):
        # 兼容 Unix Domain Socket 请求，防止缺少 (host, port) 元组导致异常
        if isinstance(self.client_address, (list, tuple)) and len(self.client_address) >= 1:
            return str(self.client_address[0])
        return "unix-client"

    def log_message(self, format, *args):
        # 过滤轮询接口日志，避免终端刷屏
        if "/api/status" not in self.path and "/api/task/logs" not in self.path:
            super().log_message(format, *args)

    def _strip_gateway_prefix(self, path: str) -> str:
        # 兼容飞牛统一网关前缀 /app/ps5pack
        for prefix in ["/app/ps5pack", "/cgi/ThirdParty/ps5pack"]:
            if path.startswith(prefix):
                path = path[len(prefix):]
                if not path.startswith("/"):
                    path = "/" + path
                break
        return path

    def _send_json(self, data: Any, code: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Trim-Userid")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Trim-Userid")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        raw_path = parsed.path
        clean_path = self._strip_gateway_prefix(raw_path)
        query = urllib.parse.parse_qs(parsed.query)

        # API 路由
        if clean_path == "/api/status":
            with compressor_manager.lock:
                state = dict(compressor_manager.task_state)
                # 实时动态计算已用秒数，避免永远停留在 0s
                if state["start_time"] > 0 and state["status"] not in ("idle", "completed", "failed", "stopped"):
                    state["elapsed"] = int(time.time() - state["start_time"])
                # 状态轮询时不传海量 logs，加快响应速度
                state.pop("logs", None)
            
            user_info = {
                "uid": self.headers.get("x-trim-userid", "local"),
                "username": self.headers.get("x-trim-username", "Guest"),
                "is_admin": self.headers.get("x-trim-isadmin") == "true"
            }
            last_paths = compressor_manager.load_last_paths()
            return self._send_json({"task": state, "user": user_info, "last_paths": last_paths})

        elif clean_path == "/api/task/logs":
            with compressor_manager.lock:
                logs = list(compressor_manager.task_state["logs"])
                status = compressor_manager.task_state["status"]
            return self._send_json({"logs": logs, "status": status})

        elif clean_path == "/api/task/history":
            limit_param = query.get("limit", ["5"])[0]
            try:
                limit_val = int(limit_param)
            except Exception:
                limit_val = 5
            history = compressor_manager.load_history(limit=limit_val)
            return self._send_json(history)

        elif clean_path == "/api/browse":
            target_path = query.get("path", [""])[0]
            data = compressor_manager.browse_fs(target_path)
            return self._send_json(data)

        elif clean_path == "/api/task/output_files":
            out_dir = query.get("out_path", [""])[0]
            files = compressor_manager.list_output_files(out_dir)
            return self._send_json({"files": files})

        elif clean_path == "/api/version":
            return self._send_json({
                "version": get_app_version(),
                "repo": GITHUB_REPO,
                "releases_url": f"https://github.com/{GITHUB_REPO}/releases"
            })

        elif clean_path == "/api/check_update":
            current_ver = get_app_version()
            now = time.time()
            # 缓存 10 分钟 (600秒)
            if UPDATE_CACHE["data"] and (now - UPDATE_CACHE["timestamp"] < 600):
                data = dict(UPDATE_CACHE["data"])
                data["current_version"] = current_ver
                return self._send_json(data)

            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ps5pack-update-checker",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=6) as resp:
                    rel = json.loads(resp.read().decode("utf-8"))
                    latest_tag = rel.get("tag_name", "")
                    latest_ver = latest_tag.lstrip("v")
                    download_url = ""
                    for asset in rel.get("assets", []):
                        if asset.get("name") == "ps5pack.fpk":
                            download_url = asset.get("browser_download_url", "")
                            break
                    if not download_url:
                        download_url = rel.get("html_url", f"https://github.com/{GITHUB_REPO}/releases")

                    res = {
                        "success": True,
                        "current_version": current_ver,
                        "latest_version": latest_ver,
                        "tag_name": latest_tag,
                        "release_name": rel.get("name", latest_tag),
                        "release_body": rel.get("body", ""),
                        "published_at": rel.get("published_at", ""),
                        "html_url": rel.get("html_url", ""),
                        "download_url": download_url
                    }
                    UPDATE_CACHE["timestamp"] = now
                    UPDATE_CACHE["data"] = res
                    return self._send_json(res)
            except Exception as e:
                return self._send_json({
                    "success": False,
                    "current_version": current_ver,
                    "error": str(e),
                    "releases_url": f"https://github.com/{GITHUB_REPO}/releases"
                })

        # 静态文件或默认主页
        if clean_path in ("", "/", "/index.html"):
            self.path = "/index.html"
            return super().do_GET()
        
        # 其它静态资源 (CSS / JS / 图标等)
        self.path = clean_path
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        clean_path = self._strip_gateway_prefix(parsed.path)

        length = int(self.headers.get("Content-Length", 0))
        post_data = {}
        if length > 0:
            try:
                body = self.rfile.read(length).decode("utf-8")
                post_data = json.loads(body)
            except Exception:
                post_data = {}

        if clean_path == "/api/check_leaf":
            path_to_check = post_data.get("path", "")
            res = compressor_manager.inspect_leaf(path_to_check)
            return self._send_json(res)

        elif clean_path == "/api/save_paths":
            src = post_data.get("src", "")
            out = post_data.get("out", "")
            compressor_manager.save_last_paths(src, out)
            return self._send_json({"success": True})

        elif clean_path == "/api/task/start":
            res = compressor_manager.start_task(post_data)
            return self._send_json(res)

        elif clean_path == "/api/task/stop":
            res = compressor_manager.stop_task()
            return self._send_json(res)

        self._send_json({"error": "Not Found"}, 404)

class UnixThreadingHTTPServer(ThreadingHTTPServer):
    address_family = getattr(socket, "AF_UNIX", socket.AF_INET)

    def server_bind(self):
        # 重写 server_bind，避免 socketserver 解构 (host, port) 时将 Unix 路径当元组崩溃
        socketserver.TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = 80

def run_server(socket_path: Optional[str] = None, port: int = 8080):
    if socket_path and hasattr(socket, "AF_UNIX"):
        try:
            if os.path.exists(socket_path):
                os.remove(socket_path)
            
            server = UnixThreadingHTTPServer(socket_path, AppRequestHandler)
            try:
                os.chmod(socket_path, 0o777)
            except Exception:
                pass
            print(f"[ps5pack] Listening on Unix Socket: {socket_path}")
            server.serve_forever()
            return
        except Exception as e:
            print(f"[ps5pack] Failed to bind Unix Socket: {e}. Fallback to TCP port.")

    # TCP 端口模式
    server = ThreadingHTTPServer(("0.0.0.0", port), AppRequestHandler)
    print(f"[ps5pack] Listening on TCP http://0.0.0.0:{port}")
    server.serve_forever()

if __name__ == "__main__":
    raw_port = os.environ.get("TRIM_SERVICE_PORT", "").strip()
    default_port = int(raw_port) if raw_port.isdigit() else 58888

    parser = argparse.ArgumentParser(description="PS5 AMPR LZ4 Compressor Service")
    parser.add_argument("--socket", type=str, default="", help="Unix domain socket path")
    parser.add_argument("--port", type=int, default=default_port, help="TCP port")
    parser.add_argument("--data", type=str, default="", help="Data directory")
    args = parser.parse_args()

    # 优先环境变量
    socket_path = args.socket or os.environ.get("SOCKET_PATH", "")
    port = args.port

    data_dir = args.data or os.environ.get("TRIM_PKGVAR", "")
    if data_dir:
        compressor_manager.data_dir = data_dir
        compressor_manager.history_file = os.path.join(data_dir, "history.json")

    run_server(socket_path=socket_path if socket_path else None, port=port)
