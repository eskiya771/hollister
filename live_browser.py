"""User-operated browser on the NAS; never solves a challenge automatically."""
import os
import logging
from pathlib import Path
import signal
import subprocess
import threading
import time

from playwright.sync_api import sync_playwright
from app import validate_config, send_status
from live_monitor import LiveSession

STOP = threading.Event()
URL = 'https://www.hollisterco.com/shop/eu-de/p/henley-mit-leopardenprint-und-logo-63757420?faceout=model&seq=08&gridProductPosition=1'


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    cfg = dict(os.environ)
    live_enabled = cfg.get('LIVE_MONITOR') == '1'
    interval = validate_config(cfg) if live_enabled else 60
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.set())
    processes = []
    context = None

    def start(args):
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(process)
        return process

    try:
        display = start(['Xvfb', ':99', '-screen', '0', '1366x900x24', '-nolisten', 'tcp'])
        deadline = time.monotonic() + 15
        while not Path('/tmp/.X11-unix/X99').exists():
            if display.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError('X display did not start')
            time.sleep(0.1)
        start(['openbox'])
        start(['x11vnc', '-display', ':99', '-listen', '127.0.0.1', '-rfbport', '5900',
               '-forever', '-shared', '-nopw', '-noxdamage'])
        start(['/usr/bin/websockify', '--web=/usr/share/novnc', '0.0.0.0:6080', '127.0.0.1:5900'])
        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    os.environ.get('BROWSER_PROFILE_DIR', '/data/browser-profile'),
                    headless=False, locale='de-DE', timezone_id='Europe/Berlin',
                    viewport={'width': 1280, 'height': 800}, timeout=30000)
                page = context.pages[0] if context.pages else context.new_page()
                try:
                    page.goto(cfg.get('PRODUCT_URL', URL), wait_until='domcontentloaded', timeout=60000)
                except Exception as exc:
                    print('Initial navigation:', type(exc).__name__, '; retry manually in the browser.', flush=True)
                print('manual_browser_ready: open noVNC through the SSH tunnel.', flush=True)
                session = LiveSession(page, cfg) if live_enabled else None
                next_check = time.monotonic()
                if live_enabled:
                    logging.info('Live-Monitor gestartet; Intervall=%ss, Browsersitzung bleibt geöffnet', interval)
                while not STOP.is_set():
                    if any(process.poll() is not None for process in processes):
                        raise RuntimeError('Display service stopped')
                    if not context.pages:
                        raise RuntimeError('User closed the browser')
                    if session and time.monotonic() >= next_check:
                        started = time.monotonic()
                        session.adopt_product_page(context.pages)
                        status, reason = session.check()
                        send_status(cfg, status, reason)
                        next_check = max(started + interval, time.monotonic() + 1)
                    (session.page if session else context.pages[0]).wait_for_timeout(250)
            finally:
                if context:
                    context.close()
                    print('manual_profile_closed_cleanly', flush=True)
    except Exception as exc:
        print('manual_browser_failed:', type(exc).__name__, flush=True)
        return 1
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
