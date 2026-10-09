"""Read the exact existing configured product URL using normal HTTP."""
from http.cookiejar import CookieJar
import json
from pathlib import Path
from confirm_http_products import USER_AGENT
from session_http_diagnostic import fetch

URL = 'https://www.hollisterco.com/shop/eu-de/p/camisole-mit-spitzenbesatz-fr-lagenlooks-63270319?faceout=model&seq=15&gridProductPosition=3'

if __name__ == '__main__':
    response = fetch(URL, USER_AGENT, CookieJar())
    queries = [q for s in response.get('embedded', {}).get('json', []) for q in s.get('inventory_cache_queries', [])]
    result = {'response': {k: v for k, v in response.items() if k not in ('embedded', 'records')}, 'cache_queries': queries}
    Path(__file__).with_name('camisole-collection-discovery.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
