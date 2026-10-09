"""Independent NAS HTTP confirmation; imports no Playwright, uses no cookies."""
import argparse
from datetime import datetime, timezone
from http.cookiejar import CookieJar
import json
from pathlib import Path
from session_http_diagnostic import fetch, summarize_stock

# Standard Linux desktop UA for Chromium bundled with pinned Playwright 1.63.0.
# No TLS impersonation, challenge solver, cookies, auth or browser HTTP API.
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'
TARGETS = (
    ('63757420', 'Helles Pink', '63766393', ('XS', 'S'),
     'https://www.hollisterco.com/shop/eu-de/p/henley-mit-leopardenprint-und-logo-63757420'),
    ('63270319', 'Weiß', '63617331', ('XS', 'S', 'XXL'),
     'https://www.hollisterco.com/shop/eu-de/p/camisole-mit-spitzenbesatz-fr-lagenlooks-63270319'),
)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--round', type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    result = {'round': args.round, 'at_utc': datetime.now(timezone.utc).isoformat(),
              'transport': 'urllib on NAS host, no browser process/API, new empty CookieJar per request',
              'request_profile': 'Linux desktop Chromium 153, German language, normal HTML Accept',
              'products': []}
    for product_id, color, color_id, sizes, url in TARGETS:
        response = fetch(url, USER_AGENT, CookieJar())
        result['products'].append({'product_id': product_id, 'color': color,
                                  'color_product_id': color_id, 'color_identity_source': 'previous confirmed browser selection',
                                  'response': {k: v for k, v in response.items() if k not in ('embedded', 'records')},
                                  'sizes': summarize_stock(response, color_id, sizes, {})})
    Path(__file__).with_name('http-confirmation-round-' + str(args.round) + '.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
