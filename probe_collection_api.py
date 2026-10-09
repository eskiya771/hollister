"""One read-only query derived from captured cache arguments; no credentials."""
from datetime import datetime, timezone
from http.cookiejar import CookieJar
import json
from pathlib import Path
from confirm_http_products import USER_AGENT
from session_http_diagnostic import fetch

URL = 'https://www.hollisterco.com/api/bff/product?storeId=19158&catalogId=11558&langId=-3&brand=hol&store=h-eu-de&country=DE&urlRoot=%2Fshop%2Feu-de&currency=EUR'
QUERY = '''query DiagnosticCollection {
  collection(collectionId: "711658", faceout: "", productId: "63757975") {
    collection {
      skus { productId shortSku sizePrimary sizeSecondary inventory inventoryStatus }
    }
  }
}'''

if __name__ == '__main__':
    response = fetch(URL, USER_AGENT, CookieJar(), graphql_query=QUERY)
    result = {'at_utc': datetime.now(timezone.utc).isoformat(), 'method': 'POST', 'url': URL,
              'query': QUERY, 'credentials': 'none', 'query_source': 'reconstructed from observed cache, not captured original query',
              'response': {k: v for k, v in response.items() if k not in ('embedded', 'records')},
              'stock_records': [r for r in response.get('records', []) if 'inventory' in r['fields']]}
    Path(__file__).with_name('collection-api-probe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
