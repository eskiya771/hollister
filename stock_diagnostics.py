"""Bounded product-only diagnostics; never dump HTML, cookies or headers."""
import json
import logging
from urllib.parse import urlsplit

LOG = logging.getLogger('hollister.diagnostics')
FIELDS = {
    '@type', 'sku', 'productid', 'productgroupid', 'catentryid', 'itemid',
    'color', 'colour', 'size', 'availability', 'inventory', 'inventorystatus',
    'inventoryquantity', 'available', 'isavailable', 'instock', 'isinstock',
    'outofstock', 'soldout', 'quantity', 'stock', 'stockstatus', 'status',
    'offers', 'hasvariant', 'id',
}
IDENTITIES = {'sku', 'catentryid', 'productid', 'itemid', 'id'}


def clean(value, depth=0):
    if depth > 5:
        return '<depth-limit>'
    if isinstance(value, dict):
        return {key: clean(item, depth + 1) for key, item in value.items()
                if key.casefold() in FIELDS}
    if isinstance(value, list):
        return [clean(item, depth + 1) for item in value[:30]]
    if isinstance(value, str):
        return value[:160]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return None


def find_records(value, sku, products=False):
    found = []
    def visit(item, depth=0):
        if depth > 15 or len(found) >= 15:
            return
        if isinstance(item, dict):
            typ = item.get('@type', '')
            is_product = typ in ('Product', 'ProductGroup') if isinstance(typ, str) else False
            direct = any(key.casefold() in IDENTITIES and str(val) == sku for key, val in item.items())
            if direct or (products and is_product):
                found.append(clean(item))
            for key, val in item.items():
                if key == sku and isinstance(val, dict):
                    found.append({'sku': sku, 'inventory': clean(val)})
                elif isinstance(val, (dict, list)):
                    visit(val, depth + 1)
        elif isinstance(item, list):
            for child in item[:2000]:
                visit(child, depth + 1)
    visit(value)
    return found[:15]


def observe_response(response, sku, sink):
    """Observe only JSON already requested by the normal product page."""
    try:
        if not sku:
            return
        if (urlsplit(response.url).hostname != 'www.hollisterco.com'
                or response.request.resource_type not in ('xhr', 'fetch')
                or 'json' not in response.headers.get('content-type', '')
                or len(sink) >= 8):
            return
        length = response.headers.get('content-length')
        if length and int(length) > 2_000_000:
            return
        body = response.body()
        if len(body) > 2_000_000 or sku.encode() not in body:
            return
        records = find_records(json.loads(body), sku)
        if records:
            sink.append(records)
    except Exception:
        pass  # Diagnostics never alter a stock result.


def report(page, cfg, responses):
    try:
        scripts = page.locator('script[type="application/ld+json"]').all_text_contents()
        products = []
        for script in scripts[:10]:
            try:
                products.extend(find_records(json.loads(script), cfg['PRODUCT_SKU'], products=True))
            except (ValueError, TypeError):
                continue
        # Only the selected product controls and explicit stock/identity fields.
        dom = page.evaluate('''() => {
          const main = document.querySelector('main');
          if (!main) return {main: false};
          const attrs = ['type', 'name', 'value', 'aria-label', 'aria-checked',
            'aria-disabled', 'data-sku', 'data-catentryid', 'data-product-id'];
          const controls = [...main.querySelectorAll('input[type="radio"], [role="radio"], input[type="hidden"]')]
            .filter(e => e.checked || e.getAttribute('aria-checked') === 'true' ||
              /^(sku|catentryid|productid|itemid)$/i.test(e.getAttribute('name') || ''))
            .slice(0, 12).map(e => Object.fromEntries(attrs
              .filter(a => e.hasAttribute(a)).map(a => [a, e.getAttribute(a).slice(0, 120)])));
          const buttons = [...main.querySelectorAll('button')]
            .filter(e => e.innerText.trim() === 'In den Warenkorb' && e.getClientRects().length);
          return {main: true, controls,
            sold_out: /Dieser Artikel ist ausverkauft/i.test(main.innerText),
            bag_count: buttons.length,
            bag_enabled: buttons.length === 1 && !buttons[0].disabled && buttons[0].getAttribute('aria-disabled') !== 'true'};
        }''')
        LOG.info('product_diagnostics=%s', json.dumps({
            'jsonld_script_count': len(scripts), 'products': products[:15],
            'selection': dom, 'variant_responses': responses,
        }, ensure_ascii=True)[:14000])
    except Exception as exc:
        LOG.info('product_diagnostics_failed=%s', type(exc).__name__)
