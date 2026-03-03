#!/usr/bin/env python3
"""
启动正式版微信公众号PDF服务（默认）
- 默认启动 src/app_pro.py（真实抓取 + 真实PDF）
- 仅在显式 --demo 参数时才启动简化演示服务
"""

import os
import sys
import socket
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def find_free_port(preferred_ports=(8080, 8081, 5000, 18080)):
    for p in preferred_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    # 兜底随机端口
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_pro_server(port: int):
    """启动正式版 Flask 服务"""
    venv_python = ROOT / "venv" / "bin" / "python3"
    py = str(venv_python if venv_python.exists() else Path(sys.executable))

    env = os.environ.copy()
    env.setdefault("PORT", str(port))
    env.setdefault("HOST", "0.0.0.0")
    env.setdefault("DEBUG", "false")

    cmd = [py, str(ROOT / "src" / "app_pro.py")]

    print("🚀 启动【正式版】微信公众号PDF服务...")
    print("✅ 模式: PRO（真实抓取 + 真实PDF，非演示）")
    print(f"📡 前端: http://localhost:{port}/")
    print(f"📊 状态: http://localhost:{port}/api/status")
    print("🔧 按 Ctrl+C 停止")
    print("=" * 60)

    subprocess.run(cmd, env=env, cwd=str(ROOT), check=False)


def run_demo_server(port: int):
    """仅在显式 --demo 时启动"""
    from start_simple_server import SimplePDFHandler
    from http.server import HTTPServer

    print("⚠️ 启动【演示版】服务（仅用于UI演示）")
    print("⚠️ 该模式不用于生产，不保证真实抓取")
    print(f"📡 前端: http://localhost:{port}/")
    print(f"📊 状态: http://localhost:{port}/api/status")
    print("=" * 60)

    httpd = HTTPServer(("", port), SimplePDFHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    demo_mode = "--demo" in sys.argv

    # 支持传入端口：python start_server.py 19000
    cli_port = None
    for arg in sys.argv[1:]:
        if arg.isdigit():
            cli_port = int(arg)
            break

    port = cli_port or find_free_port()

    if demo_mode:
        run_demo_server(port)
    else:
        run_pro_server(port)
