"""Read-only public GraphQL query metadata, only catalog fields exported."""
from http.cookiejar import CookieJar
import json
from pathlib import Path
from confirm_http_products import USER_AGENT
from probe_collection_api import URL
from session_http_diagnostic import fetch

QUERY = '''query DiagnosticCatalogSchema {
  __schema { queryType { fields {
    name type { kind name ofType { kind name } }
    args { name type { kind name ofType { kind name } } }
  } } }
}'''

if __name__ == '__main__':
    response = fetch(URL, USER_AGENT, CookieJar(), graphql_query=QUERY)
    result = {k: v for k, v in response.items() if k not in ('records', 'embedded')}
    Path(__file__).with_name('catalog-query-schema.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
