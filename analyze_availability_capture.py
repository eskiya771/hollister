"""Offline analysis of sanitized captures; no browser or HTTP activity."""
import argparse
import json
from pathlib import Path


def analyze(capture):
    white = next((s for s in capture['snapshots'] if s['phase'] in ('select_white', 'select_target_color')), None)
    identities = {s['value'] for s in (white or {}).get('selection', []) if str(s.get('value', '')).isdigit()}
    color_id = next(iter(identities)) if len(identities) == 1 else None
    selected = capture.get('selected_color')
    if selected:
        color_id = selected.get('product_id') if (selected.get('checked') and selected.get('heading_confirmed') and selected.get('name') == capture.get('color') and str(selected.get('product_id', '')).isdigit()) else None
    docs = [r for r in capture['responses'] if r['type'] == 'document' and r['phase'] == 'initial_load']
    rows = [row for doc in docs for script in doc.get('initial_html', {}).get('json', []) for row in script['records']
            if '.collection.skus[' in row['path'] and row['fields'].get('productId') == color_id]
    results = {}
    for size in (capture.get('sizes') or dict.fromkeys(('XS', 'S', 'XXL'))):
        matching = [row for row in rows if row['fields'].get('sizePrimary') == size + '_p']
        tuples = {(r['fields'].get('shortSku'), r['fields'].get('inventory'), r['fields'].get('inventoryStatus')) for r in matching}
        status = 'nicht prüfbar'
        sku = inventory = inventory_status = None
        if color_id and len(tuples) == 1:
            sku, inventory, inventory_status = next(iter(tuples))
            if isinstance(sku, str) and sku.isdigit() and isinstance(inventory, int) and not isinstance(inventory, bool):
                if inventory_status == 'Unavailable' and inventory == 0:
                    status = 'ausverkauft'
                elif inventory_status == 'Available' and inventory > 0:
                    status = 'verfügbar'
        ui = capture.get('sizes', {}).get(size, {}).get('status', 'nicht prüfbar')
        if status != ui:
            status = 'nicht prüfbar'
        results[size] = {'status': status, 'shortSku': sku, 'inventory': inventory,
                         'inventoryStatus': inventory_status, 'ui_status': ui,
                         'source': 'initial HTML: CACHE.ROOT_QUERY.*.collection.skus'}
    return {'page_product_id': capture['product_id'], 'color': capture.get('color', 'Weiß'), 'color_product_id': color_id,
            'captured_at_utc': capture.get('captured_at_utc'),
            'sizes': results, 'request_count': len(capture['requests']),
            'response_count': len(capture['responses']),
            'size_change_requests': [r for r in capture['requests'] if r['phase'].startswith('select_size_')],
            'http_tests': capture['http_tests'], 'capture_errors': capture['errors']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = analyze(json.loads(Path(args.capture).read_text(encoding='utf-8')))
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
