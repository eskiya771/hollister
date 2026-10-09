"""Use observed GetOutfits operation with confirmed public Camisole KIC."""
from http.cookiejar import CookieJar
import json
from pathlib import Path
from urllib.parse import urlencode
from confirm_http_products import USER_AGENT
from session_http_diagnostic import fetch

PARAMETERS = {'storeId': '19158', 'catalogId': '11558', 'langId': '-3', 'brand': 'hol',
              'store': 'h-eu-de', 'country': 'DE', 'urlRoot': '/shop/eu-de', 'currency': 'EUR',
              'operationName': 'GetOutfits',
              'variables': json.dumps({'kicId': 'KIC_339-6340-00307-101'}, separators=(',', ':')),
              'extensions': json.dumps({'persistedQuery': {'version': 1, 'sha256Hash': '61785d6b75f89001bb1f5e92219a1bc7b60eff40dbd8e8a1288f70a0a5e172ca'}}, separators=(',', ':'))}

if __name__ == '__main__':
    response = fetch('https://www.hollisterco.com/api/bff/product?' + urlencode(PARAMETERS), USER_AGENT, CookieJar())
    matches = [r for r in response.get('records', []) if r['fields'].get('productId') == '63617331' and 'collectionId' in r['fields']]
    if not matches:
        from probe_collection_api import URL
        text = 'query DiagnosticOutfits { outfits(kicId: "KIC_339-6340-00307-101") { products { productId collectionId kicId } } }'
        response = fetch(URL, USER_AGENT, CookieJar(), graphql_query=text)
        matches = [r for r in response.get('records', []) if r['fields'].get('productId') == '63617331' and 'collectionId' in r['fields']]
    result = {'operation': 'GetOutfits', 'public_kic': 'KIC_339-6340-00307-101',
              'response': {k: v for k, v in response.items() if k not in ('records', 'embedded')},
              'matching_product_records': matches,
              'collection_ids': sorted({r['fields']['collectionId'] for r in matches})}
    Path(__file__).with_name('camisole-api-discovery.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
