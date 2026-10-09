"""Bounded read-only probes of the observed collection GraphQL field."""
from datetime import datetime, timezone
from http.cookiejar import CookieJar
import json
from pathlib import Path
from confirm_http_products import USER_AGENT, TARGETS
from probe_collection_api import URL
from session_http_diagnostic import fetch, summarize_stock


def query(arguments):
    return 'query DiagnosticCollection { collection(' + arguments + ') { collection { skus { productId shortSku sizePrimary sizeSecondary inventory inventoryStatus } } } }'


if __name__ == '__main__':
    result = {'at_utc': datetime.now(timezone.utc).isoformat(), 'credentials': 'none', 'probes': []}
    for page_id, color, color_id, sizes, _ in TARGETS:
        candidates = [('product_id_only', 'productId: ' + json.dumps(color_id)),
                      ('empty_collection_id', 'collectionId: "", productId: ' + json.dumps(color_id) + ', faceout: ""')]
        for name, arguments in candidates:
            text = query(arguments)
            response = fetch(URL, USER_AGENT, CookieJar(), graphql_query=text)
            stocks = summarize_stock(response, color_id, sizes, {})
            result['probes'].append({'page_product_id': page_id, 'color': color, 'color_product_id': color_id,
                                     'candidate': name, 'query': text,
                                     'response': {k: v for k, v in response.items() if k not in ('embedded', 'records')},
                                     'sizes': stocks})
            if all(row['status'] != 'nicht prüfbar' for row in stocks.values()):
                break
    Path(__file__).with_name('api-variant-probes.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
