"""
QuantCore - 高性能量化交易平台
支持 python -m quantcore start 一键启动
"""
import sys
import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)


def main():
    """QuantCore CLI 入口"""
    import argparse
    parser = argparse.ArgumentParser(description="QuantCore 量化交易平台")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="启动 QuantCore 服务")
    start_parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    start_parser.add_argument("--port", type=int, default=8080, help="监听端口")
    start_parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    start_parser.add_argument("--reload", action="store_true", help="开发模式热重载")

    test_parser = subparsers.add_parser("test", help="运行测试套件")
    test_parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")

    check_parser = subparsers.add_parser("check", help="类型检查")
    check_parser.add_argument("--strict", action="store_true", help="严格模式")

    args = parser.parse_args()

    if args.command == "start":
        _start_server(args)
    elif args.command == "test":
        _run_tests(args)
    elif args.command == "check":
        _run_typecheck(args)
    else:
        parser.print_help()


def _start_server(args):
    """启动服务"""
    import logging
    import signal
    import subprocess
    import threading
    import time
    import webbrowser
    from pathlib import Path

    base_dir = Path(_BASE_DIR)
    os.chdir(base_dir)

    from core.logger import setup_logger
    setup_logger(logging.INFO)
    logger = logging.getLogger("quantcore")

    logger.info("🚀 QuantCore 启动中...")

    frontend_proc = [None]

    def start_frontend():
        frontend_dir = base_dir / "frontend"
        if not frontend_dir.exists():
            logger.warning("frontend 目录不存在，跳过前端启动")
            return
        try:
            frontend_proc[0] = subprocess.Popen(
                ["npx", "vite", "--host", "0.0.0.0"],
                cwd=str(frontend_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("前端开发服务器已启动 (http://localhost:3000)")
        except Exception as e:
            logger.warning(f"启动前端失败: {e}")

    def open_browser():
        time.sleep(3)
        if not args.no_browser:
            webbrowser.open(f"http://localhost:{args.port}")

    def stop_frontend():
        if frontend_proc[0]:
            frontend_proc[0].terminate()
            frontend_proc[0].wait(timeout=5)

    shutdown_event = threading.Event()

    def _watch_shutdown():
        shutdown_event.wait()
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=start_frontend, daemon=True).start()
    if not args.no_browser:
        threading.Thread(target=open_browser, daemon=True).start()
    threading.Thread(target=_watch_shutdown, daemon=True).start()

    import uvicorn
    from main import app

    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="warning",
        )
    finally:
        stop_frontend()


def _run_tests(args):
    """运行测试"""
    cmd = ["python", "-m", "pytest", "tests/", "-v"]
    if args.coverage:
        cmd.extend(["--cov=core", "--cov=api", "--cov-report=term-missing"])
    os.execvp("python", cmd)


def _run_typecheck(args):
    """运行类型检查"""
    cmd = ["python", "-m", "mypy", "core/", "api/"]
    if args.strict:
        cmd.append("--strict")
    os.execvp("python", cmd)


if __name__ == "__main__":
    main()
