"""Standalone read-only GraphQL checks for both products; no browser/cookies.

Diagnostic only: never changes monitor settings or sends notifications.
"""
import argparse
from datetime import datetime, timezone
from http.cookiejar import CookieJar
import json
from pathlib import Path
from session_http_diagnostic import fetch, summarize_stock

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'
URL = 'https://www.hollisterco.com/api/bff/product?storeId=19158&catalogId=11558&langId=-3&brand=hol&store=h-eu-de&country=DE&urlRoot=%2Fshop%2Feu-de&currency=EUR'
TARGETS = {
    'henley': {'page_id': '63757420', 'color': 'Helles Pink', 'color_id': '63766393',
               'collection_id': '711658', 'skus': {'XS': '673107742', 'S': '673107911'}},
    'camisole': {'page_id': '63270319', 'color': 'Weiß', 'color_id': '63617331',
                 'collection_id': '706282', 'skus': {'XS': '671819156', 'S': '671635648', 'XXL': '670148021'}},
}


def query_for(target, include_faceout=True):
    arguments = 'collectionId: ' + json.dumps(target['collection_id']) + ', productId: ' + json.dumps(target['color_id'])
    if include_faceout:
        arguments += ', faceout: ""'
    return 'query DiagnosticCollection { collection(' + arguments + ') { collection { skus { productId shortSku sizePrimary sizeSecondary inventory inventoryStatus } } } }'


def check(product, include_faceout=True):
    target = TARGETS[product]
    response = fetch(URL, USER_AGENT, CookieJar(), graphql_query=query_for(target, include_faceout))
    sizes = summarize_stock(response, target['color_id'], tuple(target['skus']), {})
    for size, row in sizes.items():
        row.pop('matches_browser_snapshot', None)
        if row['shortSku'] != target['skus'][size]:
            row['status'] = 'nicht prüfbar'
            row['reason'] = 'SKU does not match prior confirmed color/size identity'
    return {'at_utc': datetime.now(timezone.utc).isoformat(), 'page_product_id': target['page_id'],
            'color': target['color'], 'color_product_id': target['color_id'], 'collection_id': target['collection_id'],
            'transport': 'Python urllib on NAS; no browser, cookies or authentication',
            'response': {k: v for k, v in response.items() if k not in ('embedded', 'records')}, 'sizes': sizes}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--product', choices=('henley', 'camisole', 'both'), default='both')
    parser.add_argument('--omit-faceout', action='store_true', help='Diagnostic contract test only')
    args = parser.parse_args()
    keys = tuple(TARGETS) if args.product == 'both' else (args.product,)
    result = {'at_utc': datetime.now(timezone.utc).isoformat(),
              'products': [check(key, not args.omit_faceout) for key in keys]}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
