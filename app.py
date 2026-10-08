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

STOP = threading.Event()
LOG = logging.getLogger('hollister')


def load_env(path='.env'):
    if Path(path).is_file():
        for line in Path(path).read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def stock_from_html(html, size, color):
    if 'Client Challenge' in html or '/_fs-ch-' in html:
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
            if 'Product' in typ and str(obj.get('size', '')).casefold() == size.casefold() and str(obj.get('color', '')).casefold() == color.casefold():
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
    try:
        req = urllib.request.Request(cfg['PRODUCT_URL'], headers={'User-Agent': 'HollisterAvailabilityMonitor/0.1', 'Accept-Language': 'de-DE,de;q=0.9'})
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read(5_000_001)
            if len(html) > 5_000_000:
                return 'unknown', 'Shopantwort zu groß.'
            return stock_from_html(html.decode('utf-8', errors='replace'), cfg['PRODUCT_SIZE'], cfg['PRODUCT_COLOR'])
    except Exception as exc:
        # Never log URLs/exceptions containing credentials.
        return 'unknown', 'Shopabfrage fehlgeschlagen (' + type(exc).__name__ + ').'


def notify(cfg, text):
    req = urllib.request.Request('https://api.telegram.org/bot' + cfg['TELEGRAM_BOT_TOKEN'] + '/sendMessage', data=json.dumps({'chat_id': cfg['TELEGRAM_CHAT_ID'], 'text': text, 'disable_web_page_preview': True}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)
    if not data.get('ok') or str(data.get('result', {}).get('chat', {}).get('id')) != cfg['TELEGRAM_CHAT_ID']:
        raise RuntimeError('Telegram did not confirm delivery to configured chat')
    return data['result']['message_id']


def run_once(cfg):
    status, reason = check(cfg)
    timestamp = datetime.now(ZoneInfo(cfg.get('TZ', 'Europe/Berlin'))).strftime('%d.%m.%Y %H:%M')
    label = {'available': '✅ Verfügbar', 'unavailable': '❌ Nicht verfügbar', 'unknown': '⚠️ Status nicht prüfbar'}[status]
    message = f'Hollister · {timestamp}\nIcon Henley · {cfg["PRODUCT_SIZE"]} · {cfg["PRODUCT_COLOR"]}\n{label}\n{reason}\n{cfg["PRODUCT_URL"]}'
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
    parser.add_argument('--delay-first', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    load_env()
    required = ['PRODUCT_URL', 'PRODUCT_SIZE', 'PRODUCT_COLOR', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    cfg = dict(os.environ)
    missing = [k for k in required if not cfg.get(k)]
    if missing:
        parser.error('Missing settings: ' + ', '.join(missing))
    if not cfg['PRODUCT_URL'].startswith('https://www.hollisterco.com/shop/'):
        parser.error('PRODUCT_URL must be a Hollister shop HTTPS URL')
    interval = int(cfg.get('CHECK_INTERVAL_SECONDS', '900'))
    if interval < 60:
        parser.error('CHECK_INTERVAL_SECONDS must be at least 60')
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.set())
    if args.delay_first:
        STOP.wait(interval)
    while not STOP.is_set():
        started = time.monotonic()
        result = run_once(cfg)
        if args.once:
            return 1 if result == 'delivery_failed' else 0
        STOP.wait(max(0, interval - (time.monotonic() - started)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
