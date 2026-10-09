"""Cookie-free, conservative availability checks against Hollister's EU API."""
import json
import urllib.error
import urllib.request

URL = 'https://www.hollisterco.com/api/bff/product?storeId=19158&catalogId=11558&langId=-3&brand=hol&store=h-eu-de&country=DE&urlRoot=%2Fshop%2Feu-de&currency=EUR'
TARGETS = {
    'henley': {'name': 'Icon Henley', 'color': 'Helles Pink', 'page': '63757420',
               'product': '63766393', 'collection': '711658',
               'skus': {'XS': '673107742', 'S': '673107911'}},
    'camisole': {'name': 'Camisole mit Spitzenbesatz', 'color': 'Weiß', 'page': '63270319',
                 'product': '63617331', 'collection': '706282',
                 'skus': {'XS': '671819156', 'S': '671635648', 'XXL': '670148021'}},
}
MAX_BYTES = 2 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def query(target):
    return ('query MonitorCollection { collection(collectionId: '
            + json.dumps(target['collection']) + ', productId: '
            + json.dumps(target['product'])
            + ', faceout: "") { collection { skus { productId shortSku '
              'sizePrimary sizeSecondary inventory inventoryStatus } } } }')


def classify(data, target, inventories=None):
    unknown = {size: ('unknown', 'API: Variante nicht eindeutig prüfbar') for size in target['skus']}
    if not isinstance(data, dict) or data.get('errors'):
        return {size: ('unknown', 'API: GraphQL-Antwort fehlerhaft') for size in unknown}
    try:
        rows = data['data']['collection']['collection']['skus']
        if not isinstance(rows, list):
            return unknown
    except (KeyError, TypeError):
        return unknown
    result = dict(unknown)
    for size, sku in target['skus'].items():
        matches = [r for r in rows if isinstance(r, dict)
                   and str(r.get('productId')) == target['product']
                   and r.get('sizePrimary') == size + '_p'
                   and r.get('sizeSecondary') in (None, '')]
        if len(matches) != 1 or str(matches[0].get('shortSku')) != sku:
            continue
        row = matches[0]
        inventory = row.get('inventory')
        if type(inventory) is not int:
            continue
        status = row.get('inventoryStatus')
        if inventory > 0 and status == 'Available':
            result[size] = ('available', f'API: verfügbar (Bestand {inventory})')
        elif inventory == 0 and status == 'Unavailable':
            result[size] = ('unavailable', 'API: ausverkauft (Bestand 0)')
        if inventories is not None and result[size][0] != 'unknown':
            inventories[size] = inventory
    return result


def check_product(target, max_age=900, inventories=None):
    def failed(reason):
        return {size: ('unknown', reason) for size in target['skus']}
    request = urllib.request.Request(URL, method='POST',
        data=json.dumps({'query': query(target)}).encode(), headers={
            'Content-Type': 'application/json',
            'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            if response.status != 200:
                return failed(f'API: HTTP {response.status}')
            age = response.headers.get('Age')
            if age is not None and (not age.isdigit() or int(age) > max_age):
                return failed('API: Cache-Alter nicht zulässig')
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                return failed('API: Antwort zu groß')
            return classify(json.loads(body), target, inventories)
    except urllib.error.HTTPError as exc:
        return failed(f'API: HTTP {exc.code}')
    except Exception as exc:
        # Exception strings can include URLs or server-controlled data.
        return failed('API: Abfrage fehlgeschlagen (' + type(exc).__name__ + ')')


def check_all(cfg):
    results = []
    for target in TARGETS.values():
        inventories = {}
        sizes = check_product(target, int(cfg.get('HTTP_MAX_CACHE_AGE_SECONDS', '900')), inventories)
        for size, (status, reason) in sizes.items():
            variant = dict(PRODUCT_NAME=target['name'], PRODUCT_COLOR=target['color'],
                           PRODUCT_SIZE=size, PRODUCT_SKU=target['skus'][size],
                           PRODUCT_INVENTORY=inventories.get(size),
                           PRODUCT_URL='https://www.hollisterco.com/shop/eu-de/search?searchTerm=' + target['page'])
            results.append((variant, status, reason))
    return results
