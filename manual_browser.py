"""Visible browser for user-operated challenges; available only via SSH tunnel."""
import os
import logging
import signal
import subprocess
import time
from threading import Event

from playwright.sync_api import sync_playwright
from profile_lock import profile_lock


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    monitor_enabled = os.environ.get('SESSION_MONITOR') == '1'
    if monitor_enabled:
        from app import validate_config
        from telegram_summary import send_summary
        from live_monitor import LiveSession
        from variant_checks import configured_sizes, check_sizes
        from product_checks import configured_products
        cfg = dict(os.environ)
        interval = validate_config(cfg)
        products = configured_products(cfg)
        verify_s_once = cfg.get('VERIFY_S_ONCE') == '1'
    url = os.environ.get('PRODUCT_URL', '')
    if not url.startswith('https://www.hollisterco.com/shop/'):
        raise SystemExit('PRODUCT_URL must be a Hollister shop HTTPS URL')
    stop = Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    children = []
    with profile_lock(os.environ.get('BROWSER_PROFILE_DIR', '/data/browser-profile')):
        try:
            children.append(subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1440x1000x24', '-nolisten', 'tcp']))
            deadline = time.monotonic() + 15
            while subprocess.run(['xdpyinfo', '-display', ':99'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
                if children[0].poll() is not None or time.monotonic() > deadline or stop.wait(0.2):
                    raise RuntimeError('Display konnte nicht gestartet werden')
            children.append(subprocess.Popen(['x11vnc', '-display', ':99', '-localhost', '-rfbport', '5900', '-forever', '-shared', '-nopw']))
            children.append(subprocess.Popen(['websockify', '--web=/usr/share/novnc', '6080', '127.0.0.1:5900']))
            with sync_playwright() as p:
                options = {'headless': False, 'locale': 'de-DE', 'timezone_id': 'Europe/Berlin',
                           'viewport': {'width': 1400, 'height': 900}}
                if os.environ.get('BROWSER_EXECUTABLE_PATH'):
                    options['executable_path'] = os.environ['BROWSER_EXECUTABLE_PATH']
                context = p.chromium.launch_persistent_context(os.environ.get('BROWSER_PROFILE_DIR', '/data/browser-profile'), **options)
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    try:
                        page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    except Exception:
                        print('Navigation nicht abgeschlossen; Browser kann manuell bedient werden.', flush=True)
                    print('Manueller Browser bereit. noVNC nur über den SSH-Tunnel öffnen. Zum Speichern: Container stoppen.', flush=True)
                    sessions = []
                    if monitor_enabled:
                        for index, product in enumerate(products):
                            product_page = page if index == 0 else context.new_page()
                            product_session = LiveSession(product_page, product)
                            product_session.refresh_next = index > 0
                            sessions.append(product_session)
                    session = sessions[0] if sessions else None
                    next_check = time.monotonic()
                    if session:
                        logging.info('session_monitor_started interval=%s browser_lifetime=continuous', interval)
                    while not stop.is_set() and context.pages:
                        if any(child.poll() is not None for child in children):
                            raise RuntimeError('Eine Desktop-Komponente wurde beendet')
                        if session and time.monotonic() >= next_check:
                            started = time.monotonic()
                            results = []
                            for product_session in sessions:
                                product_session.recover_closed_page(context)
                                product_session.adopt_product_page(context.pages)
                                product = product_session.cfg
                                cycle_sizes = configured_sizes(product)
                                if verify_s_once and 'S' not in cycle_sizes:
                                    cycle_sizes.append('S')
                                for variant_cfg, status, reason in check_sizes(product_session, product, cycle_sizes):
                                    results.append((variant_cfg, status, reason))
                            send_summary(cfg, results)
                            verify_s_once = False
                            next_check = max(started + interval, time.monotonic() + 1)
                        # Pump Playwright events using a surviving tab, not a
                        # stale product-page reference that may have closed.
                        open_pages = [tab for tab in context.pages if not tab.is_closed()]
                        if open_pages:
                            open_pages[0].wait_for_timeout(500)
                finally:
                    context.close()
        finally:
            for child in reversed(children):
                if child.poll() is None:
                    child.terminate()
            for child in reversed(children):
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


if __name__ == '__main__':
    main()
