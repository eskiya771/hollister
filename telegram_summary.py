"""One compact Telegram message per completed checking cycle."""
from datetime import datetime
from zoneinfo import ZoneInfo
from app import LOG, notify


def format_summary(cfg, results):
    stamp = datetime.now(ZoneInfo(cfg.get('TZ', 'Europe/Berlin'))).strftime('%d.%m. %H:%M')
    lines = [f'Hollister · {stamp}']
    groups = {}
    for variant, status, reason in results:
        key = (variant['PRODUCT_URL'], variant.get('PRODUCT_NAME', 'Icon Henley'), variant['PRODUCT_COLOR'])
        groups.setdefault(key, []).append((variant, status, reason))
    icons = {'available': '✅', 'unavailable': '❌', 'unknown': '⚠️'}
    for (_, name, color), entries in groups.items():
        name = {'Icon Henley': 'Henley', 'Camisole mit Spitzenbesatz': 'Camisole'}.get(name, name)
        lines.extend(['', f'{name} · {color}'])
        for variant, status, _ in entries:
            label = {'available': 'Verfügbar', 'unavailable': 'Ausverkauft'}.get(status, 'Nicht prüfbar')
            inventory = variant.get('PRODUCT_INVENTORY')
            count = str(inventory) if status in ('available', 'unavailable') and type(inventory) is int and inventory >= 0 else 'unbekannt'
            lines.append(f'{icons.get(status, "⚠️")} {variant["PRODUCT_SIZE"]} · {label} · Bestand: {count}')
            if variant.get('PRODUCT_SKU'):
                lines.append(f'   SKU: {variant["PRODUCT_SKU"]}')
        errors = [(variant['PRODUCT_SIZE'], reason) for variant, status, reason in entries if status not in ('available', 'unavailable')]
        if errors:
            kinds = {}
            for size, reason in errors:
                text = reason.casefold()
                label = ('Browser-Tab geschlossen' if 'targetclosed' in text else
                         'CAPTCHA' if 'captcha' in text or 'schutzseite' in text else
                         'Cookie-Dialog' if 'cookie' in text else
                         'Ladefehler' if 'ladefehler' in text or 'produktseite laden' in text else
                         'API nicht prüfbar' if text.startswith('api:') else
                         'nicht eindeutig prüfbar')
                kinds.setdefault(label, []).append(size)
            lines.append('  ' + '; '.join(f'{"/".join(sizes)}: {label}' for label, sizes in kinds.items()))
    return '\n'.join(lines)


def send_summary(cfg, results):
    for variant, status, reason in results:
        LOG.info('stock_check product=%s size=%s status=%s reason=%s',
                 variant.get('PRODUCT_NAME'), variant['PRODUCT_SIZE'], status, reason)
    try:
        mid = notify(cfg, format_summary(cfg, results))
        LOG.info('summary variants=%s telegram_message_id=%s', len(results), mid)
        return True
    except Exception as exc:
        LOG.error('Telegram delivery failed: %s', type(exc).__name__)
        return False
