"""Three read-only contract checks for the confirmed Henley collection."""
from http.cookiejar import CookieJar
import json
from pathlib import Path
from confirm_http_products import USER_AGENT
from probe_collection_api import URL
from probe_api_variants import query
from session_http_diagnostic import fetch, summarize_stock

if __name__ == '__main__':
    tests = []
    for name, arguments in (
        ('all_arguments', 'collectionId: "711658", faceout: "", productId: "63766393"'),
        ('without_product_id', 'collectionId: "711658", faceout: ""'),
        ('collection_id_only', 'collectionId: "711658"'),
    ):
        response = fetch(URL, USER_AGENT, CookieJar(), graphql_query=query(arguments))
        tests.append({'name': name, 'arguments': arguments,
                      'response': {k: v for k, v in response.items() if k not in ('records', 'embedded')},
                      'sizes': summarize_stock(response, '63766393', ('XS', 'S'), {})})
    Path(__file__).with_name('collection-argument-checks.json').write_text(json.dumps(tests, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(tests, ensure_ascii=True, indent=2))
