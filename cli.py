"""
resonance_ng CLI entry point.

Usage:
  python cli.py scan                  # Scan for emulators
  python cli.py connect --port 16384  # Test ADB connection
  python cli.py screenshot             # Take a test screenshot
  python cli.py benchmark-screenshot   # Benchmark screenshot backends
  python cli.py start-game             # Start game app
  python cli.py stop-game              # Stop game app
"""

import argparse
import sys

from resonance import logger


def main():
    parser = argparse.ArgumentParser(description="resonance_ng CLI")
    parser.add_argument("command", nargs="?", default="help",
                        choices=["scan", "connect", "screenshot", "benchmark-screenshot", "start-game", "stop-game", "restart-game", "serve", "help"])
    parser.add_argument("--port", type=int, help="ADB port")
    parser.add_argument("--samples", type=int, default=5, help="Screenshot benchmark samples")
    parser.add_argument("--warmup", type=int, default=1, help="Screenshot benchmark warmup captures")
    parser.add_argument("--apply-fastest", action="store_true", help="Persist fastest screenshot backend")

    args = parser.parse_args()

    if args.command == "help":
        print(__doc__)
        return

    if args.command == "scan":
        from resonance.device.port_scanner import get_adb_port
        emulators = get_adb_port()
        if not emulators:
            logger.info("未检测到运行中的模拟器")
            return
        for emu in emulators:
            logger.info(f"发现: {emu.name} port={emu.port} path={emu.path} type={emu.type.value} index={emu.index}")

    elif args.command == "connect":
        port = args.port
        if not port:
            logger.error("请指定 --port 参数")
            return
        from resonance.device.device import connect
        status = connect(port)
        logger.info(f"连接结果: {'成功' if status else '失败'}")

    elif args.command == "serve":
        from resonance.server.app import app, _register_frontend
        import resonance.server.websocket  # noqa: F401  register /ws route
        from resonance.server.routes import register_blueprints
        register_blueprints(app)
        _register_frontend()
        logger.bind(skip_ws=True).info("启动 Web 服务器: http://localhost:15177")
        logger.bind(skip_ws=True).info("WebSocket 日志+截图推送已启用")
        from resonance.server.app import _frontend_dist
        if _frontend_dist.is_dir() and (_frontend_dist / "index.html").is_file():
            logger.bind(skip_ws=True).info("前端已托管，访问 http://localhost:15177 即可")
        app.run(host="127.0.0.1", port=15177, debug=False, use_reloader=False)

    elif args.command == "screenshot":
        from resonance.device.device import connect, screenshot_image
        from resonance.vision.ocr import predict
        port = args.port
        if not port:
            logger.error("请指定 --port 参数")
            return
        status = connect(port)
        if not status:
            logger.error("连接失败")
            return
        img = screenshot_image()
        results = predict(img)
        logger.info(f"OCR识别到 {len(results)} 条文本")
        for r in results:
            logger.info(f"  {r['text']} (置信度: {r['score']:.2f})")

    elif args.command == "benchmark-screenshot":
        from resonance.device.device import benchmark_screenshot_methods
        result = benchmark_screenshot_methods(
            port=args.port,
            samples=args.samples,
            warmup=args.warmup,
            apply_fastest=args.apply_fastest,
        )
        for item in result["results"]:
            if item["ok"]:
                logger.info(
                    f"{item['method']}: avg={item['avg_ms']}ms min={item['min_ms']}ms max={item['max_ms']}ms samples={item['samples']}"
                )
            else:
                logger.warning(f"{item['method']}: 不可用 ({item['error']})")
        logger.info(f"最快截图方式: {result['fastest'] or '无'}")
        if result["applied"]:
            logger.info("已保存最快截图方式")

    elif args.command in ("start-game", "stop-game", "restart-game"):
        from resonance.device.device import restart_game, start_game, stop_game
        if args.command == "start-game":
            result = start_game()
        elif args.command == "stop-game":
            result = stop_game()
        else:
            result = {"success": restart_game(), "action": "restart"}
        logger.info(result)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
