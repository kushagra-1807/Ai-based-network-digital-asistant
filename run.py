#!/usr/bin/env python3

import argparse
import sys
import time

from netassist.config import Config
from netassist.factory import build
from netassist.simulator import scenarios


def make_cfg(args):
    cfg = Config()
    cfg.capacity_mbps = args.capacity
    cfg.interval_sec = args.interval if args.interval else (5.0 if args.live else 1.0)
    cfg.scan_method = args.scan
    if args.gateway:
        cfg.gateway = args.gateway
    if args.target:
        cfg.ping_target = args.target
    cfg.db_path = args.db or ("netassist.db" if args.live else ":memory:")
    return cfg


def make_stack(args):
    cfg = make_cfg(args)
    return build(cfg, simulate=not args.live, seed=args.seed, use_ml=args.ml)


def cmd_web(args):
    from netassist.webapp import create_app
    service, assistant = make_stack(args)
    for _ in range(25):
        service.tick_once()
    service.start()
    app = create_app(service, assistant)
    mode = "LIVE network" if args.live else "SIMULATION"
    print("\n  %s mode. Open http://127.0.0.1:%d in your browser (Ctrl+C to stop)\n" % (mode, args.port))
    try:
        app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)
    finally:
        service.stop()


def cmd_monitor(args):
    service, _ = make_stack(args)
    n = 0
    print("Collecting every %.0fs (%s). Ctrl+C to stop.\n" % (service.cfg.interval_sec, service.mode))
    try:
        while args.count == 0 or n < args.count:
            s, anomalies = service.tick_once()
            n += 1
            print(time.strftime("%H:%M:%S"), "| down %.1f Mbps  up %.1f Mbps  latency router %s / internet %s  loss %.1f%%  devices %d"
                  % (s.down_mbps, s.up_mbps,
                     "%.1f ms" % s.latency_gw_ms if s.latency_gw_ms is not None else "n/a",
                     "%.0f ms" % s.latency_net_ms if s.latency_net_ms is not None else "n/a",
                     s.loss_pct, len(s.devices)))
            for d in s.devices:
                traffic = "traffic n/a" if d.down_mbps is None else "%.1f Mbps down" % d.down_mbps
                print("    %-24s %-15s %s" % (d.name, d.ip, traffic))
            for a in anomalies:
                print("    [%s] %s" % (a.severity.upper(), a.message))
            time.sleep(service.cfg.interval_sec)
    except KeyboardInterrupt:
        pass


def cmd_chat(args):
    service, assistant = make_stack(args)
    for _ in range(25):
        service.tick_once()
    service.start()
    print("Network assistant (%s mode). Type a question, or /help." % service.mode)
    if service.mode == "simulation":
        print("Inject a problem with /scenario <name>. Names: %s" % ", ".join(scenarios()))
    try:
        while True:
            try:
                line = input("\nyou> ").strip()
            except EOFError:
                break
            if line in ("/quit", "/exit"):
                break
            if line.startswith("/scenario") and service.mode == "simulation":
                name = line.split(maxsplit=1)[1] if " " in line else "normal"
                try:
                    service.source.set_scenario(name)
                    print("scenario set to %s (give it a few seconds to be detected)" % name)
                except ValueError:
                    print("unknown scenario")
                continue
            if line == "/help":
                line = "help"
            r = assistant.chat("cli", line)
            print("\nassistant>", r["reply"])
    finally:
        service.stop()


def cmd_evaluate(args):
    from netassist.evaluation import run_all
    run_all(trials=args.trials, out_dir="docs")


def cmd_speedtest(args):
    from netassist.collector import measure_capacity
    mbps = measure_capacity()
    if mbps is None:
        print("Could not run a speed test. Install it with: pip install speedtest-cli")
    else:
        print("Download capacity ~ %.0f Mbps. Use it with: python run.py web --live --capacity %.0f" % (mbps, mbps))


def main():
    ap = argparse.ArgumentParser(description="AI-Based Network Digital Assistant")
    ap.add_argument("command", nargs="?", default="web", choices=["web", "monitor", "chat", "evaluate", "speedtest"])
    ap.add_argument("--live", action="store_true", help="use the real network instead of the simulator")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--capacity", type=float, default=100.0, help="link capacity in Mbps (for utilisation)")
    ap.add_argument("--interval", type=float, default=0.0, help="seconds between readings")
    ap.add_argument("--gateway", help="router IP (auto-detected if omitted)")
    ap.add_argument("--target", help="host to ping for internet latency (default 8.8.8.8)")
    ap.add_argument("--scan", choices=["arp", "nmap", "scapy"], default="arp", help="device discovery method (live mode)")
    ap.add_argument("--ml", action="store_true", help="enable the IsolationForest detector (needs scikit-learn)")
    ap.add_argument("--db", help="SQLite file (default: in-memory for the simulator, netassist.db for live)")
    ap.add_argument("--seed", type=int, default=None, help="random seed for the simulator")
    ap.add_argument("--count", type=int, default=0, help="monitor: stop after N readings")
    ap.add_argument("--trials", type=int, default=15, help="evaluate: trials per scenario")
    args = ap.parse_args()
    {"web": cmd_web, "monitor": cmd_monitor, "chat": cmd_chat, "evaluate": cmd_evaluate, "speedtest": cmd_speedtest}[args.command](args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
