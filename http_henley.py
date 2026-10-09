"""Single credential-free HTTP probe; does not touch the running monitor."""
import json
from pathlib import Path
from diagnose_availability import direct_http

URL = 'https://www.hollisterco.com/shop/eu-de/p/henley-mit-leopardenprint-und-logo-63757420'

if __name__ == '__main__':
    response = direct_http(URL)
    reason = 'HTTP-Antwort liefert keine bestätigte Zuordnung zu Helles Pink und Größe.'
    if response.get('challenge_detected'):
        reason = 'Hollister liefert eine Schutzseite statt Produkt-/Bestandsdaten.'
    result = {'product_id': '63757420', 'color': 'Helles Pink', 'method': 'GET',
              'url': URL, 'credentials': 'none', 'response': response,
              'sizes': {size: {'status': 'nicht prüfbar', 'reason': reason} for size in ('XS', 'S')}}
    Path(__file__).with_name('http-henley-result.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
