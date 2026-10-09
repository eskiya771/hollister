"""Two product captures in one shared diagnostic browser, no Telegram."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from diagnose_availability import run, validate_target
from analyze_availability_capture import analyze

TARGETS = (
    ('63757420', 'Helles Pink', ('XS', 'S'),
     'https://www.hollisterco.com/shop/eu-de/p/henley-mit-leopardenprint-und-logo-63757420'),
    ('63270319', 'Weiß', ('XS', 'S', 'XXL'),
     'https://www.hollisterco.com/shop/eu-de/p/camisole-mit-spitzenbesatz-fr-lagenlooks-63270319'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cdp', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--session-http', action='store_true')
    args = parser.parse_args()
    result = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'products': [], 'summaries': []}
    output = Path(args.output)
    for product_id, color, sizes, url in TARGETS:
        validate_target(product_id, color, sizes, url)
        print('Capturing product=' + product_id, flush=True)
        config = SimpleNamespace(product_id=product_id, color=color, sizes=sizes, url=url, cdp=args.cdp, http=False, session_http=args.session_http)
        try:
            capture = run(config)
        except Exception as exc:
            capture = {'product_id': product_id, 'color': color, 'sizes': {s: {'status': 'nicht prüfbar'} for s in sizes},
                       'requests': [], 'responses': [], 'snapshots': [], 'http_tests': [],
                       'errors': [{'stage': 'product_capture', 'error_type': type(exc).__name__}]}
        result['products'].append(capture)
        result['summaries'].append(analyze(capture))
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Captured product=' + product_id + ' errors=' + str(len(capture['errors'])), flush=True)
    result['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Both product diagnostics written.', flush=True)


if __name__ == '__main__':
    main()
