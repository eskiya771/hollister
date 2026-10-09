"""Ordinary HTTP with scoped session cookies in memory; no CAPTCHA bypass.

Only HTTPS requests and redirects to the existing Hollister host are allowed.
Cookie values, headers, raw HTML and raw error messages never enter the result.
"""
from datetime import datetime, timezone
from http.cookiejar import Cookie, CookieJar
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPCookieProcessor, HTTPRedirectHandler, Request
from diagnose_availability import HOST, LIMIT, embedded, endpoint, extract


def allowed_url(url):
    parsed = urlsplit(url)
    return parsed.scheme == 'https' and parsed.hostname == HOST and parsed.port in (None, 443) and not parsed.username and not parsed.password


class ScopedRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl):
            raise ValueError('redirect_outside_scope')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def cookie_jar(browser_cookies):
    jar = CookieJar()
    for item in browser_cookies:
        domain = item.get('domain', '')
        if domain.lstrip('.') not in (HOST, 'hollisterco.com'):
            continue
        expires = item.get('expires', -1)
        jar.set_cookie(Cookie(
            version=0, name=item['name'], value=item['value'], port=None, port_specified=False,
            domain=domain, domain_specified=True, domain_initial_dot=domain.startswith('.'),
            path=item.get('path', '/'), path_specified=True, secure=item.get('secure', False),
            expires=int(expires) if expires and expires > 0 else None,
            discard=not expires or expires <= 0, comment=None, comment_url=None,
            rest={'HttpOnly': None} if item.get('httpOnly') else {}, rfc2109=False))
    return jar


def parse_response(body, status, final_url):
    result = {'status': status, 'final_url': endpoint(final_url), 'bytes': len(body), 'truncated': len(body) > LIMIT}
    if len(body) > LIMIT:
        return result
    try:
        payload = json.loads(body)
        result['records'] = extract(payload)
        query_type = payload.get('data', {}).get('__schema', {}).get('queryType', {}) if isinstance(payload, dict) and isinstance(payload.get('data'), dict) else {}
        if isinstance(query_type, dict) and isinstance(query_type.get('fields'), list):
            result['catalog_query_fields'] = [f for f in query_type['fields']
                if isinstance(f, dict) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,45}', str(f.get('name', '')))
                and re.search(r'collection|product|catalog|search', f['name'], re.I)]
        if isinstance(payload, dict) and isinstance(payload.get('errors'), list):
            kinds = []
            arguments = set()
            for error in payload['errors'][:10]:
                message = str(error.get('message', '')) if isinstance(error, dict) else ''
                kind = 'schema_or_query_validation' if re.search(r'cannot query field|unknown argument|expected type|syntax error|variable.*type', message, re.I) else 'graphql_error'
                kinds.append(kind)
                for name in re.findall(r'argument\s+["\x27]([A-Za-z_][A-Za-z0-9_]{0,45})["\x27]', message, re.I):
                    if name in ('collectionId', 'productId', 'faceout', 'storeId', 'catalogId', 'langId'):
                        arguments.add(name)
            result['graphql_error_types'] = kinds
            if arguments:
                result['graphql_error_arguments'] = sorted(arguments)
    except (ValueError, UnicodeDecodeError):
        html = body.decode('utf-8', 'replace')
        result['embedded'] = embedded(html)
        result['challenge_detected'] = bool(re.search(
            r'<title[^>]*>\s*(?:Client Challenge|Access Denied)|verify you are human|Please enable JavaScript to proceed', html, re.I))
    return result


def fetch(url, user_agent, jar, graphql_query=None):
    if not allowed_url(url):
        return {'error_type': 'out_of_scope'}
    opener = build_opener(ScopedRedirect(), HTTPCookieProcessor(jar))
    if graphql_query is not None and not graphql_query.lstrip().startswith('query '):
        return {'error_type': 'only_readonly_graphql_queries_allowed'}
    req = Request(url, data=json.dumps({'query': graphql_query}).encode() if graphql_query is not None else None,
                  headers={'User-Agent': user_agent,
                               'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
                               'Accept-Language': 'de-DE,de;q=0.9'})
    if graphql_query is not None:
        req.add_header('Content-Type', 'application/json')
    try:
        with opener.open(req, timeout=25) as response:
            result = parse_response(response.read(LIMIT + 1), response.status, response.url)
            # HTTP Date/Age aid freshness assessment; no other headers exported.
            age = response.headers.get('Age', '')
            if age.isdigit():
                result['cache_age_seconds'] = int(age)
            cache_control = response.headers.get('Cache-Control', '')
            if cache_control and re.fullmatch(r'[A-Za-z0-9=, -]{1,160}', cache_control):
                result['cache_control'] = cache_control
            return result
    except HTTPError as exc:
        result = parse_response(exc.read(LIMIT + 1), exc.code, exc.url)
        result['error_type'] = 'HTTPError'
        exc.close()
        return result
    except Exception as exc:
        return {'error_type': type(exc).__name__}


def summarize_stock(response, color_product_id, sizes, expected):
    records = list(response.get('records', []))
    for script in response.get('embedded', {}).get('json', []):
        records.extend(script['records'])
    result = {}
    for size in sizes:
        tuples = {(r['fields'].get('shortSku'), r['fields'].get('inventory'), r['fields'].get('inventoryStatus'))
                  for r in records if r['fields'].get('productId') == color_product_id
                  and r['fields'].get('sizePrimary') == size + '_p'
                  and '.collection.skus[' in r['path']}
        status = 'nicht prüfbar'
        sku = inventory = state = None
        if response.get('status') == 200 and not response.get('challenge_detected') and not response.get('truncated') and not response.get('graphql_error_types') and len(tuples) == 1:
            sku, inventory, state = next(iter(tuples))
            if isinstance(sku, str) and sku.isdigit() and isinstance(inventory, int) and not isinstance(inventory, bool):
                if state == 'Available' and inventory > 0:
                    status = 'verfügbar'
                elif state == 'Unavailable' and inventory == 0:
                    status = 'ausverkauft'
        reference = expected.get(size, {})
        matches = status != 'nicht prüfbar' and all((sku, inventory, state)[i] == reference.get(k)
                  for i, k in enumerate(('shortSku', 'inventory', 'inventoryStatus')))
        result[size] = {'status': status, 'shortSku': sku, 'inventory': inventory,
                        'inventoryStatus': state, 'matches_browser_snapshot': matches}
    return result


def investigate(context, page, args, browser_capture):
    """Copy cookies only for this product URL; use ordinary urllib transport."""
    from analyze_availability_capture import analyze
    reference = analyze(browser_capture)
    if reference['color_product_id'] is None or browser_capture['errors']:
        return {'skipped': 'browser_product_not_confirmed', 'tests': []}
    user_agent = page.evaluate('navigator.userAgent')
    # Credentials are retained only in local memory, sent only to their origin.
    jar = cookie_jar(context.cookies([args.url]))
    tests = []
    for mode, active_jar in (('browser_headers_without_cookies', CookieJar()),
                             ('session_cookies_first', jar), ('session_cookies_repeat', jar)):
        if mode == 'session_cookies_repeat' and (not tests or any(
                row['status'] == 'nicht prüfbar' for row in tests[-1]['sizes'].values())):
            tests.append({'mode': mode, 'skipped': 'first_session_request_not_usable'})
            break
        response = fetch(args.url, user_agent, active_jar)
        tests.append({'mode': mode, 'at_utc': datetime.now(timezone.utc).isoformat(),
                      'transport': 'urllib, no Playwright HTTP API',
                      'response': response,
                      'sizes': summarize_stock(response, reference['color_product_id'], args.sizes, reference['sizes'])})
    return {'color_product_id': reference['color_product_id'], 'tests': tests,
            'cookie_export': 'none', 'browser_dependency': 'cookies obtained from live context for this experiment'}
