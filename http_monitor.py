"""Automatic two-product monitor, independent of Chromium and its profile."""
import argparse
import logging
import os
import signal
import threading
import time
from zoneinfo import ZoneInfo
from app import load_env, LOG
from http_stock import check_all
from telegram_summary import send_summary

STOP = threading.Event()


def validate(cfg, require_telegram=True):
    if require_telegram:
        missing = [key for key in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID') if not cfg.get(key)]
        if missing:
            raise ValueError('Fehlende Einstellungen: ' + ', '.join(missing))
    try:
        interval = int(cfg.get('CHECK_INTERVAL_SECONDS', '60'))
        age = int(cfg.get('HTTP_MAX_CACHE_AGE_SECONDS', '900'))
        ZoneInfo(cfg.get('TZ', 'Europe/Berlin'))
    except Exception:
        raise ValueError('Intervall, Cache-Alter oder Zeitzone ungültig.') from None
    if interval < 60 or not 0 <= age <= 900:
        raise ValueError('Intervall mindestens 60 Sekunden; Cache-Alter zwischen 0 und 900.')
    return interval


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    load_env()
    cfg = dict(os.environ)
    try:
        interval = validate(cfg, not args.check_only)
    except ValueError as exc:
        parser.error(str(exc))
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.set())
    LOG.info('HTTP-Monitor gestartet; erste Abfrage sofort, Intervall=%ss', interval)
    while not STOP.is_set():
        started = time.monotonic()
        results = check_all(cfg)
        if args.check_only:
            for variant, status, reason in results:
                LOG.info('stock_check product=%s size=%s status=%s reason=%s',
                         variant['PRODUCT_NAME'], variant['PRODUCT_SIZE'], status, reason)
            return 2 if any(status == 'unknown' for _, status, _ in results) else 0
        delivered = send_summary(cfg, results)
        if args.once:
            return 1 if not delivered else (2 if any(s == 'unknown' for _, s, _ in results) else 0)
        STOP.wait(max(0, interval - (time.monotonic() - started)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
