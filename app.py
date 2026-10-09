"""Conservative Hollister checker: only exact variant data establishes stock."""
import argparse
import json
import logging
import os
from pathlib import Path
import re
import signal
import threading
import time
import urllib.request
from datetime import datetime
from html import unescape
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit

STOP = threading.Event()
LOG = logging.getLogger('hollister')


def load_env(path='.env'):
    if Path(path).is_file():
        for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def stock_from_html(html, size, color, sku):
    if re.search(r'<title\b[^>]*>\s*(?:Client Challenge|Access Denied)\s*</title>', html, re.I):
        return 'unknown', 'Hollister liefert eine Schutzseite statt Produktdaten.'
    scripts = re.findall(r'<script\b[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script\s*>', html, re.I | re.S)
    variants = []

    def visit(obj):
        if isinstance(obj, list):
            for item in obj:
                visit(item)
        elif isinstance(obj, dict):
            typ = obj.get('@type', [])
            if isinstance(typ, str):
                typ = [typ]
            if 'Product' in typ and str(obj.get('sku', '')) == sku and str(obj.get('size', '')).casefold() == size.casefold() and str(obj.get('color', '')).casefold() == color.casefold():
                offers = obj.get('offers', [])
                if isinstance(offers, dict):
                    offers = [offers]
                states = {o.get('availability', '').rsplit('/', 1)[-1] for o in offers if isinstance(o, dict)}
                if states == {'InStock'}:
                    variants.append('available')
                elif states and states <= {'OutOfStock', 'SoldOut', 'Discontinued'}:
                    variants.append('unavailable')
                else:
                    variants.append('unknown')
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    visit(value)

    for script in scripts:
        try:
            visit(json.loads(unescape(script)))
        except (ValueError, TypeError):
            continue
    if variants and len(set(variants)) == 1 and variants[0] != 'unknown':
        return variants[0], 'Exakte Größe und Farbe in den Produktdaten gefunden.'
    return 'unknown', 'Keine eindeutigen Bestandsdaten für die gewünschte Größe und Farbe gefunden.'


def check(cfg):
    if cfg.get('CHECK_MODE', 'browser') == 'browser':
        try:
            from browser_check import check_browser
            return check_browser(cfg)
        except Exception as exc:
            return 'unknown', 'Browser nicht einsatzbereit (' + type(exc).__name__ + ').'
    return 'unknown', 'Nur CHECK_MODE=browser unterstützt die geprüfte Variantenauswahl.'


def validate_config(cfg):
    required = ['PRODUCT_URL', 'PRODUCT_SIZE', 'PRODUCT_COLOR', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing = [key for key in required if not cfg.get(key)]
    if missing:
        raise ValueError('Fehlende Einstellungen: ' + ', '.join(missing))
    cfg.setdefault('PRODUCT_SKU', '673107873')
    url = urlsplit(cfg['PRODUCT_URL'])
    if (url.scheme != 'https' or url.netloc != 'www.hollisterco.com'
            or url.path != '/shop/eu-de/p/henley-mit-leopardenprint-und-logo-63757420'):
        raise ValueError('PRODUCT_URL muss die konfigurierte deutsche Produktseite sein.')
    if (cfg['PRODUCT_SKU'], cfg['PRODUCT_SIZE'], cfg['PRODUCT_COLOR']) != ('673107873', 'XS', 'Helles Pink'):
        raise ValueError('Zielvariante muss SKU 673107873, XS, Helles Pink sein.')
    if cfg.get('CHECK_MODE', 'browser') != 'browser':
        raise ValueError('CHECK_MODE muss browser sein.')
    try:
        interval = int(cfg.get('CHECK_INTERVAL_SECONDS', '60'))
        ZoneInfo(cfg.get('TZ', 'Europe/Berlin'))
    except Exception:
        raise ValueError('Intervall oder Zeitzone ungültig.') from None
    if interval < 60:
        raise ValueError('CHECK_INTERVAL_SECONDS muss für diesen Monitor 900 sein.')
    return interval


def notify(cfg, text):
    req = urllib.request.Request('https://api.telegram.org/bot' + cfg['TELEGRAM_BOT_TOKEN'] + '/sendMessage', data=json.dumps({'chat_id': cfg['TELEGRAM_CHAT_ID'], 'text': text, 'disable_web_page_preview': True}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)
    if not data.get('ok') or str(data.get('result', {}).get('chat', {}).get('id')) != cfg['TELEGRAM_CHAT_ID']:
        raise RuntimeError('Telegram did not confirm delivery to configured chat')
    return data['result']['message_id']


def run_once(cfg):
    status, reason = check(cfg)
    return send_status(cfg, status, reason)


def send_status(cfg, status, reason):
    timestamp = datetime.now(ZoneInfo(cfg.get('TZ', 'Europe/Berlin'))).strftime('%d.%m.%Y %H:%M')
    label = {'available': '✅ Verfügbar', 'unavailable': '❌ Nicht verfügbar', 'unknown': '⚠️ Status nicht prüfbar'}[status]
    LOG.info('stock_check status=%s reason=%s', status, reason)
    sku_label = f' · Referenz-SKU {cfg["PRODUCT_SKU"]}' if cfg.get('PRODUCT_SKU') else ''
    message = f'Hollister · {timestamp}\n{cfg.get('PRODUCT_NAME', 'Icon Henley')}{sku_label} · {cfg["PRODUCT_SIZE"]} · {cfg["PRODUCT_COLOR"]}\n{label}\n{reason}\n{cfg["PRODUCT_URL"]}'
    try:
        mid = notify(cfg, message)
        LOG.info('status=%s telegram_message_id=%s', status, mid)
        return status
    except Exception as exc:
        LOG.error('Telegram delivery failed: %s', type(exc).__name__)
        return 'delivery_failed'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--test-telegram', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    load_env()
    cfg = dict(os.environ)
    try:
        interval = validate_config(cfg)
    except ValueError as exc:
        parser.error(str(exc))
    if args.test_telegram:
        try:
            LOG.info('telegram_test message_id=%s', notify(cfg, 'Hollister: Telegram-Verbindungstest. Dies ist keine Bestandsmeldung.'))
            return 0
        except Exception as exc:
            LOG.error('Telegram-Test fehlgeschlagen: %s', type(exc).__name__)
            return 1
    if args.check_only:
        status, reason = check(cfg)
        LOG.info('stock_check status=%s reason=%s', status, reason)
        return 2 if status == 'unknown' else 0
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.set())
    LOG.info('Monitor gestartet; erste Abfrage sofort, Intervall=%ss', interval)
    while not STOP.is_set():
        started = time.monotonic()
        result = run_once(cfg)
        if args.once:
            return 1 if result == 'delivery_failed' else (2 if result == 'unknown' else 0)
        STOP.wait(max(0, interval - (time.monotonic() - started)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
