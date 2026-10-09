"""Read-only stock investigation attached to an EXISTING Chromium CDP session.

Never launches a browser, opens a profile, sends Telegram, or writes raw traffic.
Only creates and closes its own tab. No checkout/cart requests are replayed.
"""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

HOST = 'www.hollisterco.com'
LIMIT = 4_000_000
SAFE = re.compile(r'^(?:@type|sku|productId|productGroupId|catentryId|itemId|color|colour|colorId|size|sizeId|sizeName|availability|inventory|inventoryStatus|inventoryQuantity|available|isAvailable|inStock|isInStock|outOfStock|soldOut|quantity|stock|stockStatus|storeId|catalogId|langId|seq|faceout)$', re.I)
PRODUCT_FIELDS = re.compile(r'^(?:id|name|value|collectionId|kicId|kic|primarySize|secondarySize|sizePrimary|sizeSecondary|sizeCode|colorCode|colorName|productCode|skuId|partNumber|shortSku|longSku|isSoldOut|isAvailable|isOrderable|orderable|isPurchasable|inventoryStatus|inventory|size|sizeName|productId|itemId|catentryId|sku)$', re.I)
PUBLIC_PARAMS = {'brand', 'store', 'country', 'currency', 'urlRoot', 'storePreview', 'aemContentAuthoring', 'operationName', 'responseFormat', 'sha256Hash', 'version'}
PUBLIC_CONTAINERS = {'variables', 'extensions', 'persistedQuery'}
SECRET = re.compile(r'cookie|token|auth|session|password|secret|email|address|customer|user|visitor|device|fingerprint|csrf|jwt|signature|consent', re.I)


def scalar(key, value):
    if key in PUBLIC_PARAMS:
        if isinstance(value, (int, bool)) or value is None:
            return value
        if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_./-]{0,100}', value):
            return value
        return '[omitted]'
    if SECRET.search(key):
        return '[redacted]'
    if key.lower() == 'id' and isinstance(value, str) and not re.fullmatch(r'[0-9-]{1,30}', value):
        return '[omitted]'
    if key.lower() in ('name', 'value') and isinstance(value, str) and not re.fullmatch(r'(?:XXS|XS|S|M|L|XL|XXL|XXXL|Weiß|Weiss|White|Helles Pink|Regular|Short|Long|[0-9-]{1,30})', value, re.I):
        return '[omitted]'
    if not SAFE.fullmatch(key) and not PRODUCT_FIELDS.fullmatch(key):
        return '[omitted]'
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str) and len(value) <= 100 and not re.search(r'@|[\r\n]|eyJ|Bearer|https?://(?!schema.org/)', value):
        return value
    return '[omitted]'


def endpoint(url):
    u = urlsplit(url)
    if u.hostname != HOST:
        return '[external omitted]'
    # Drop fragments, userinfo and unknown query values; retain parameter names.
    path = u.path if u.path.startswith('/shop/') and re.search(r'-\d{8}$', u.path) else re.sub(r'[A-Za-z0-9_-]{48,}', '[redacted]', u.path)
    if SECRET.search(path):
        path = '/[sensitive-path-omitted]'
    def parameter(k, v):
        if k in ('variables', 'extensions'):
            try:
                return json.dumps(public_parameters(json.loads(v)), separators=(',', ':'))
            except ValueError:
                return '[omitted]'
        return scalar(k, v)
    return urlunsplit(('https', HOST, path, urlencode([(k if re.fullmatch(r'[\w.-]{1,50}', k) else '[key]', parameter(k, v)) for k, v in parse_qsl(u.query)]), ''))


def public_parameters(value, depth=0):
    if depth > 8:
        return '[depth-limit]'
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            if k in PUBLIC_CONTAINERS:
                result[k] = public_parameters(v, depth + 1)
            elif k in PUBLIC_PARAMS or SAFE.fullmatch(k) or PRODUCT_FIELDS.fullmatch(k) or k in ('productIds', 'itemIds', 'skuIds'):
                if isinstance(v, list):
                    result[k] = [scalar('productId', x) for x in v[:100]]
                else:
                    result[k] = scalar(k, v)
        return result
    return '[omitted]'


def schema(value, depth=0):
    if depth > 7:
        return 'depth-limit'
    if isinstance(value, dict):
        return {k: schema(v, depth + 1) for k, v in list(value.items())[:100]
                if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,45}', k) and not SECRET.search(k)}
    if isinstance(value, list):
        return [schema(value[0], depth + 1)] if value else []
    return type(value).__name__


def extract(value):
    """Preserve product-field paths, never arbitrary response strings or keys."""
    records = []
    def visit(item, path='$', depth=0):
        if depth > 20 or len(records) >= 250:
            return
        if isinstance(item, dict):
            fields = {k: scalar(k, v) for k, v in item.items()
                      if (SAFE.fullmatch(k) or PRODUCT_FIELDS.fullmatch(k)) and not isinstance(v, (list, dict))}
            if fields:
                records.append({'path': path, 'fields': fields})
            for k, v in list(item.items())[:3000]:
                if SECRET.search(k):
                    continue
                if isinstance(v, (list, dict)):
                    label = k if SAFE.fullmatch(k) or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,45}', k) or re.fullmatch(r'\d{1,15}', k) else '*'
                    visit(v, path + '.' + label, depth + 1)
        elif isinstance(item, list):
            for i, v in enumerate(item[:3000]):
                visit(v, path + f'[{i}]', depth + 1)
    visit(value)
    return records


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.scripts = []
        self.controls = []
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.active = True
            self.scripts.append('')
        attributes = dict(attrs)
        if tag in ('input', 'button', 'option') or attributes.get('role') == 'radio':
            allowed = ('data-sku', 'data-product-id', 'data-catentryid', 'aria-checked', 'aria-disabled', 'checked', 'disabled')
            control = {k: scalar(k.removeprefix('data-').replace('-', ''), v) if k.startswith('data-') else (v if v in (None, '', 'true', 'false', 'checked', 'disabled') else '[omitted]')
                       for k, v in attrs if k in allowed}
            label = attributes.get('aria-label', '')
            if label in ('XS', 'S', 'XXL', 'Weiß', 'Weiss'):
                control['label'] = label
            if control and len(self.controls) < 200:
                self.controls.append(control)
    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False
    def handle_data(self, data):
        if self.active:
            self.scripts[-1] += data


def embedded(html):
    parser = Scripts()
    parser.feed(html)
    result = []
    decoder = json.JSONDecoder()
    for i, script in enumerate(parser.scripts):
        candidates = [script.strip()]
        # Parse JSON object/array assignments without executing JavaScript.
        candidates.extend(script[m.end():].lstrip() for m in re.finditer(r'=\s*(?=[{\[])', script))
        for candidate in candidates[:100]:
            try:
                value, _ = decoder.raw_decode(candidate)
                fields = extract(value)
                if fields:
                    record = {'script_index': i, 'records': fields, 'schema': schema(value)}
                    if isinstance(value, dict):
                        root = value.get('CACHE', {}).get('ROOT_QUERY', {}) if isinstance(value.get('CACHE'), dict) else {}
                        descriptors = []
                        if isinstance(root, dict):
                            for key, entry in root.items():
                                if not isinstance(entry, dict) or not isinstance(entry.get('collection'), dict) or not isinstance(entry['collection'].get('skus'), list):
                                    continue
                                match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]{0,45})(?:\((.*)\))?', key)
                                if match and not SECRET.search(match[1]):
                                    descriptor = {'root_field': match[1]}
                                    if match[2]:
                                        try:
                                            descriptor['public_arguments'] = public_parameters(json.loads(match[2]))
                                        except ValueError:
                                            descriptor['arguments'] = '[omitted]'
                                    descriptors.append(descriptor)
                        if descriptors:
                            record['inventory_cache_queries'] = descriptors
                    result.append(record)
            except (ValueError, TypeError):
                pass
    return {'script_count': len(parser.scripts), 'json': result, 'product_controls': parser.controls,
            'coverage': 'JSON and JSON assignments; executable JS/JSON.parse strings not decoded'}


def direct_http(url):
    """Fresh urllib HTTP request: no browser context, cookies or authorization."""
    try:
        with urlopen(Request(url, headers={'Accept': 'application/json,text/html', 'User-Agent': 'Hollister-Availability-Diagnostic/1.0'}), timeout=25) as response:
            body = response.read(LIMIT + 1)
            result = {'status': response.status, 'final_url': endpoint(response.url), 'bytes': len(body), 'truncated': len(body) > LIMIT}
            if len(body) <= LIMIT:
                try:
                    result['records'] = extract(json.loads(body))
                except ValueError:
                    html = body.decode('utf-8', 'replace')
                    result['embedded'] = embedded(html)
                    result['challenge_detected'] = bool(re.search(r'<title[^>]*>\s*(?:Client Challenge|Access Denied)|verify you are human|Please enable JavaScript to proceed', html, re.I))
            return result
    except Exception as exc:
        return {'error_type': type(exc).__name__, 'status': getattr(exc, 'code', None)}


def run(args):
    from playwright.sync_api import sync_playwright
    report = {'product_id': args.product_id, 'color': args.color,
              'captured_at_utc': datetime.now(timezone.utc).isoformat(),
              'sizes': {s: {'status': 'nicht prüfbar'} for s in args.sizes},
              'requests': [], 'responses': [], 'snapshots': [], 'http_tests': [], 'errors': []}
    phase = 'initial_load'
    replay = set()
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(args.cdp, timeout=15000)
        except Exception as exc:
            report['errors'].append({'stage': 'attach_existing_session', 'error_type': type(exc).__name__})
            return report
        if not browser.contexts:
            report['errors'].append({'stage': 'existing_context_missing'})
            return report
        # Existing context preserves session; dedicated tab avoids monitor races.
        page = browser.contexts[0].new_page()
        def request(req):
            if urlsplit(req.url).hostname != HOST or req.resource_type not in ('fetch', 'xhr', 'document') or len(report['requests']) >= 400:
                return
            item = {'phase': phase, 'url': endpoint(req.url), 'method': req.method, 'type': req.resource_type}
            if req.post_data:
                try:
                    payload = json.loads(req.post_data)
                    item['body_product_fields'] = extract(payload)
                    item['body_parameters'] = public_parameters(payload)
                    item['body_schema'] = schema(payload)
                except ValueError:
                    item['body_parameters'] = {k: scalar(k, v) for k, v in parse_qsl(req.post_data) if re.fullmatch(r'[\w.-]{1,50}', k)}
            report['requests'].append(item)
        def response(res):
            req = res.request
            if urlsplit(res.url).hostname != HOST or req.resource_type not in ('fetch', 'xhr', 'document') or len(report['responses']) >= 250:
                return
            item = {'phase': phase, 'url': endpoint(res.url), 'method': req.method, 'status': res.status, 'type': req.resource_type}
            try:
                body = res.body()
                item['bytes'] = len(body)
                if len(body) <= LIMIT:
                    if req.resource_type == 'document':
                        item['initial_html'] = embedded(body.decode('utf-8', 'replace'))
                    else:
                        try:
                            payload = json.loads(body)
                            item['records'] = extract(payload)
                            item['schema'] = schema(payload)
                            # Replay only observed GETs with stock-like fields and safe URLs.
                            stock = any(any(re.search(r'stock|inventory|avail|sold', k, re.I) for k in row['fields']) for row in item['records'])
                            u = urlsplit(res.url)
                            def safe_parameter(k, v):
                                if k in ('variables', 'extensions'):
                                    try:
                                        original_value = json.loads(v)
                                        return public_parameters(original_value) == original_value
                                    except ValueError:
                                        return False
                                return scalar(k, v) == v
                            safe_query = all(safe_parameter(k, v) for k, v in parse_qsl(u.query))
                            if (stock or u.path == '/api/bff/product') and req.method == 'GET' and safe_query and not re.search(r'cart|bag|checkout|order|account|login|auth', u.path, re.I) and not SECRET.search(u.path) and not re.search(r'[A-Za-z0-9_-]{48,}', u.path):
                                replay.add(res.url)
                        except ValueError:
                            item['non_json'] = True
                else:
                    item['body_skipped'] = 'size_limit'
            except Exception as exc:
                item['error_type'] = type(exc).__name__
            report['responses'].append(item)
        page.on('request', request)
        page.on('response', response)
        def snapshot(label):
            controls = page.get_by_role('main').get_by_role('radio')
            selection = []
            for i in range(controls.count()):
                control = controls.nth(i)
                if control.is_checked():
                    selection.append({'label': scalar('name', control.get_attribute('aria-label') or ''),
                                      'value': scalar('id', control.get_attribute('value') or ''),
                                      'sku': scalar('sku', control.get_attribute('data-sku'))})
            report['snapshots'].append({'phase': label, 'url': endpoint(page.url), 'selection': selection, 'embedded': embedded(page.content())})
        try:
            page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(5000)
            snapshot(phase)
            from browser_check import protected, ready, color_pattern, inspect_variant
            if protected(page):
                report['errors'].append({'stage': 'initial_load', 'reason': 'challenge'})
            else:
                ready(page)
                main = page.get_by_role('main')
                color = main.get_by_role('radio', name=re.compile(r'^\s*' + color_pattern(args.color).pattern + r'\s*$', re.I))
                phase = 'select_target_color'
                color.check(timeout=10000)
                main.get_by_role('heading', name=re.compile(r'^Farbe:\s*' + color_pattern(args.color).pattern + r'\s*$', re.I)).wait_for(timeout=10000)
                page.wait_for_timeout(3000)
                report['selected_color'] = {'name': args.color, 'product_id': scalar('id', color.get_attribute('value') or ''), 'checked': color.is_checked(), 'heading_confirmed': True}
                snapshot(phase)
                for size_name in args.sizes:
                    phase = 'select_size_' + size_name
                    try:
                        size = main.get_by_role('radio', name=size_name, exact=True)
                        size.check(timeout=10000)
                        samples = []
                        cfg = {'PRODUCT_URL': args.url, 'PRODUCT_COLOR': args.color, 'PRODUCT_SIZE': size_name, 'PRODUCT_SKU': ''}
                        for _ in range(6):
                            page.wait_for_timeout(1000)
                            samples.append(inspect_variant(page, cfg, color, size))
                        status = samples[0] if len(set(samples)) == 1 and not protected(page) else 'unknown'
                        report['sizes'][size_name] = {'status': {'available': 'verfügbar', 'unavailable': 'ausverkauft', 'unknown': 'nicht prüfbar'}[status], 'evidence': 'UI, six matching samples; internal SKU not independently verified', 'samples': samples}
                        snapshot(phase)
                    except Exception as exc:
                        report['sizes'][size_name]['error_type'] = type(exc).__name__
                # Change to another color and back, observing network on both changes.
                radios = main.get_by_role('radio')
                color_group = color.get_attribute('name')
                for i in range(radios.count()):
                    candidate = radios.nth(i)
                    label = candidate.get_attribute('aria-label') or ''
                    same_color_group = color_group and candidate.get_attribute('name') == color_group
                    other_color_label = label and label not in ('XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXS') and not color_pattern(args.color).fullmatch(label)
                    if (same_color_group or other_color_label) and not candidate.is_checked() and candidate.is_enabled():
                        phase = 'alternate_color'
                        candidate.check(timeout=10000)
                        page.wait_for_timeout(3000)
                        snapshot(phase)
                        phase = 'return_target_color'
                        color.check(timeout=10000)
                        page.wait_for_timeout(3000)
                        snapshot(phase)
                        break
        except Exception as exc:
            report['errors'].append({'stage': phase, 'error_type': type(exc).__name__})
        finally:
            page.remove_listener('request', request)
            page.remove_listener('response', response)
            if getattr(args, 'session_http', False):
                try:
                    from session_http_diagnostic import investigate
                    report['session_http'] = investigate(browser.contexts[0], page, args, report)
                except Exception as exc:
                    report['session_http'] = {'error_type': type(exc).__name__, 'tests': []}
            page.close()
            # Do not close shared browser/context. Playwright disconnects on exit.
    if args.http:
        for url in [args.url] + sorted(replay)[:10]:
            report['http_tests'].append({'url': endpoint(url), 'method': 'GET', 'credentials': 'none', 'result': direct_http(url)})
    return report


def validate_target(product_id, color, sizes, url):
    targets = {'63270319': ('Weiß', ('XS', 'S', 'XXL')),
               '63757420': ('Helles Pink', ('XS', 'S'))}
    if product_id not in targets or color != targets[product_id][0] or not sizes or any(s not in targets[product_id][1] for s in sizes):
        raise ValueError('Unsupported diagnostic product/color/sizes')
    u = urlsplit(url)
    if u.scheme != 'https' or u.hostname != HOST or not u.path.startswith('/shop/eu-de/p/') or not u.path.endswith('-' + product_id) or u.username or u.password or u.query or u.fragment:
        raise ValueError('Use matching German product URL without query/credentials')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cdp', help='Existing CDP endpoint; never starts/restarts Chromium')
    parser.add_argument('--url', required=True, help='German product URL for requested diagnostic product')
    parser.add_argument('--product-id', default='63270319', choices=('63270319', '63757420'))
    parser.add_argument('--color', help='Default: Weiß for Camisole, Helles Pink for Henley')
    parser.add_argument('--sizes', help='Comma-separated sizes; defaults to requested product sizes')
    parser.add_argument('--output', default='availability-diagnostic.json')
    parser.add_argument('--http', action='store_true', help='Test observed safe GET endpoints without cookies/auth')
    parser.add_argument('--http-only', action='store_true', help='Probe product HTML via urllib without Playwright')
    args = parser.parse_args()
    args.color = args.color or ('Weiß' if args.product_id == '63270319' else 'Helles Pink')
    args.sizes = tuple(dict.fromkeys((args.sizes or ('XS,S,XXL' if args.product_id == '63270319' else 'XS,S')).split(',')))
    try:
        validate_target(args.product_id, args.color, args.sizes, args.url)
    except ValueError as exc:
        parser.error(str(exc))
    if not args.http_only and not args.cdp:
        parser.error('--cdp is required unless --http-only is selected')
    result = {'product_id': args.product_id, 'http_test': direct_http(args.url), 'errors': [],
              'sizes': {s: {'status': 'nicht prüfbar'} for s in args.sizes}} if args.http_only else run(args)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Sanitized diagnostic written; errors=' + str(len(result['errors'])))


if __name__ == '__main__':
    main()
